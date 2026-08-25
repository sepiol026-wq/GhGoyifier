# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import os
import pwd
import shutil
import signal
import subprocess
from pathlib import Path

service = "ghgoyifier"
root = Path(__file__).resolve().parent.parent
_runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or str(Path.home() / ".cache")
pidfile = Path(os.environ.get("GHGOYIFIER_PIDFILE", str(Path(_runtime_dir) / "ghgoyifier.pid")))
logfile = Path(os.environ.get("GHGOYIFIER_LOG", str(root / "ghgoyifier.log")))


def detect_init() -> str:
    if shutil.which("systemctl") and Path("/run/systemd/system").exists():
        return "systemd"
    for name, marker in (("dinit", "/run/dinitctl"), ("runit", "/etc/service"), ("openrc", "/run/openrc"), ("s6", "/run/s6"), ("upstart", "/var/run/upstart")):
        if shutil.which(name) or Path(marker).exists():
            return name
    for name in ("sv", "supervise", "initctl", "rc-service", "s6-svc", "start-stop-daemon"):
        if shutil.which(name):
            return {"sv": "runit", "rc-service": "openrc", "initctl": "upstart", "s6-svc": "s6", "start-stop-daemon": "sysvinit", "supervise": "runit"}[name]
    for name in ("busybox", "finit", "dumb-init", "minit", "tiny-init", "epoch"):
        if shutil.which(name):
            return name.replace("-init", "")
    return "direct"


def _command(action: str, init: str) -> list[str] | None:
    if init == "systemd":
        return ["systemctl", action, service]
    if init == "openrc":
        return ["rc-service", service, action]
    if init == "runit":
        return ["sv", action, f"/etc/service/{service}"]
    if init == "dinit":
        return ["dinitctl", action, service]
    if init == "s6":
        return ["s6-svc", "-u" if action in {"start", "enable"} else "-d", f"/run/service/{service}"]
    if init == "upstart":
        return ["initctl", action, service]
    if init == "sysvinit":
        if action == "enable":
            return ["update-rc.d", service, "defaults"]
        if action == "disable":
            return ["update-rc.d", "-f", service, "remove"]
        return [f"/etc/init.d/{service}", action]
    if init == "finit":
        return ["finitctl", action, service]
    return None


def _service_python() -> str:
    candidate = root / ".venv" / "bin" / "python"
    return str(candidate if candidate.exists() else Path("python3"))


def install_service(init: str | None = None) -> tuple[int, str]:
    init = init or detect_init()
    python = _service_python()
    config = root / "config.toml"
    try:
        service_user = os.environ.get("SUDO_USER") or pwd.getpwuid(config.stat().st_uid).pw_name
    except (FileNotFoundError, KeyError):
        service_user = os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name
    definitions: dict[str, tuple[Path, str, int]] = {
        "systemd": (Path("/etc/systemd/system/ghgoyifier.service"), f"[Unit]\nDescription=GhGoyifier Telegram GitHub gateway\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nUser={service_user}\nWorkingDirectory={root}\nExecStart={python} -m GhGoyifier --config {config}\nRestart=on-failure\nRestartSec=5\nNoNewPrivileges=true\n\n[Install]\nWantedBy=multi-user.target\n", 0o644),
        "runit": (Path("/etc/service/ghgoyifier/run"), f"#!/bin/sh\nexec {python} -m GhGoyifier --config {config}\n", 0o755),
        "dinit": (Path("/etc/dinit.d/ghgoyifier"), f"command = {python} -m GhGoyifier --config {config}\nrestart = true\n", 0o644),
        "openrc": (Path("/etc/init.d/ghgoyifier"), f"#!/sbin/openrc-run\ncommand={python}\ncommand_args=\"-m GhGoyifier --config {config}\n\"\ncommand_background=true\npidfile=\"/run/${{RC_SVCNAME}}.pid\"\n\ndepend() {{\n    need net\n}}\n", 0o755),
        "sysvinit": (Path("/etc/init.d/ghgoyifier"), f"#!/bin/sh\ncase \"$1\" in\nstart) start-stop-daemon --start --background --make-pidfile --pidfile /run/ghgoyifier.pid --exec {python} -- -m GhGoyifier --config {config} ;;\nstop) start-stop-daemon --stop --pidfile /run/ghgoyifier.pid --retry TERM/30/KILL/5 ;;\nrestart) $0 stop; $0 start ;;\n*) exit 1 ;;\nesac\n", 0o755),
        "upstart": (Path("/etc/init/ghgoyifier.conf"), f"description \"GhGoyifier gateway\"\nstart on filesystem\nstop on runlevel [016]\nrespawn\nexec {python} -m GhGoyifier --config {config}\n", 0o644),
        "s6": (Path("/etc/s6/sv/ghgoyifier/run"), f"#!/bin/execlineb -P\n{python}\n-m\nGhGoyifier\n--config\n{config}\n", 0o755),
    }
    definition = definitions.get(init)
    if definition is None:
        return 0, f"init={init} uses direct supervised mode; no portable native service definition exists"
    path, content, mode = definition
    try:
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(content)
        temporary.chmod(mode)
        temporary.replace(path)
        if init == "systemd":
            subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        return 0, f"installed {init} service at {path}"
    except PermissionError:
        return 1, f"cannot install {init} service at {path}: root privileges required"


