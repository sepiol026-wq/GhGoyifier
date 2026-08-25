# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""Helpers for resolving Telegram chat titles and listing chats where a
particular user is an administrator. Used by DM dialogs (My chats, Repos
integrate flow). Results are cached in-process to avoid hammering Telegram
on every dialog interaction.
"""

import asyncio
import time
from typing import TypedDict

from GhGoyifier.db.functions import Chat
from GhGoyifier.goygram_bot import GoyBot


class AdminChat(TypedDict):
    chat_id: int
    title: str



_title_ttl = 300.0
_title_cache: dict[int, tuple[str, float]] = {}


_admin_ttl = 60.0
_admin_cache: dict[int, tuple[list[AdminChat], float]] = {}


async def resolve_chat_title(bot: GoyBot, chat_id: int) -> str:
    cached = _title_cache.get(chat_id)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]
    try:
        tg_chat = await bot.get_chat(chat_id)
        title = (
            tg_chat.title or getattr(tg_chat, "full_name", None) or f"chat {chat_id}"
        )
    except Exception:
        title = f"(unavailable, id={chat_id})"
    _title_cache[chat_id] = (title, now + _title_ttl)
    return title


def invalidate_titles() -> None:
    _title_cache.clear()


async def list_admin_chats(bot: GoyBot, telegram_user_id: int) -> list[AdminChat]:
    """Return chats from our DB where the user is currently an admin.

    One ``getChatAdministrators`` API call per known chat, fanned out in
    parallel. Failures (bot kicked / chat deleted / network) are silently
    skipped. Cached per user for ``_admin_ttl`` seconds.
    """
    cached = _admin_cache.get(telegram_user_id)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]

    chats = await Chat.all()

    async def _check(chat: Chat) -> AdminChat | None:
        try:
            admins = await bot.get_chat_administrators(chat.chat_id)
        except Exception:
            return None
        if telegram_user_id not in [a.user.id for a in admins]:
            return None
        title = await resolve_chat_title(bot, chat.chat_id)
        return AdminChat(chat_id=chat.chat_id, title=title)

    raw = await asyncio.gather(*[_check(c) for c in chats])
    result = [x for x in raw if x is not None]
    result.sort(key=lambda c: c["title"].lower())
    _admin_cache[telegram_user_id] = (result, now + _admin_ttl)
    return result


def invalidate_admin_chats(telegram_user_id: int | None = None) -> None:
    if telegram_user_id is None:
        _admin_cache.clear()
    else:
        _admin_cache.pop(telegram_user_id, None)
