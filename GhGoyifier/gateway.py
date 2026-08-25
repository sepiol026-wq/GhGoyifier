# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import os
import pwd
import shutil
import signal
import subprocess
import time
from pathlib import Path

service = "ghgoyifier"
root = Path(__file__).resolve().parent.parent
_runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or str(Path.home() / ".cache")
pidfile = Path(os.environ.get("GHGOYIFIER_PIDFILE", str(Path(_runtime_dir) / "ghgoyifier.pid")))
logfile = Path(os.environ.get("GHGOYIFIER_LOG", str(root / "ghgoyifier.log")))

_native = {"systemd", "runit", "dinit", "openrc", "sysvinit", "upstart", "s6"}
_supervised = {"direct", "busybox", "dumb-init", "minit", "tiny", "epoch", "finit"}


def detect_init() -> str:
    override = os.environ.get("GHGOYIFIER_INIT", "").strip().lower()
    if override in _native | _supervised:
        return override
    if shutil.which("systemctl") and Path("/run/systemd/system").exists():
        return "systemd"
    for name, marker in (("dinit", "/run/dinitctl"), ("runit", "/etc/service"), ("openrc", "/run/openrc"), ("s6", "/run/s6"), ("upstart", "/var/run/upstart")):
        if shutil.which(name) or Path(marker).exists():
            return name
    for name in ("sv", "supervise", "rc-service", "s6-svc", "initctl", "dinitctl"):
        if shutil.which(name):
            return {"sv": "runit", "supervise": "runit", "rc-service": "openrc", "s6-svc": "s6", "initctl": "upstart", "dinitctl": "dinit"}[name]
    for name in ("busybox", "dumb-init", "minit", "tiny-init", "epoch", "finit"):
        if shutil.which(name):
            return name.replace("-init", "")
    return "direct"


def _service_path(init: str) -> Path | None:
    return {
        "systemd": Path("/etc/systemd/system/ghgoyifier.service"),
        "runit": Path("/etc/service/ghgoyifier/run"),
        "dinit": Path("/etc/dinit.d/ghgoyifier"),
        "openrc": Path("/etc/init.d/ghgoyifier"),
        "sysvinit": Path("/etc/init.d/ghgoyifier"),
        "upstart": Path("/etc/init/ghgoyifier.conf"),
        "s6": Path("/etc/s6/sv/ghgoyifier/run"),
    }.get(init)


def _command(action: str, init: str) -> list[str] | None:
    path = _service_path(init)
    if init == "systemd":
        return ["systemctl", action, service]
    if init == "runit" and action in {"start", "stop", "restart"}:
        return ["sv", action, str(path.parent)] if path else None
    if init == "dinit":
        return ["dinitctl", action, service] if action in {"start", "stop", "restart", "status", "enable", "disable"} else None
    if init == "openrc":
        if action == "enable":
            return ["rc-update", "add", service, "default"]
        if action == "disable":
            return ["rc-update", "del", service, "default"]
        return ["rc-service", service, action]
    if init == "sysvinit":
        if action == "enable":
            return ["update-rc.d", service, "defaults"]
        if action == "disable":
            return ["update-rc.d", "-f", service, "remove"]
        return [str(path), action] if path else None
    if init == "upstart":
        return ["initctl", action, service] if action in {"start", "stop", "restart", "status"} else None
    if init == "s6":
        if action in {"start", "enable"}:
            return ["s6-svc", "-u", "/run/service/ghgoyifier"]
        if action in {"stop", "disable"}:
            return ["s6-svc", "-d", "/run/service/ghgoyifier"]
        if action == "restart":
            return ["s6-svc", "-r", "/run/service/ghgoyifier"]
        if action == "status" and shutil.which("s6-svstat"):
            return ["s6-svstat", "/run/service/ghgoyifier"]
    return None


def _service_python() -> str:
    candidate = root / ".venv" / "bin" / "python"
    return str(candidate if candidate.exists() else Path("python3"))


