# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace
from typing import Any

import aiohttp
from goygram import GoyGram
from goygram.types.kbd import KbdBuilder

from GhGoyifier.anti_abuse import OutboundGuard, SilentDrop
from GhGoyifier.callback_vault import protect
from GhGoyifier.emoji import (
    button_icon,
    extract_github_buttons,
    rich_button_rows,
    rich_html,
)


class GoyBot:
    def __init__(self, app: GoyGram, buttons_mode: str = "in-msg"):
        self.app = app
        if buttons_mode not in {"inline", "in-msg"}:
            raise ValueError("buttons_mode must be 'inline' or 'in-msg'")
        self.buttons_mode = buttons_mode
        self.outbound_guard = OutboundGuard()
        self.proxy_manager: Any = None

    async def request(self, method: str, **data: Any) -> Any:
        if not self.outbound_guard.allow(method, data.get("chat_id")):
            raise SilentDrop
        try:
            return await self.app.bot_req(method, **data)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            if self.proxy_manager is not None:
                await self.proxy_manager.failover()
            raise
        except RuntimeError as exc:
            match = re.search(r"retry after (\d+)", str(exc), re.IGNORECASE)
            if "http 429" in str(exc) and match:
                self.outbound_guard.trip(int(match.group(1)))
            raise

    async def send_message(
        self, chat_id: int | str, text: str, reply_markup: Any = None, **kwargs: Any
    ):
        if hasattr(reply_markup, "to_dict"):
            reply_markup = reply_markup.to_dict()
        text, reply_markup = extract_github_buttons(text, reply_markup)
        if kwargs.pop("disable_web_page_preview", False):
            kwargs.setdefault("link_preview_options", {"is_disabled": True})
        rich_message = kwargs.pop("rich_message", None)
        if self.buttons_mode == "inline":
            rich_message = rich_message or {"html": rich_html(text)}
            return GoyMessage(
                self,
                await self.request(
                    "sendRichMessage",
                    chat_id=chat_id,
                    rich_message=rich_message,
                    reply_markup=reply_markup,
                    **kwargs,
                )
                or {"chat": {"id": chat_id}, "text": text},
            )
        if rich_message is None:
            rendered_html = rich_html(text) + rich_button_rows(reply_markup)
            rich_message = {"html": rendered_html}
        result = await self.request(
            "sendRichMessage",
            chat_id=chat_id,
            rich_message=rich_message,
            **kwargs,
        )
        return GoyMessage(self, result or {"chat": {"id": chat_id}, "text": text})

    async def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: Any = None,
        **kwargs: Any,
    ):
        if hasattr(reply_markup, "to_dict"):
            reply_markup = reply_markup.to_dict()
        text, reply_markup = extract_github_buttons(text, reply_markup)
        rich_message = kwargs.pop("rich_message", None)
        if self.buttons_mode == "inline":
            try:
                return await self.request(
                    "editMessageText",
                    chat_id=chat_id,
                    message_id=message_id,
                    rich_message=rich_message or {"html": rich_html(text)},
                    reply_markup=reply_markup,
                    **kwargs,
                )
            except Exception as exc:
                if "message is not modified" in str(exc).lower():
                    return True
                raise
        rich_message = rich_message or {
            "html": rich_html(text) + rich_button_rows(reply_markup)
        }
        try:
            return await self.request(
                "editMessageText",
                chat_id=chat_id,
                message_id=message_id,
                rich_message=rich_message,
                **kwargs,
            )
        except Exception as exc:
            if "message is not modified" in str(exc).lower():
                return True
            raise

    async def edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: Any = None,
        **kwargs: Any,
    ):
        if hasattr(reply_markup, "to_dict"):
            reply_markup = reply_markup.to_dict()
        return await self.request(
            "editMessageReplyMarkup",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            **kwargs,
        )

    async def delete_message(self, chat_id: int | str, message_id: int):
        return await self.request(
            "deleteMessage", chat_id=chat_id, message_id=message_id
        )

    async def get_chat_administrators(self, chat_id: int):
        rows = await self.request("getChatAdministrators", chat_id=chat_id)
        return [
            SimpleNamespace(
                user=SimpleNamespace(**row.get("user", {})), status=row.get("status")
            )
            for row in rows or []
        ]

    async def get_chat(self, chat_id: int | str):
        row = await self.request("getChat", chat_id=chat_id)
        return SimpleNamespace(**(row or {}))

    async def set_my_commands(self, commands: list[dict[str, str]]):
        return await self.request("setMyCommands", commands=commands)

    async def delete_my_commands(self, **kwargs: Any):
        return await self.request("deleteMyCommands", **kwargs)


class GoyMessage:
    def __init__(self, bot: GoyBot, raw: dict[str, Any], is_callback: bool = False):
        self.bot = bot
        self.raw = raw
        self.is_callback = is_callback
        self.message_id = raw.get("message_id")
        self.chat = SimpleNamespace(**(raw.get("chat") or {}))
        self.chat_id = self.chat.id if hasattr(self.chat, "id") else raw.get("chat_id")
        self.text = raw.get("text") or raw.get("caption") or ""
        self.from_user = (
            SimpleNamespace(**(raw.get("from") or {})) if raw.get("from") else None
        )
        self.message_thread_id = raw.get("message_thread_id")

    async def answer(self, text: str, reply_markup: Any = None, **kwargs: Any):
        if self.is_callback and self.message_id:
            return await self.edit_text(text, reply_markup=reply_markup, **kwargs)
        if self.message_thread_id and "message_thread_id" not in kwargs:
            kwargs["message_thread_id"] = self.message_thread_id
        return await self.bot.send_message(
            self.chat_id, text, reply_markup=reply_markup, **kwargs
        )

    async def edit_text(self, text: str, reply_markup: Any = None, **kwargs: Any):
        result = await self.bot.edit_message_text(
            self.chat_id, self.message_id, text, reply_markup, **kwargs
        )
        if isinstance(result, dict):
            self.raw.update(result)
        self.text = text
        return self

    async def edit_reply_markup(self, reply_markup: Any = None, **kwargs: Any):
        return await self.bot.edit_message_reply_markup(
            self.chat_id, self.message_id, reply_markup, **kwargs
        )

    async def delete(self):
        return await self.bot.delete_message(self.chat_id, self.message_id)


def inline_keyboard(rows: list[list[tuple[str, str, str]]]) -> dict[str, Any]:
    builder = KbdBuilder(kind="inline")
    for row in rows:
        for text, kind, value in row:
            label, emoji_id = button_icon(text)
            if kind == "callback_data":
                value = protect(str(value))
            options = {kind: value}
            if emoji_id is not None:
                options["icon_custom_emoji_id"] = emoji_id
            builder.btn(label, **options)
        builder.row()
    return builder.to_dict()


def message_from_packet(bot: GoyBot, packet: Any) -> GoyMessage:
    normalized = packet.raw if isinstance(packet.raw, dict) else {}
    candidate = normalized.get("raw")
    original = candidate if isinstance(candidate, dict) else normalized
    raw = original.get("message") or original.get("edited_message")
    if not isinstance(raw, dict):
        raw = normalized
    return GoyMessage(bot, raw)