def uninstall_service(init: str | None = None) -> tuple[int, str]:
    init = init or detect_init()
    paths = {
        "systemd": Path("/etc/systemd/system/ghgoyifier.service"),
        "runit": Path("/etc/service/ghgoyifier/run"),
        "dinit": Path("/etc/dinit.d/ghgoyifier"),
        "openrc": Path("/etc/init.d/ghgoyifier"),
        "sysvinit": Path("/etc/init.d/ghgoyifier"),
        "upstart": Path("/etc/init/ghgoyifier.conf"),
        "s6": Path("/etc/s6/sv/ghgoyifier/run"),
    }
    path = paths.get(init)
    if path is None:
        return 0, f"init={init} has no native service definition to remove"
    try:
        if init == "systemd":
            subprocess.run(["systemctl", "disable", "--now", service], check=False, capture_output=True)
        if path.exists() or path.is_symlink():
            path.unlink()
        if init == "systemd":
            subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        return 0, f"removed {init} service definition at {path}"
    except PermissionError:
        return 1, f"cannot remove {init} service at {path}: root privileges required"


def run(action: str, init: str | None = None) -> tuple[int, str]:
    init = init or detect_init()
    if action == "install":
        return install_service(init)
    if action == "uninstall":
        run("stop", init)
        code, message = uninstall_service(init)
        pidfile.unlink(missing_ok=True)
        logfile.unlink(missing_ok=True)
        return code, message
    if action == "status":
        if init == "systemd":
            result = subprocess.run(["systemctl", "is-active", service], text=True, capture_output=True)
            return result.returncode, f"init={init} status={result.stdout.strip() or 'inactive'}"
        if pidfile.exists():
            try:
                pid = int(pidfile.read_text().strip())
                os.kill(pid, 0)
                return 0, f"init={init} status=active pid={pid}"
            except (ValueError, ProcessLookupError, PermissionError):
                pidfile.unlink(missing_ok=True)
        return 3, f"init={init} status=inactive"
    command: list[str] | None = None
    if action in {"start", "restart", "stop", "enable", "disable"}:
        command = _command(action, init)
        if command:
            try:
                result = subprocess.run(command, text=True, capture_output=True)
            except FileNotFoundError:
                command = None
            else:
                return result.returncode, (result.stdout + result.stderr).strip()
    if init != "systemd" and not command:
        if action in {"start", "restart"}:
            if action == "restart":
                run("stop", init)
            logfile.parent.mkdir(parents=True, exist_ok=True)
            log = logfile.open("ab")
            process = subprocess.Popen(["python3", "-m", "GhGoyifier", "--config", str(root / "config.toml")], cwd=root, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            pidfile.parent.mkdir(parents=True, exist_ok=True)
            pidfile.write_text(str(process.pid))
            return 0, f"init={init} started pid={process.pid}"
        if action == "stop":
            return _stop_direct(init)
        if action in {"enable", "disable"}:
            return 0, f"init={init} {action}=not-applicable"
    return 2, f"init={init} does not provide an installed service backend for {action}"


def _stop_direct(init: str) -> tuple[int, str]:
    if not pidfile.exists():
        return 3, f"init={init} status=inactive"
    try:
        pid = int(pidfile.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pidfile.unlink(missing_ok=True)
        return 0, f"init={init} stopped pid={pid}"
    except (ValueError, ProcessLookupError):
        pidfile.unlink(missing_ok=True)
        return 3, f"init={init} status=inactive"
