# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import toml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from GhGoyifier.config import Config
from GhGoyifier.gateway import detect_init, logfile, run

console = Console()
default_config = os.environ.get("GHGOYIFIER_CONFIG", "config.toml")
sensitive = {"bot.token", "database.password", "github_app.webhook_secret", "GOYIFIER_DATA_KEY"}


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


def configure(path: str) -> int:
    target = Path(path).expanduser()
    data = toml.load(target) if target.exists() else {}
    defaults = {
        "bot": {},
        "database": {"models": ["GhGoyifier.db.functions", "aerich.models"], "protocol": "sqlite", "file_name": "production-database.sqlite3"},
        "settings": {"throttling_rate": 0.5, "drop_pending_updates": True, "buttons": "inline"},
        "api": {"id": 2040, "hash": "b18441a1ff607e10a989891a5462e627", "bot_api_url": "https://api.telegram.org", "host": "localhost:4454"},
        "notifications": {"mode": "polling", "poll_interval": 30, "none_auth_perm": False},
        "github_app": {"app_id": 0, "slug": "", "private_key_path": "", "webhook_secret": ""},
    }
    for section, values in defaults.items():
        data.setdefault(section, {})
        for key, value in values.items():
            data[section].setdefault(key, value)
    console.print(Panel.fit("[bold cyan]GhGoyifier setup[/bold cyan]\nOnly operator-important settings are requested. Technical defaults are configured automatically.\nPress Enter to keep a value; secrets are never displayed.", border_style="cyan"))

    def text(section: str, key: str, label: str, secret: bool = False, default: str = "") -> None:
        current = str(data[section].get(key, default))
        if secret:
            value = Prompt.ask(label + " (hidden; Enter keeps current)", password=True, default="")
        else:
            value = Prompt.ask(label, default=current) if current else Prompt.ask(label)
        if value != "":
            _set_value(data, f"{section}.{key}", _coerce(value))

    def number(section: str, key: str, label: str, default: float) -> None:
        current = str(data[section].get(key, default))
        value = Prompt.ask(label, default=current)
        _set_value(data, f"{section}.{key}", _coerce(value))

    def boolean(section: str, key: str, label: str, default: bool) -> None:
        current = bool(data[section].get(key, default))
        _set_value(data, f"{section}.{key}", Confirm.ask(label, default=current))

    console.print("\n[bold]1/4 · Telegram bot[/bold]")
    text("bot", "token", "Telegram Bot API token", True)
    console.print("\n[bold]2/4 · Bot behavior[/bold]")
    number("settings", "owner_id", "Owner Telegram user ID", 0)
    current_buttons = str(data["settings"].get("buttons", "inline"))
    data["settings"]["buttons"] = Prompt.ask("Button type", choices=["inline", "in-msg"], default=current_buttons)
    console.print("\n[bold]3/4 · GitHub notifications[/bold]")
    number("notifications", "poll_interval", "Polling interval in seconds", 30)
    boolean("notifications", "none_auth_perm", "Allow anonymous access to public repositories?", False)
    console.print("\n[bold]4/4 · Optional GitHub App[/bold]")
    app_enabled = Confirm.ask("Configure a GitHub App now?", default=bool(data["github_app"].get("app_id")))
    if app_enabled:
        number("github_app", "app_id", "GitHub App ID", 0)
        text("github_app", "slug", "GitHub App slug", False)
        text("github_app", "private_key_path", "GitHub App private key path", False)
        text("github_app", "webhook_secret", "GitHub App webhook secret", True)
    else:
        data["github_app"] = {"app_id": 0, "slug": "", "private_key_path": "", "webhook_secret": ""}
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
    parser.add_argument("--version", action="version", version="GhGoyifier 1.0")
    sub = parser.add_subparsers(dest="command")
    config = sub.add_parser("config", help="configure and edit TOML settings")
    config.add_argument("params", nargs="*", metavar="ACTION [KEY] [VALUE]")
    config.add_argument("--file", "-f", default=default_config)
    config.set_defaults(func=config_command)
    gateway = sub.add_parser("gateway", help="manage the GhGoyifier gateway service")
    gateway.add_argument("action", choices=["install", "start", "restart", "enable", "stop", "disable", "status"])
    gateway.set_defaults(func=lambda a: _gateway(a))
    logs = sub.add_parser("logs", help="inspect gateway logs")
    logs.add_argument("action", nargs="?", choices=["show", "follow", "clear"], default="show")
    logs.add_argument("--lines", type=int, default=100)
    logs.add_argument("--file", default=str(logfile))
    logs.set_defaults(func=logs_command)
    doctor = sub.add_parser("doctor", help="show runtime and init diagnostics")
    doctor.set_defaults(func=lambda a: _doctor())
    status = sub.add_parser("status", help="show gateway status")
    status.set_defaults(func=lambda a: _gateway(argparse.Namespace(action="status")))
    return parser


def _gateway(args: argparse.Namespace) -> int:
    code, message = run(args.action)
    console.print(Panel(message or "ok", title=f"gateway {args.action} / {detect_init()}", border_style="green" if code == 0 else "red"))
    return code


def _doctor() -> int:
    table = Table(title="GhGoyifier doctor")
    table.add_column("Component")
    table.add_column("Value")
    table.add_row("Python", sys.executable)
    table.add_row("Config", default_config)
    table.add_row("Init", detect_init())
    table.add_row("Log", str(logfile))
    table.add_row("Package", "GhGoyifier")
    console.print(table)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
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
