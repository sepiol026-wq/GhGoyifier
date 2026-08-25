# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from __future__ import annotations

import asyncio
import logging
import sys

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
    bot = GoyBot(app, buttons_mode=config.settings.buttons)
    register_handlers(app, config, bot)
    from GhGoyifier.notifications import poll_loop

    await setup_bot_commands(bot, config)
    identity = await app.bot_req("getMe")
    set_bot_username(identity.get("username"))
    logging.info("Bot started: @%s (%s)", identity.get("username"), identity.get("id"))
    polling_task = asyncio.create_task(poll_loop(bot, config))
    try:
        await app.run()
    finally:
        polling_task.cancel()
        await asyncio.gather(polling_task, return_exceptions=True)
        await remove_bot_commands(bot, config)
        await close_orm()


if __name__ == "__main__":
    try:
        if sys.argv[1:] and sys.argv[1] in {"config", "gateway", "logs", "doctor", "status", "update", "--help", "-h", "--version"}:
            from GhGoyifier.cli import main as cli_main
            raise SystemExit(cli_main())
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped!")