def _service_user() -> str:
    config = root / "config.toml"
    try:
        return pwd.getpwuid(config.stat().st_uid).pw_name
    except (FileNotFoundError, KeyError, OSError):
        return os.environ.get("SUDO_USER") or os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name


def _definition(init: str) -> tuple[Path, str, int] | None:
    python = _service_python()
    config = root / "config.toml"
    user = _service_user()
    qroot = str(root)
    qpython = str(python)
    qconfig = str(config)
    definitions = {
        "systemd": (Path("/etc/systemd/system/ghgoyifier.service"), f"[Unit]\nDescription=GhGoyifier Telegram GitHub gateway\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nUser={user}\nEnvironmentFile=-/etc/environment\nEnvironmentFile=-%h/.config/environment.d/90-goyifier-proxy.conf\nWorkingDirectory={qroot}\nExecStart={qpython} -m GhGoyifier --config {qconfig}\nRestart=on-failure\nRestartSec=5\nNoNewPrivileges=true\n\n[Install]\nWantedBy=multi-user.target\n", 0o644),
        "runit": (Path("/etc/service/ghgoyifier/run"), f"#!/bin/sh\nexec {qpython} -m GhGoyifier --config {qconfig}\n", 0o755),
        "dinit": (Path("/etc/dinit.d/ghgoyifier"), f"command = {qpython} -m GhGoyifier --config {qconfig}\nworking-dir = {qroot}\nuser = {user}\nrestart = true\n", 0o644),
        "openrc": (Path("/etc/init.d/ghgoyifier"), f"#!/sbin/openrc-run\ncommand={qpython}\ncommand_args=\"-m GhGoyifier --config {qconfig}\"\ncommand_user=\"{user}\"\ncommand_background=true\npidfile=\"/run/${{RC_SVCNAME}}.pid\"\noutput_log=\"{root / 'ghgoyifier.log'}\"\nerror_log=\"{root / 'ghgoyifier.log'}\"\n\ndepend() {{\n    need net\n}}\n", 0o755),
        "sysvinit": (Path("/etc/init.d/ghgoyifier"), f"#!/bin/sh\nPYTHON={qpython}\nCONFIG={qconfig}\nROOT={qroot}\nPIDFILE=/run/ghgoyifier.pid\nUSER={user}\ncase \"$1\" in\nstart) start-stop-daemon --start --background --make-pidfile --pidfile \"$PIDFILE\" --chuid \"$USER\" --chdir \"$ROOT\" --exec \"$PYTHON\" -- -m GhGoyifier --config \"$CONFIG\" ;;\nstop) start-stop-daemon --stop --pidfile \"$PIDFILE\" --retry TERM/30/KILL/5 ;;\nrestart) \"$0\" stop; \"$0\" start ;;\nstatus) test -f \"$PIDFILE\" && kill -0 \"$(cat \"$PIDFILE\")\" ;;\n*) exit 2 ;;\nesac\n", 0o755),
        "upstart": (Path("/etc/init/ghgoyifier.conf"), f"description \"GhGoyifier gateway\"\nstart on started networking\nstop on runlevel [016]\nrespawn\nsetuid {user}\nchdir {qroot}\nexec {qpython} -m GhGoyifier --config {qconfig}\n", 0o644),
        "s6": (Path("/etc/s6/sv/ghgoyifier/run"), f"#!/bin/execlineb -P\ns6-setuidgid {user}\nfdmove -c 2 1\ncd {qroot}\n{qpython}\n-m\nGhGoyifier\n--config\n{qconfig}\n", 0o755),
    }
    return definitions.get(init)


def install_service(init: str | None = None) -> tuple[int, str]:
    init = init or detect_init()
    definition = _definition(init)
    if definition is None:
        return 0, f"init={init} uses direct supervised mode; start/stop/restart/status are available, enable/disable is not applicable"
    path, content, mode = definition
    try:
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
        temporary.write_text(content)
        temporary.chmod(mode)
        temporary.replace(path)
        if init == "systemd":
            subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        return 0, f"installed {init} service at {path} for user {_service_user()}"
    except PermissionError:
        return 1, f"cannot install {init} service at {path}: root privileges required"
    except OSError as exc:
        return 1, f"cannot install {init} service at {path}: {type(exc).__name__}"


