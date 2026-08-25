# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
import contextlib
import logging

from aerich import Command
from click import Abort
from tortoise import Tortoise


async def create_models(tortoise_config: dict):
    command = Command(tortoise_config=tortoise_config, app="models")
    await command.init()
    await command.init_db(safe=True)
    await command.upgrade(run_in_transaction=True)


async def migrate_models(tortoise_config: dict):
    command = Command(tortoise_config=tortoise_config, app="models")
    await command.init()
    with contextlib.suppress(Abort):
        await command.migrate()
    await command.upgrade(run_in_transaction=True)


async def init_orm(tortoise_config: dict) -> None:
    await Tortoise.init(config=tortoise_config)
    connection = Tortoise.get_connection("default")
    await connection.execute_script(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_eventsetting_chat_event "
        "ON eventsetting(chat_id, event_type)"
    )
    logging.info(f"Tortoise-ORM started, {Tortoise.apps}")


async def close_orm() -> None:
    await Tortoise.close_connections()
    logging.info("Tortoise-ORM shutdown")
