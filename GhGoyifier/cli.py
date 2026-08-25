# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import pwd
import sqlite3
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import toml
import aiohttp
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from GhGoyifier.config import Config, parse_config
from GhGoyifier.gateway import detect_init, logfile, run
from GhGoyifier.proxy import _masked_url, validate_url

console = Console()
default_config = os.environ.get("GHGOYIFIER_CONFIG", "config.toml")
sensitive = {"bot.token", "database.password", "github_app.webhook_secret", "GOYIFIER_DATA_KEY"}


def _version(root: Path | None = None) -> str:
    target = root or Path(__file__).resolve().parent.parent
    version_file = target / "VERSION"
    return version_file.read_text().strip() if version_file.exists() else "0.0.0"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)


def update_command(args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parent.parent
    if not (root / ".git").exists():
        console.print("[red]Update requires a Git checkout.[/red]")
        return 1
    remote = "origin"
    origin_url = _git(root, "remote", "get-url", "origin").stdout.strip()
    if "GhGoyifier" not in origin_url:
        candidate = _git(root, "remote", "get-url", "ghgoyifier")
        if candidate.returncode == 0:
            remote = "ghgoyifier"
    branch = "main"
    fetched = _git(root, "fetch", "--prune", remote, branch)
    if fetched.returncode:
        console.print(f"[red]Could not fetch updates:[/red] {fetched.stderr.strip()}")
        return 1
    target = f"{remote}/{branch}"
    local_sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    remote_sha = _git(root, "rev-parse", target).stdout.strip()
    if local_sha == remote_sha:
        console.print(f"[green]Already up to date.[/green] version={_version(root)} commit={local_sha[:12]}")
        return 0
    dirty = _git(root, "diff", "--quiet").returncode or _git(root, "diff", "--cached", "--quiet").returncode
    if dirty:
        console.print("[red]Tracked local changes detected; update cancelled to protect them.[/red]")
        return 1
    counts = _git(root, "rev-list", "--left-right", "--count", f"HEAD...{target}").stdout.strip().split()
    behind = counts[1] if len(counts) == 2 else "?"
    old_version = _version(root)
    merged = _git(root, "merge", "--ff-only", target)
    if merged.returncode:
        console.print(f"[red]Fast-forward update failed:[/red] {merged.stderr.strip()}")
        return 1
    new_version = _version(root)
    python = root / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)
    if shutil.which("uv"):
        install = subprocess.run(["uv", "pip", "install", "--python", str(python), "-r", "requirements.txt"], cwd=root, text=True, capture_output=True)
    else:
        install = subprocess.run([str(python), "-m", "pip", "install", "-r", "requirements.txt"], cwd=root, text=True, capture_output=True)
    checks = subprocess.run([str(python), "-m", "compileall", "-q", "GhGoyifier"], cwd=root, text=True, capture_output=True)
    if install.returncode or checks.returncode:
        _git(root, "reset", "--hard", local_sha)
        run("restart")
        detail = (install.stderr or checks.stderr).strip()
        console.print(f"[red]Update validation failed; rolled back.[/red] {detail}")
        return 1
    service_code, service_message = run("install")
    if service_code:
        _git(root, "reset", "--hard", local_sha)
        run("restart")
        console.print(f"[red]Gateway service installation failed; rolled back.[/red] {service_message}")
        return 1
    code, message = run("restart")
    if code:
        _git(root, "reset", "--hard", local_sha)
        run("restart")
        console.print(f"[red]Gateway restart failed; rolled back.[/red] {message}")
        return 1
    console.print(f"[green]Updated and restarted gateway.[/green] {old_version} → {new_version}, commits behind={behind}")
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parent.parent
    resolved = root.resolve()
    home = Path.home().resolve()
    if resolved in {Path("/").resolve(), home} or resolved.name.lower() != "ghgoyifier":
        console.print("[red]Refusing full uninstall: this is not an isolated GhGoyifier installation directory.[/red]")
        console.print(f"[yellow]Detected directory:[/yellow] {resolved}")
        return 1
    if not args.yes and not Confirm.ask(f"Delete the entire GhGoyifier installation at {resolved}?", default=False):
        console.print("Uninstall cancelled.")
        return 0
    backup = resolved.parent / f"GhGoyifier-uninstall-backup-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.tar.gz"
    if args.backup:
        with tarfile.open(backup, "w:gz") as archive:
            def include(item: Path) -> bool:
                return ".venv" not in item.parts and ".git" not in item.parts and "__pycache__" not in item.parts
            archive.add(resolved, arcname=resolved.name, recursive=True, filter=lambda info: info if include(Path(info.name)) else None)
        backup.chmod(0o600)
    code, message = run("uninstall")
    if code:
        console.print(f"[red]Gateway uninstall failed; application was preserved.[/red] {message}")
        return code
    bin_dir = Path(os.environ.get("GHGOYIFIER_BIN", str(home / ".local" / "bin"))).expanduser()
    for name in ("ghgoyifi", "ghgoyifier", "GhGoyifier"):
        candidate = bin_dir / name
        if candidate.is_symlink():
            target = candidate.resolve(strict=False)
            if target == resolved / ".venv" / "bin" / "ghgoyifi" or name != "ghgoyifi":
                candidate.unlink(missing_ok=True)
        elif candidate.is_file():
            try:
                if str(resolved) in candidate.read_text(errors="ignore"):
                    candidate.unlink()
            except OSError:
                pass
    shutil.rmtree(resolved)
    detail = f" removed; backup={backup}" if args.backup else " removed; no backup created"
    console.print(f"[green]GhGoyifier fully uninstalled.[/green]{detail}")
    return 0


