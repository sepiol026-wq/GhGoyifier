# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.

from GhGoyifier.goygram_bot import GoyBot


async def get_admin_ids(bot: GoyBot, chat_id: int) -> list[int] | None:
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except Exception:
        return None
    return [a.user.id for a in admins]


async def is_user_admin(bot: GoyBot, chat_id: int, user_id: int) -> bool:
    admin_ids = await get_admin_ids(bot, chat_id)
    return admin_ids is not None and user_id in admin_ids
