# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import coloredlogs
from goygram import GoyGram

from GhGoyifier import db
from GhGoyifier.arguments import parse_arguments
from GhGoyifier.commands import remove_bot_commands, setup_bot_commands
from GhGoyifier.config import parse_config
from GhGoyifier.db import close_orm, init_orm
from GhGoyifier.db.functions import migrate_secrets
from GhGoyifier.goygram_bot import GoyBot
from GhGoyifier.handlers import register_handlers
from GhGoyifier.runtime import set_bot_username
from GhGoyifier.secret_store import initialize as initialize_secret_store
from GhGoyifier.security_storage import harden_config_file, harden_runtime

_proxy_names = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy")


def _read_proxy_environment() -> dict[str, str]:
    values = {name: os.environ[name] for name in _proxy_names if os.environ.get(name)}
    files = [Path("/etc/environment"), Path.home() / ".config" / "environment.d" / "90-goyifier-proxy.conf"]
    for directory in (Path.home() / ".config" / "environment.d",):
        if directory.is_dir():
            files.extend(sorted(directory.glob("*.conf")))
    assignment = re.compile(r"^\s*(?:export\s+)?(" + "|".join(_proxy_names) + r")\s*=\s*(.*?)\s*$")
    for path in files:
        try:
            for line in path.read_text(errors="replace").splitlines():
                match = assignment.match(line)
                if match:
                    value = match.group(2)
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                        value = value[1:-1]
                    values[match.group(1)] = value
        except OSError:
            continue
    try:
        result = subprocess.run(["systemctl", "--user", "show-environment"], text=True, capture_output=True, timeout=2, check=False)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                match = assignment.match(line)
                if match:
                    values[match.group(1)] = match.group(2)
    except (OSError, subprocess.SubprocessError):
        pass
    return values


async def _proxy_monitor(app) -> None:
    previous: dict[str, str] | None = None
    while True:
        try:
            values = _read_proxy_environment()
            if values != previous:
                for name in _proxy_names:
                    if values.get(name):
                        os.environ[name] = values[name]
                    else:
                        os.environ.pop(name, None)
                if previous is not None and app.bot is not None and app.bot.sess is not None and not app.bot.sess.closed:
                    await app.bot.sess.close()
                    app.bot.sess = None
                    logging.info("Proxy configuration changed; reconnecting Telegram transport")
                previous = values
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.getLogger("goyifi").exception("Proxy monitor failed")
        await asyncio.sleep(5)


async def main():
    coloredlogs.install(level=logging.INFO)
    logging.info("Starting bot...")
    arguments = parse_arguments()
    harden_config_file(arguments.config)
    config = parse_config(arguments.config)
    harden_runtime(arguments.config, config)
    initialize_secret_store()
    tortoise_config = config.database.get_tortoise_config()
    try:
        await db.create_models(tortoise_config)
    except FileExistsError:
        await db.migrate_models(tortoise_config)
    await init_orm(tortoise_config)
    await migrate_secrets()
    app = GoyGram(
        bot_token=config.bot.token, bot_timeout=25, bot_base=config.api.bot_api_url
    )
    proxy_task = asyncio.create_task(_proxy_monitor(app))
    bot = GoyBot(app, buttons_mode=config.settings.buttons)
    register_handlers(app, config, bot)
    from GhGoyifier.notifications import poll_loop

    try:
        await setup_bot_commands(bot, config)
    except asyncio.TimeoutError:
        logging.warning("Telegram command registration timed out; continuing with bot startup")
    try:
        identity = await app.bot_req("getMe")
    except asyncio.TimeoutError:
        identity = {}
        logging.warning("Telegram identity request timed out; continuing with bot startup")
    set_bot_username(identity.get("username"))
    logging.info("Bot started: @%s (%s)", identity.get("username", "unknown"), identity.get("id", "unknown"))
    polling_task = asyncio.create_task(poll_loop(bot, config))
    try:
        await app.run()
    finally:
        proxy_task.cancel()
        await asyncio.gather(proxy_task, return_exceptions=True)
        polling_task.cancel()
        await asyncio.gather(polling_task, return_exceptions=True)
        await remove_bot_commands(bot, config)
        await close_orm()


if __name__ == "__main__":
    try:
        if not sys.argv[1:] or sys.argv[1] in {"config", "gateway", "logs", "doctor", "status", "update", "uninstall", "--help", "-h", "-v", "--version"}:
            from GhGoyifier.cli import main as cli_main
            raise SystemExit(cli_main())
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped!")
    except EOFError:
        logging.error("Interactive configuration requires terminal input.")
        raise SystemExit(1)