def _set_value(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _remove_value(data: dict[str, Any], path: str) -> bool:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return bool(isinstance(current, dict) and current.pop(parts[-1], None) is not None)


def _coerce(value: str) -> Any:
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _write(path: str, data: dict[str, Any]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.is_symlink():
        raise RuntimeError(f"refusing to write symlink config: {target}")
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(toml.dumps(data))
    temporary.chmod(0o600)
    temporary.replace(target)
    target.chmod(0o600)


def _proxy_config_path(path: str, root: Path) -> Path:
    target = Path(path).expanduser()
    return target if target.is_absolute() else root / target


def _proxy_save(path: Path, data: dict[str, Any]) -> None:
    _write(str(path), data)


async def _test_proxy_url(url: str) -> tuple[bool, str]:
    parsed = urlsplit(url)
    try:
        if parsed.scheme.lower().startswith("socks"):
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(url)
            async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=8), trust_env=False) as session:
                async with session.get("https://api.telegram.org") as response:
                    return True, f"HTTP {response.status}"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8), trust_env=False) as session:
            async with session.get("https://api.telegram.org", proxy=url) as response:
                return True, f"HTTP {response.status}"
    except Exception as exc:
        return False, type(exc).__name__


def proxy_command(args: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parent.parent
    path = _proxy_config_path(args.file, root)
    data = toml.load(path) if path.exists() else {}
    section = data.setdefault("proxy", {})
    profiles = section.setdefault("profiles", [])
    action = args.params[0] if args.params else "list"
    if action == "list":
        table = Table(title="GhGoyifier proxy profiles")
        for column in ("Name", "Scheme", "Priority", "State", "Active", "URL"):
            table.add_column(column)
        active = str(section.get("active") or "")
        for item in sorted(profiles, key=lambda value: (int(value.get("priority", 100)), str(value.get("name", "")))):
            url = str(item.get("url", ""))
            table.add_row(str(item.get("name", "")), urlsplit(url).scheme, str(item.get("priority", 100)), "on" if item.get("enabled", True) else "off", "yes" if item.get("name") == active else "", _masked_url(url))
        console.print(table)
        console.print(f"auto={'on' if section.get('auto', True) else 'off'} active={active or 'system'} fallback_count={len(profiles)}")
        return 0
    if action == "add":
        if len(args.params) != 3:
            console.print("[red]Usage:[/red] proxy add NAME URL")
            return 2
        name = args.params[1]
        try:
            url = validate_url(args.params[2])
        except ValueError as exc:
            console.print(f"[red]Invalid proxy URL:[/red] {exc}")
            return 2
        profiles[:] = [item for item in profiles if item.get("name") != name]
        profiles.append({"name": name, "url": url, "enabled": True, "priority": args.priority})
        _proxy_save(path, data)
        console.print(f"[green]Added proxy profile:[/green] {name}")
        return 0
    if action in {"remove", "use", "enable", "disable"}:
        if len(args.params) != 2:
            console.print(f"[red]Usage:[/red] proxy {action} NAME")
            return 2
        name = args.params[1]
        item = next((value for value in profiles if value.get("name") == name), None)
        if item is None:
            console.print(f"[red]Proxy profile not found:[/red] {name}")
            return 1
        if action == "remove":
            profiles.remove(item)
            if section.get("active") == name:
                section["active"] = ""
        elif action == "use":
            section["active"] = name
            section["auto"] = True
        else:
            item["enabled"] = action == "enable"
        _proxy_save(path, data)
        console.print(f"[green]Proxy profile updated:[/green] {name}")
        return 0
    if action == "clear":
        profiles.clear()
        section["active"] = ""
        _proxy_save(path, data)
        console.print("[green]Proxy profiles cleared.[/green]")
        return 0
    if action == "auto":
        if len(args.params) != 2 or args.params[1] not in {"on", "off"}:
            console.print("[red]Usage:[/red] proxy auto on|off")
            return 2
        section["auto"] = args.params[1] == "on"
        _proxy_save(path, data)
        console.print(f"[green]Automatic system proxy:[/green] {args.params[1]}")
        return 0
    if action == "test":
        names = [args.params[1]] if len(args.params) > 1 else [item.get("name") for item in profiles if item.get("enabled", True)]
        if args.all:
            names = [item.get("name") for item in profiles]
        selected = [item for item in profiles if item.get("name") in names]
        if not selected:
            console.print("[yellow]No proxy profiles selected.[/yellow]")
            return 1
        failures = 0
        for item in selected:
            ok, detail = asyncio.run(_test_proxy_url(str(item["url"])))
            console.print(f"{'[green]OK[/green]' if ok else '[red]FAIL[/red]'} {item['name']}: {_masked_url(str(item['url']))} ({detail})")
            failures += not ok
        return int(bool(failures))
    console.print(f"[red]Unknown proxy action:[/red] {action}")
    return 2


def configure(path: str) -> int:
    target = Path(path).expanduser()
    data = toml.load(target) if target.exists() else {}
    defaults = {
        "bot": {},
        "database": {"models": ["GhGoyifier.db.functions", "aerich.models"], "protocol": "sqlite", "file_name": "production-database.sqlite3"},
        "settings": {"throttling_rate": 0.5, "drop_pending_updates": True, "buttons": "inline"},
        "api": {"id": 2040, "hash": "b18441a1ff607e10a989891a5462e627", "bot_api_url": "https://api.telegram.org", "host": "localhost:4454"},
        "notifications": {"mode": "polling", "poll_interval": 30, "none_auth_perm": False},
        "proxy": {"auto": True, "active": "", "profiles": []},
        "github_app": {"app_id": 0, "slug": "", "private_key_path": "", "webhook_secret": ""},
    }
    for section, values in defaults.items():
        data.setdefault(section, {})
        for key, value in values.items():
            data[section].setdefault(key, value)
    console.print(Panel.fit("[bold cyan]GhGoyifier setup[/bold cyan]\nOnly operator-important settings are requested. Technical defaults are configured automatically.\nPress Enter to keep a value; secrets are never displayed.", border_style="cyan"))

    def operator_input(prompt: str) -> str:
        try:
            with open("/dev/tty") as stream:
                print(prompt, end="", flush=True)
                return stream.readline().rstrip("\n")
        except OSError:
            return console.input(prompt)

    def default_input(label: str, current: str) -> str:
        value = operator_input(f"{label} ({current}): ")
        return value.strip() or current

    def text(section: str, key: str, label: str, secret: bool = False, default: str = "") -> None:
        current = str(data[section].get(key, default))
        if secret:
            value = getpass.getpass(label + " (hidden; Enter keeps current): ")
        else:
            value = default_input(label, current) if current else operator_input(f"{label}: ")
        if value != "":
            _set_value(data, f"{section}.{key}", _coerce(value))

    def number(section: str, key: str, label: str, default: float) -> None:
        current = str(data[section].get(key, default))
        value = default_input(label, current)
        _set_value(data, f"{section}.{key}", _coerce(value))

    def boolean(section: str, key: str, label: str, default: bool) -> None:
        current = bool(data[section].get(key, default))
        while True:
            value = operator_input(f"{label} [{'Y/n' if current else 'y/N'}]: ").strip().lower()
            if not value:
                _set_value(data, f"{section}.{key}", current)
                return
            if value in {"y", "yes"}:
                _set_value(data, f"{section}.{key}", True)
                return
            if value in {"n", "no"}:
                _set_value(data, f"{section}.{key}", False)
                return
            console.print("[yellow]Please enter Y or N.[/yellow]")

    console.print("\n[bold]1/4 · Telegram bot[/bold]")
    text("bot", "token", "Telegram Bot API token", True)
    console.print("\n[bold]2/4 · Bot behavior[/bold]")
    number("settings", "owner_id", "Owner Telegram user ID", 0)
    current_buttons = str(data["settings"].get("buttons", "inline"))
    button_value = default_input("Button type (inline/in-msg)", current_buttons)
    while button_value not in {"inline", "in-msg"}:
        console.print("[yellow]Please select inline or in-msg.[/yellow]")
        button_value = default_input("Button type (inline/in-msg)", current_buttons)
    data["settings"]["buttons"] = button_value
    console.print("\n[bold]3/4 · GitHub notifications[/bold]")
    number("notifications", "poll_interval", "Polling interval in seconds", 30)
    boolean("notifications", "none_auth_perm", "Allow anonymous access to public repositories?", False)
    console.print("\n[bold]4/4 · Optional GitHub App[/bold]")
    app_enabled = operator_input(f"Configure a GitHub App now? [{'Y/n' if data['github_app'].get('app_id') else 'y/N'}]: ").strip().lower()
    if app_enabled in {"y", "yes"} or (not app_enabled and data["github_app"].get("app_id")):
        number("github_app", "app_id", "GitHub App ID", 0)
        text("github_app", "slug", "GitHub App slug", False)
        text("github_app", "private_key_path", "GitHub App private key path", False)
        text("github_app", "webhook_secret", "GitHub App webhook secret", True)
    elif app_enabled in {"n", "no", ""}:
        data["github_app"] = {"app_id": 0, "slug": "", "private_key_path": "", "webhook_secret": ""}
    else:
        console.print("[yellow]Please enter Y or N.[/yellow]")
        return configure(path)
    try:
        Config.model_validate(data)
    except Exception as exc:
        console.print(f"[red]Configuration is incomplete or invalid:[/red] {exc}")
        return 1
    _write(path, data)
    console.print(f"[green]Saved secure config:[/green] {target}")
    return 0


def config_command(args: argparse.Namespace) -> int:
    path = args.file
    params = args.params
    action = params[0] if params else None
    key = params[1] if len(params) > 1 else None
    value = params[2] if len(params) > 2 else None
    if action == "set":
        data = toml.load(path) if Path(path).exists() else {}
        _set_value(data, key, _coerce(value))
        _write(path, data)
        console.print(f"[green]Set[/green] {key}")
        return 0
    if action == "rm":
        data = toml.load(path)
        if not _remove_value(data, key):
            console.print(f"[yellow]Not found:[/yellow] {key}")
            return 1
        _write(path, data)
        console.print(f"[green]Removed[/green] {key}")
        return 0
    return configure(path)


def logs_command(args: argparse.Namespace) -> int:
    if detect_init() == "systemd":
        if args.action == "follow":
            os.execvp("journalctl", ["journalctl", "-u", "ghgoyifier", "-n", str(args.lines), "-f"])
        if args.action == "show":
            result = subprocess.run(["journalctl", "-u", "ghgoyifier", "--no-pager", "-n", str(args.lines)], text=True, capture_output=True)
            if result.returncode == 0:
                console.print(result.stdout.rstrip())
            else:
                console.print(result.stderr.rstrip() or "No systemd log available.")
            return result.returncode
    path = Path(args.file)
    if args.action == "clear":
        path.unlink(missing_ok=True)
        console.print("[green]Logs cleared.[/green]")
        return 0
    if args.action == "show":
        if not path.exists():
            console.print("[yellow]No log file yet.[/yellow]")
            return 0
        lines = path.read_text(errors="replace").splitlines()[-args.lines:]
        console.print("\n".join(lines))
        return 0
    if args.action == "follow":
        os.execvp("tail", ["tail", "-n", str(args.lines), "-f", str(path)])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="GhGoyifier", description="GhGoyifier Telegram/GitHub gateway")
    parser.add_argument("--version", "-v", action="version", version=f"GhGoyifier {_version()}")
    sub = parser.add_subparsers(dest="command")
    config = sub.add_parser("config", help="configure and edit TOML settings")
    config.add_argument("params", nargs="*", metavar="ACTION [KEY] [VALUE]")
    config.add_argument("--file", "-f", default=default_config)
    config.set_defaults(func=config_command)
    gateway = sub.add_parser(
        "gateway",
        help="manage the GhGoyifier gateway service",
        description="Install, control, enable, inspect, or remove the GhGoyifier gateway service.",
        epilog="""Actions:
  install    Write or refresh the native service definition. Does not start it.
  start      Start the service now.
  restart    Stop and start the service now, loading the current code/config.
  enable     Enable automatic start at system boot.
  stop       Stop the service now without removing its definition.
  disable    Disable automatic start at system boot.
  status     Show whether the service is active and its process details.
  uninstall  Stop the service and remove its native service definition.

Examples:
  ghgoyifi gateway install
  ghgoyifi gateway enable
  ghgoyifi gateway start
  ghgoyifi gateway restart
  ghgoyifi gateway status

On systemd, install/enable/disable/uninstall may require sudo. The gateway
itself runs from the configured installation directory and is restarted by
the service manager when it exits unexpectedly.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    gateway.add_argument(
        "action",
        metavar="ACTION",
        choices=["install", "start", "restart", "enable", "stop", "disable", "status", "uninstall"],
        help="one of: install, start, restart, enable, stop, disable, status, uninstall",
    )
    gateway.set_defaults(func=lambda a: _gateway(a))
    logs = sub.add_parser("logs", help="inspect gateway logs")
    logs.add_argument("action", nargs="?", choices=["show", "follow", "clear"], default="show")
    logs.add_argument("--lines", type=int, default=100)
    logs.add_argument("--file", default=str(logfile))
    logs.set_defaults(func=logs_command)
    proxy = sub.add_parser(
        "proxy",
        help="manage automatic proxy profiles and fallbacks",
        description="Manage HTTP, HTTPS, SOCKS4, and SOCKS5 proxy profiles used by Telegram.",
        epilog="""Actions:
  list                         Show profiles and the active fallback order.
  add NAME URL [--priority N]  Add or replace a profile.
  remove NAME                  Remove a profile.
  use NAME                     Put a profile first in the fallback chain.
  enable NAME                  Enable a profile.
  disable NAME                 Disable a profile without deleting it.
  clear                        Remove all saved profiles.
  auto on|off                  Enable or disable system proxy autodetection.
  test [NAME]                  Test one profile or every enabled profile.
  test --all                   Test disabled profiles too.

URL schemes: http://, https://, socks4://, socks4a://, socks5://, socks5h://
Profiles are tried by priority after the selected profile. If a Telegram
request times out, the next enabled profile is selected automatically.
When no profile is selected and auto is on, the system proxy is used.

Examples:
  ghgoyifi proxy list
  ghgoyifi proxy add office-http http://127.0.0.1:8080 --priority 10
  ghgoyifi proxy add backup-socks socks5h://127.0.0.1:1080 --priority 20
  ghgoyifi proxy use office-http
  ghgoyifi proxy test --all
  ghgoyifi proxy auto on""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    proxy.add_argument("params", nargs="*", metavar="ACTION [ARGS]")
    proxy.add_argument("--priority", type=int, default=100, help="fallback priority; lower values are tried first")
    proxy.add_argument("--all", action="store_true", help="with test, include disabled profiles")
    proxy.add_argument("--file", "-f", default=default_config, help="configuration file")
    proxy.set_defaults(func=proxy_command)
    doctor = sub.add_parser("doctor", help="show runtime and init diagnostics")
    doctor.add_argument("--fix", action="store_true", help="repair safe local prerequisites")
    doctor.add_argument("--json", action="store_true", help="print machine-readable JSON")
    doctor.add_argument("--strict", action="store_true", help="treat warnings as failures")
    doctor.add_argument("--file", "-f", default=default_config)
    doctor.set_defaults(func=lambda a: _doctor(a.file, a.fix, a.json, a.strict))
    status = sub.add_parser("status", help="show gateway status")
    status.set_defaults(func=lambda a: _gateway(argparse.Namespace(action="status")))
    update = sub.add_parser("update", help="check, install, and restart available updates")
    update.set_defaults(func=update_command)
    uninstall = sub.add_parser("uninstall", help="backup and remove the isolated GhGoyifier installation")
    uninstall.add_argument("--yes", action="store_true", help="skip confirmation")
    uninstall.add_argument("--backup", action="store_true", help="create a recovery archive before removal")
    uninstall.set_defaults(func=uninstall_command)
    return parser


def _gateway(args: argparse.Namespace) -> int:
    code, message = run(args.action)
    console.print(Panel(message or "ok", title=f"gateway {args.action} / {detect_init()}", border_style="green" if code == 0 else "red"))
    return code


def _doctor(path: str = default_config, fix: bool = False, as_json: bool = False, strict: bool = False) -> int:
    root = Path(__file__).resolve().parent.parent
    config_path = Path(path).expanduser()
    if not config_path.is_absolute():
        config_path = root / config_path
    rows: list[tuple[str, str, str, str]] = []

    def add(check: str, target: str, status: str, detail: str) -> None:
        rows.append((check, target, status, detail))

    if fix:
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if config_path.exists() and not config_path.is_symlink():
            config_path.chmod(0o600)
    add("python", sys.executable, "ok" if sys.version_info >= (3, 10) else "fail", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    venv = root / ".venv" / "bin" / "python"
    if fix and not venv.exists():
        command = ["uv", "venv", "--python", sys.executable, str(root / ".venv")] if shutil.which("uv") else [sys.executable, "-m", "venv", str(root / ".venv")]
        subprocess.run(command, cwd=root, check=False, capture_output=True)
    add("venv", str(venv), "ok" if venv.is_file() and os.access(venv, os.X_OK) else "fail", "executable environment" if venv.exists() else "missing")
    valid = False
    if config_path.is_symlink():
        add("config.symlink", str(config_path), "fail", "symlink refused")
    elif not config_path.exists():
        add("config.exists", str(config_path), "fail", "file missing")
    else:
        mode = config_path.stat().st_mode & 0o777
        add("config.permissions", oct(mode), "ok" if mode == 0o600 else "warn", "private file" if mode == 0o600 else "expected 0o600")
        try:
            parse_config(str(config_path))
            valid = True
            add("config.parse", str(config_path), "ok", "validated by Config.model_validate")
        except Exception as exc:
            add("config.parse", str(config_path), "fail", type(exc).__name__)
    db_path = root / "production-database.sqlite3"
    if valid:
        try:
            configured = toml.load(config_path).get("database", {}).get("file_name")
            if configured and configured != ":memory:":
                db_path = Path(configured).expanduser()
                if not db_path.is_absolute():
                    db_path = root / db_path
        except Exception:
            pass
    if db_path.is_symlink():
        add("database.symlink", str(db_path), "fail", "symlink refused")
    elif db_path.exists():
        if fix:
            db_path.chmod(0o600)
        mode = db_path.stat().st_mode & 0o777
        add("database.permissions", oct(mode), "ok" if mode == 0o600 else "warn", "private file" if mode == 0o600 else "expected 0o600")
        try:
            with sqlite3.connect(db_path) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            add("database.integrity", str(db_path), "ok" if integrity == "ok" else "fail", str(integrity))
        except sqlite3.Error as exc:
            add("database.integrity", str(db_path), "fail", type(exc).__name__)
    else:
        add("database", str(db_path), "warn", "created on first gateway start")
    python = venv if venv.exists() else Path(sys.executable)
    if venv.exists():
        if fix:
            install_command = ["uv", "pip", "install", "--python", str(python), "-r", "requirements.txt"] if shutil.which("uv") else [str(python), "-m", "pip", "install", "-r", "requirements.txt"]
            subprocess.run(install_command, cwd=root, text=True, capture_output=True)
        if shutil.which("uv"):
            dependency = subprocess.run(["uv", "pip", "check", "--python", str(python)], cwd=root, text=True, capture_output=True)
        else:
            dependency = subprocess.run([str(python), "-m", "pip", "check"], cwd=root, text=True, capture_output=True)
        if fix and dependency.returncode:
            command = ["uv", "pip", "install", "--python", str(python), "-r", "requirements.txt"] if shutil.which("uv") else [str(python), "-m", "pip", "install", "-r", "requirements.txt"]
            dependency = subprocess.run(command, cwd=root, text=True, capture_output=True)
        add("dependencies", "requirements.txt", "ok" if dependency.returncode == 0 else "fail", "compatible" if dependency.returncode == 0 else "install/check failed")
    else:
        add("dependencies", "requirements.txt", "fail", "venv missing")
    compile_check = subprocess.run([str(python), "-m", "compileall", "-q", "GhGoyifier"], cwd=root, capture_output=True)
    add("compile", "GhGoyifier", "ok" if compile_check.returncode == 0 else "fail", "bytecode compilation")
    git_status = _git(root, "status", "--porcelain").stdout.strip()
    add("git.tree", "tracked worktree", "ok" if not git_status else "warn", "clean" if not git_status else "local changes present")
    requirements = root / "requirements.txt"
    add("requirements", str(requirements), "ok" if requirements.is_file() else "fail", "present" if requirements.is_file() else "file missing")
    try:
        free_bytes = shutil.disk_usage(root).free
        free_gb = free_bytes / 1024**3
        add("disk.free", str(root), "ok" if free_gb >= 0.5 else "warn", f"{free_gb:.2f} GiB available")
    except OSError as exc:
        add("disk.free", str(root), "warn", type(exc).__name__)
    if valid:
        try:
            raw_config = toml.load(config_path)
            token = str(raw_config.get("bot", {}).get("token") or "")
            bot_base = str(raw_config.get("api", {}).get("bot_api_url") or "https://api.telegram.org").rstrip("/")
            if token:
                request = urllib.request.Request(f"{bot_base}/bot{token}/getMe", headers={"User-Agent": "GhGoyifier-doctor"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode())
                api_ok = bool(payload.get("ok"))
                identity = (payload.get("result") or {}).get("username", "bot identity available")
                add("telegram.api", bot_base, "ok" if api_ok else "fail", str(identity))
            else:
                add("telegram.api", bot_base, "warn", "token not configured")
        except Exception as exc:
            add("telegram.api", "Bot API", "fail", type(exc).__name__)
        try:
            request = urllib.request.Request("https://api.github.com/rate_limit", headers={"User-Agent": "GhGoyifier-doctor", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(request, timeout=5) as response:
                github_status = response.status
            add("github.api", "https://api.github.com", "ok" if github_status == 200 else "warn", f"HTTP {github_status}")
        except Exception as exc:
            add("github.api", "https://api.github.com", "fail", type(exc).__name__)
    if db_path.exists() and db_path.suffix in {".sqlite", ".sqlite3", ".db"}:
        try:
            with sqlite3.connect(db_path) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                required = {"user", "chat", "eventsetting", "integration"}
                missing_tables = required - tables
                missing_columns = {}
                for table, column in (("user", "language"), ("chat", "language")):
                    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                    if column not in columns:
                        missing_columns[table] = column
            detail = "schema complete" if not missing_tables and not missing_columns else f"missing tables={sorted(missing_tables)} columns={missing_columns}"
            add("database.schema", str(db_path), "ok" if not missing_tables and not missing_columns else "fail", detail)
        except sqlite3.Error as exc:
            add("database.schema", str(db_path), "fail", type(exc).__name__)
    remote = "origin"
    origin_url = _git(root, "remote", "get-url", "origin").stdout.strip()
    if "GhGoyifier" not in origin_url:
        candidate = _git(root, "remote", "get-url", "ghgoyifier")
        if candidate.returncode == 0:
            remote = "ghgoyifier"
    fetched = _git(root, "fetch", "--dry-run", remote, "main")
    remote_ref = _git(root, "rev-parse", f"{remote}/main")
    if fetched.returncode == 0 and remote_ref.returncode == 0:
        local_ref = _git(root, "rev-parse", "HEAD").stdout.strip()
        remote_sha = remote_ref.stdout.strip()
        if local_ref == remote_sha:
            add("git.update", f"{remote}/main", "ok", "already up to date")
        else:
            counts = _git(root, "rev-list", "--left-right", "--count", f"HEAD...{remote}/main").stdout.strip().split()
            add("git.update", f"{remote}/main", "warn", f"update available ahead={counts[1] if len(counts) == 2 else '?'}")
    else:
        add("git.update", remote, "warn", "remote main unavailable")
    init = detect_init()
    owner_name = None
    owner_home = None
    for candidate in (config_path, db_path):
        if candidate.exists():
            try:
                owner = pwd.getpwuid(candidate.stat().st_uid)
                owner_name = owner.pw_name
                owner_home = Path(owner.pw_dir)
                break
            except (KeyError, OSError):
                pass
    if owner_name:
        add("installation.owner", str(config_path), "ok" if owner_name != "root" else "warn", f"owner={owner_name}")
    if init == "systemd":
        service_path = Path("/etc/systemd/system/ghgoyifier.service")
        add("gateway.definition", str(service_path), "ok" if service_path.exists() else "fail", "service definition present" if service_path.exists() else "not installed")
        if service_path.exists():
            try:
                unit = service_path.read_text(errors="replace")
                expected_user = owner_name or "unknown"
                unit_user = next((line.split("=", 1)[1].strip() for line in unit.splitlines() if line.startswith("User=")), "root")
                add("gateway.unit_user", str(service_path), "ok" if unit_user == expected_user else "fail", f"unit={unit_user} expected={expected_user}")
                proxy_files = [line.split("=", 1)[1].strip() for line in unit.splitlines() if line.startswith("EnvironmentFile=")]
                add("gateway.proxy_sources", str(service_path), "ok" if any("environment.d" in item for item in proxy_files) and any("/etc/environment" in item for item in proxy_files) else "warn", ", ".join(proxy_files) or "no EnvironmentFile")
            except OSError as exc:
                add("gateway.unit_read", str(service_path), "fail", type(exc).__name__)
            try:
                state = subprocess.run(["systemctl", "show", "ghgoyifier", "--no-pager", "--property=ActiveState,SubState,Result,MainPID,NRestarts,User"], text=True, capture_output=True, check=False)
                properties = dict(line.split("=", 1) for line in state.stdout.splitlines() if "=" in line)
                active = properties.get("ActiveState", "unknown")
                result = properties.get("Result", "unknown")
                status = "ok" if active == "active" and result in {"success", "exit-code"} else "fail" if active == "failed" or result not in {"success", "exit-code", "unknown"} else "warn"
                add("gateway.state", "ghgoyifier.service", status, f"active={active} sub={properties.get('SubState', 'unknown')} result={result}")
                restarts = int(properties.get("NRestarts", "0") or 0)
                add("gateway.restarts", "ghgoyifier.service", "ok" if restarts < 3 else "warn" if restarts < 10 else "fail", f"count={restarts}")
                add("gateway.runtime_user", "ghgoyifier.service", "ok" if properties.get("User") == owner_name else "fail", f"unit={properties.get('User', 'unknown')} expected={owner_name or 'unknown'}")
            except (OSError, ValueError) as exc:
                add("gateway.state", "ghgoyifier.service", "fail", type(exc).__name__)
    if owner_home:
        proxy_dir = owner_home / ".config" / "environment.d"
        proxy_file = proxy_dir / "90-goyifier-proxy.conf"
        if proxy_file.exists():
            mode = proxy_file.stat().st_mode & 0o777
            names = []
            for line in proxy_file.read_text(errors="replace").splitlines():
                if "=" in line:
                    names.append(line.split("=", 1)[0].strip())
            add("proxy.file", str(proxy_file), "ok" if mode == 0o600 else "warn", f"permissions={oct(mode)} variables={','.join(names) or 'none'}")
        else:
            add("proxy.file", str(proxy_file), "warn", "not found; relying on /etc/environment or live user environment")
    for command in ("ghgoyifi", "ghgoyifier", "GhGoyifier"):
        target = Path("/usr/local/bin") / command
        add("global.command", str(target), "ok" if target.exists() and os.access(target, os.X_OK) else "warn", "executable" if target.exists() else "missing")
    if db_path.exists() and db_path.suffix in {".sqlite", ".sqlite3", ".db"}:
        try:
            with sqlite3.connect(db_path) as connection:
                counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("user", "chat", "integration", "eventsetting") if table in {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}}
                add("database.records", str(db_path), "ok" if counts.get("integration", 0) else "warn", ", ".join(f"{key}={value}" for key, value in counts.items()))
                integrations = connection.execute("SELECT chat_id, repository_name FROM integration ORDER BY chat_id, repository_name").fetchall()
                add("database.integrations", str(db_path), "ok" if integrations else "warn", f"count={len(integrations)}")
                for chat_id, repository_name in integrations:
                    settings = connection.execute("SELECT COUNT(*) FROM eventsetting WHERE chat_id = ?", (chat_id,)).fetchone()[0]
                    add("database.integration", f"{chat_id}/{repository_name}", "ok" if settings >= 19 else "warn", f"event_settings={settings}/19")
        except sqlite3.Error as exc:
            add("database.records", str(db_path), "fail", type(exc).__name__)
    if init == "systemd":
        try:
            journal = subprocess.run(["journalctl", "-u", "ghgoyifier", "--no-pager", "-n", "200"], text=True, capture_output=True, check=False)
            recent = journal.stdout.splitlines()
            errors = sum("Traceback" in line or "ERROR" in line or "FAILURE" in line for line in recent)
            timeouts = sum("TimeoutError" in line or "timed out" in line.lower() for line in recent)
            add("gateway.journal", "ghgoyifier", "fail" if errors >= 3 else "warn" if errors else "ok", f"errors={errors} timeouts={timeouts}")
        except OSError as exc:
            add("gateway.journal", "ghgoyifier", "warn", type(exc).__name__)
    service_paths = {"systemd": Path("/etc/systemd/system/ghgoyifier.service"), "openrc": Path("/etc/init.d/ghgoyifier"), "sysvinit": Path("/etc/init.d/ghgoyifier")}
    if init:
        if init in service_paths:
            service_path = service_paths[init]
            if init != "systemd":
                add("gateway.definition", str(service_path), "ok" if service_path.exists() else "warn", "service definition present" if service_path.exists() else "not installed")
    try:
        process_list = subprocess.run(["ps", "-eo", "pid=,comm=,args="], text=True, capture_output=True, check=False)
        pids = []
        for line in process_list.stdout.splitlines():
            fields = line.strip().split(None, 2)
            if len(fields) == 3 and fields[0].isdigit() and int(fields[0]) != os.getpid() and Path(fields[1]).name.startswith("python") and " -m GhGoyifier" in fields[2]:
                pids.append(fields[0])
        status = "ok" if len(pids) == 1 else "fail" if len(pids) > 1 else "warn"
        detail = "process running" if len(pids) == 1 else f"duplicate processes={len(pids)}" if pids else "process not found"
        add("gateway.process", "GhGoyifier", status, detail)
    except FileNotFoundError:
        add("gateway.process", "GhGoyifier", "warn", "pgrep unavailable")
    if init == "systemd":
        add("gateway.logs", "journalctl -u ghgoyifier", "ok", "systemd journal is active log backend")
    elif logfile.exists():
        try:
            recent = logfile.read_text(errors="replace").splitlines()[-200:]
            errors = sum("ERROR" in line or "Traceback" in line for line in recent)
            add("gateway.logs", str(logfile), "warn" if errors else "ok", f"recent errors={errors}")
        except OSError as exc:
            add("gateway.logs", str(logfile), "warn", type(exc).__name__)
    else:
        add("gateway.logs", str(logfile), "warn", "log file not created yet")
    init = detect_init()
    if fix:
        service_code, service_message = run("install")
        add("gateway.service", init, "ok" if service_code == 0 else "warn", "installed" if service_code == 0 else service_message)
    else:
        status_code, status_message = run("status")
        add("gateway.status", init, "ok" if status_code == 0 else "warn", status_message)
    if as_json:
        print(json.dumps([{"check": check, "target": target, "status": status, "details": detail} for check, target, status, detail in rows], ensure_ascii=False))
    table = Table(title=f"GhGoyifier doctor{' --fix' if fix else ''}")
    table.add_column("Check")
    table.add_column("Target")
    table.add_column("Status")
    table.add_column("Details")
    for check, target, status, detail in rows:
        color = "green" if status == "ok" else "yellow" if status == "warn" else "red"
        table.add_row(check, target, f"[{color}]{status.upper()}[/{color}]", detail)
    if not as_json:
        console.print(table)
    failed = [check for check, _, status, _ in rows if status == "fail"]
    if failed and not as_json:
        console.print(f"[red]Unresolved checks:[/red] {', '.join(failed)}")
    warnings = [check for check, _, status, _ in rows if status == "warn"]
    return 1 if failed or (strict and warnings) else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    commands = {"config", "gateway", "logs", "doctor", "proxy", "status", "update", "uninstall"}
    if len(raw) >= 2 and raw[0] in {"-h", "--help"} and raw[1] in commands:
        raw = [raw[1], raw[0], *raw[2:]]
    if raw and raw[0] == "config":
        config_options: list[str] = []
        remaining: list[str] = [raw[0]]
        index = 1
        while index < len(raw):
            if raw[index] in {"--file", "-f"} and index + 1 < len(raw):
                config_options.extend(raw[index : index + 2])
                index += 2
                continue
            remaining.append(raw[index])
            index += 1
        raw = remaining + config_options
    args = parser.parse_args(raw)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    if args.command == "config" and args.params and args.params[0] not in {"set", "rm"}:
        parser.error("config accepts set, rm, or no action")
    if args.command == "config" and args.params and args.params[0] == "set" and len(args.params) != 3:
        parser.error("config set requires KEY VALUE")
    if args.command == "config" and args.params and args.params[0] == "rm" and len(args.params) != 2:
        parser.error("config rm requires KEY")
    return int(args.func(args))
