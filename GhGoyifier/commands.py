# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from GhGoyifier.config import Config
from GhGoyifier.goygram_bot import GoyBot

users_commands = {
    "start": "Start bot / show setup guide",
    "help": "Show setup guide and command reference",
    "integrate": "Integrate a repository (in group)",
    "integrations": "List integrated repositories",
    "delete": "Remove an integration",
    "reinstall": "Refresh polling notifications for this chat",
    "install": "Install the GitHub App for your account (DM)",
    "token": "Set or replace your GitHub token (DM)",
    "set_topic": "Send notifications to current forum topic",
    "events": "Toggle event types per chat",
}


async def setup_bot_commands(bot: GoyBot, config: Config):
    await bot.set_my_commands(
        [
            {"command": command, "description": description}
            for command, description in users_commands.items()
        ]
    )


async def remove_bot_commands(bot: GoyBot, config: Config):
    await bot.delete_my_commands()