def uninstall_service(init: str | None = None) -> tuple[int, str]:
    init = init or detect_init()
    path = _service_path(init)
    if path is None:
        return 0, f"init={init} uses direct supervised mode; no native service definition to remove"
    try:
        command = _command("disable", init)
        if command:
            subprocess.run(command, check=False, capture_output=True)
        if init == "systemd":
            subprocess.run(["systemctl", "disable", "--now", service], check=False, capture_output=True)
        if path.exists() or path.is_symlink():
            path.unlink()
        if init == "systemd":
            subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        return 0, f"removed {init} service definition at {path}"
    except PermissionError:
        return 1, f"cannot remove {init} service at {path}: root privileges required"
    except OSError as exc:
        return 1, f"cannot remove {init} service at {path}: {type(exc).__name__}"


def _direct_start() -> tuple[int, str]:
    if pidfile.exists():
        try:
            pid = int(pidfile.read_text().strip())
            os.kill(pid, 0)
            return 0, f"direct supervised gateway already active pid={pid}"
        except (ValueError, ProcessLookupError, PermissionError):
            pidfile.unlink(missing_ok=True)
    logfile.parent.mkdir(parents=True, exist_ok=True)
    log = logfile.open("ab")
    process = subprocess.Popen([_service_python(), "-m", "GhGoyifier", "--config", str(root / "config.toml")], cwd=root, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(str(process.pid)
    )
    pidfile.chmod(0o600)
    return 0, f"direct supervised gateway started pid={process.pid}"


def _stop_direct() -> tuple[int, str]:
    if not pidfile.exists():
        return 3, "direct supervised gateway is inactive"
    try:
        pid = int(pidfile.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.2)
        else:
            os.kill(pid, signal.SIGKILL)
        pidfile.unlink(missing_ok=True)
        return 0, f"direct supervised gateway stopped pid={pid}"
    except (ValueError, ProcessLookupError, PermissionError):
        pidfile.unlink(missing_ok=True)
        return 3, "direct supervised gateway is inactive"


def _direct_status(init: str) -> tuple[int, str]:
    if not pidfile.exists():
        return 3, f"init={init} status=inactive"
    try:
        pid = int(pidfile.read_text().strip())
        os.kill(pid, 0)
        return 0, f"init={init} status=active pid={pid} supervised=true"
    except (ValueError, ProcessLookupError, PermissionError):
        pidfile.unlink(missing_ok=True)
        return 3, f"init={init} status=inactive"


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
    if init in _supervised or init == "direct":
        if action in {"start", "restart"}:
            if action == "restart":
                _stop_direct()
            return _direct_start()
        if action == "stop":
            return _stop_direct()
        if action == "status":
            return _direct_status(init)
        if action in {"enable", "disable"}:
            return 0, f"init={init} {action}=not-applicable (direct supervised mode)"
    if action == "status" and init == "systemd":
        try:
            result = subprocess.run(["systemctl", "is-active", service], text=True, capture_output=True)
        except FileNotFoundError:
            return _direct_status(init)
        return result.returncode, f"init={init} status={result.stdout.strip() or 'inactive'}"
    command = _command(action, init)
    if command:
        try:
            result = subprocess.run(command, text=True, capture_output=True)
        except FileNotFoundError:
            return _direct_status(init) if action == "status" else _direct_start() if action in {"start", "restart"} else (2, f"init={init} command unavailable for {action}")
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output or ("ok" if result.returncode == 0 else f"init={init} {action} failed")
    if action in {"start", "restart"}:
        if action == "restart":
            _stop_direct()
        return _direct_start()
    if action == "stop":
        return _stop_direct()
    if action == "status":
        return _direct_status(init)
    if action in {"enable", "disable"}:
        return 0, f"init={init} {action}=not-applicable (no stable native control API)"
    return 2, f"init={init} does not provide a service backend for {action}"
