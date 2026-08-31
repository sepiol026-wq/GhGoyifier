# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
import html
import logging
import time

import aiohttp
from fastapi import APIRouter, Header, HTTPException, Request

from GhGoyifier.config import parse_config
from GhGoyifier.db.functions import Chat, EventSetting, Integration
from GhGoyifier.emoji import extract_github_buttons, rich_button_rows, rich_html
from GhGoyifier.events import EventCtx, build_message
from GhGoyifier.utils.github_app import verify_pat_webhook_signature
from GhGoyifier.utils.text_splitter import split_html_message

router = APIRouter()
try:
    config = parse_config()
except FileNotFoundError:
    config = None


def get_config():
    global config
    if config is None:
        config = parse_config()
    return config


floodwait_cache: dict[int, float] = {}




_delivery_failure_notified: dict[tuple[int, int], float] = {}
_notify_interval = 1800.0
_webhook_max_bytes = 2 * 1024 * 1024
_webhook_window = 60.0
_webhook_limit = 120
_webhook_hits: dict[str, list[float]] = {}


def check_floodwait(chat_id: int, floodwait: int = 3) -> bool:
    now = time.time()
    if (last := floodwait_cache.get(chat_id)) and now - last < floodwait:
        return True
    floodwait_cache[chat_id] = now
    return False


def _allow_webhook(source: str) -> bool:
    now = time.time()
    hits = [stamp for stamp in _webhook_hits.get(source, []) if now - stamp < _webhook_window]
    if len(hits) >= _webhook_limit:
        _webhook_hits[source] = hits
        return False
    hits.append(now)
    _webhook_hits[source] = hits
    if len(_webhook_hits) > 10000:
        _webhook_hits.clear()
    return True


async def _post_send(session: aiohttp.ClientSession, data: dict) -> tuple[int, str]:
    payload = dict(data)
    markup = payload.pop("reply_markup", None)
    if markup and payload.get("rich_message"):
        rich_message = dict(payload["rich_message"])
        rich_message["html"] = rich_message.get("html", "") + rich_button_rows(markup)
        payload["rich_message"] = rich_message
    async with session.post(
        f"https://api.telegram.org/bot{config.bot.token}/sendRichMessage",
        json=payload,
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        return response.status, await response.text()


async def _notify_owner_of_delivery_failure(
    session: aiohttp.ClientSession,
    integration: Integration,
    failure_summary: str,
) -> None:
    """DM the user who set up this integration about a persistent delivery
    failure. Rate-limited per (user, chat) to avoid spamming on every event
    while the chat is unreachable."""
    user = integration.user
    chat = integration.chat
    if user is None or chat is None or not user.telegram_id:
        return

    key = (user.telegram_id, chat.chat_id)
    now = time.time()
    last = _delivery_failure_notified.get(key)
    if last is not None and now - last < _notify_interval:
        logging.info(
            "Suppressed delivery-failure DM to %s about chat %s "
            "(last notified %.0fs ago, interval %.0fs)",
            user.telegram_id,
            chat.chat_id,
            now - last,
            _notify_interval,
        )
        return
    _delivery_failure_notified[key] = now

    text = (
        "⚠️ <b>I couldn't deliver a notification</b>\n\n"
        f"Repository: <code>{html.escape(integration.repository_name or '?')}</code>\n"
        f"Target chat id: <code>{chat.chat_id}</code>\n"
        f"Error: <code>{html.escape(failure_summary[:300])}</code>\n\n"
        "Possible causes:\n"
        "• I was removed from the chat\n"
        "• The chat was deleted or migrated to a different id\n"
        "• I lost permissions to write there\n"
        "• The forum topic the integration uses was closed\n\n"
        "Run <code>/integrations</code> in that chat to manage, or "
        "<code>/remove owner/repo</code> there to remove the integration "
        "if the chat is gone."
    )
    clean_text, markup = extract_github_buttons(text)
    data = {
        "chat_id": user.telegram_id,
        "rich_message": {"html": rich_html(clean_text)},
        "link_preview_options": {"is_disabled": True},
    }
    if markup is not None:
        data["reply_markup"] = markup
    try:
        status, body = await _post_send(session, data)
        if status < 400:
            logging.info(
                "Sent delivery-failure DM to %s about chat %s",
                user.telegram_id,
                chat.chat_id,
            )
        else:
            logging.warning(
                "Couldn't DM owner %s about delivery failure: %s — %s",
                user.telegram_id,
                status,
                body,
            )
    except aiohttp.ClientError as e:
        logging.warning(
            "Network error DM-ing owner %s about delivery failure: %s",
            user.telegram_id,
            e,
        )


async def send_message(
    session: aiohttp.ClientSession,
    integration: Integration,
    text: str,
) -> None:
    """Send a (possibly long) Telegram-HTML message to the integration's
    chat. Splits the text into 32768-safe chunks at safe HTML boundaries and
    sends them sequentially, so one event with many commits / a huge body
    arrives as a series of messages instead of falling on the floor."""
    chunks = split_html_message(text)
    for chunk in chunks:
        await _send_one_chunk(session, integration, chunk)


async def _send_one_chunk(
    session: aiohttp.ClientSession,
    integration: Integration,
    text: str,
) -> None:
    """Send a single chunk that's already known to fit Telegram's limit.
    Handles topic-thread retry, owner-notify on persistent failure, and
    auto-cleanup of dead topics."""
    chat = integration.chat
    if chat is None:
        return
    chat_id = chat.chat_id
    topic_id = chat.topic_id

    clean_text, markup = extract_github_buttons(text)
    data: dict = {
        "chat_id": chat_id,
        "rich_message": {"html": rich_html(clean_text)},
        "link_preview_options": {"is_disabled": True},
    }
    if markup is not None:
        data["reply_markup"] = markup
    if topic_id:
        data["message_thread_id"] = topic_id

    try:
        status, body = await _post_send(session, data)
        if status < 400:
            return





        if (
            topic_id
            and status == 400
            and ("thread not found" in body.lower() or "topic_closed" in body.lower())
        ):
            thread_gone = "thread not found" in body.lower()
            logging.warning(
                "Topic %s in chat %s is unavailable, retrying without thread.",
                topic_id,
                chat_id,
            )
            data.pop("message_thread_id", None)
            status, body = await _post_send(session, data)
            if status < 400:



                if thread_gone:
                    try:
                        await Chat.remove_topic(chat_id)
                        logging.info(
                            "Cleared dead topic %s from chat %s",
                            topic_id,
                            chat_id,
                        )
                    except Exception:
                        logging.exception(
                            "Couldn't clear topic_id for chat %s", chat_id
                        )
                return




        if status == 403:
            logging.warning(
                "Bot can't write to chat %s (kicked / no permission): %s",
                chat_id,
                body,
            )
            await _notify_owner_of_delivery_failure(session, integration, body)
        elif 400 <= status < 500:
            logging.warning(
                "Telegram sendMessage to %s returned %s: %s",
                chat_id,
                status,
                body,
            )
            await _notify_owner_of_delivery_failure(session, integration, body)
        else:

            logging.warning(
                "Telegram sendMessage to %s returned %s (transient): %s",
                chat_id,
                status,
                body,
            )
    except aiohttp.ClientError as e:
        logging.error("Error sending to chat %s: %s", chat_id, e)


@router.post("/{token}")
async def webhook(
    req: Request,
    token: str,
    X_GitHub_Event: str = Header(),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
):
    config = get_config()
    content_length = req.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(400, "Invalid Content-Length") from exc
        if declared_length < 0 or declared_length > _webhook_max_bytes:
            raise HTTPException(413, "Webhook payload is too large")
    source = req.client.host if req.client else "unknown"
    if not _allow_webhook(source):
        raise HTTPException(429, "Webhook rate limit exceeded")
    body = await req.body()
    if len(body) > _webhook_max_bytes:
        raise HTTPException(413, "Webhook payload is too large")
    integrations = await Integration.get_by_token(token)
    if integrations and not verify_pat_webhook_signature(token, body, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")
    payload = await req.json()

    if not integrations:
        logging.info(
            "PAT webhook %s: no matching integrations",
            X_GitHub_Event,
        )
        return {"status": "ok", "matched": 0, "sent": 0}

    sent = 0
    skipped_event = 0
    skipped_floodwait = 0
    skipped_no_message = 0
    async with aiohttp.ClientSession() as session:
        for integration in integrations:
            chat = integration.chat
            user = integration.user

            if not await EventSetting.is_enabled(chat.chat_id, X_GitHub_Event):
                skipped_event += 1
                continue

            if X_GitHub_Event == "star" and check_floodwait(
                chat.chat_id, chat.floodwait
            ):
                skipped_floodwait += 1
                continue

            ctx = EventCtx(auth_token=user.token, config=config)
            message = build_message(X_GitHub_Event, payload, ctx)
            if not message:
                skipped_no_message += 1
                continue
            await send_message(session, integration, message)
            sent += 1

    logging.info(
        "PAT webhook %s: %d integrations, sent=%d, "
        "skipped(event=%d floodwait=%d no_msg=%d)",
        X_GitHub_Event,
        len(integrations),
        sent,
        skipped_event,
        skipped_floodwait,
        skipped_no_message,
    )
    return {
        "status": "ok",
        "matched": len(integrations),
        "sent": sent,
        "skipped": {
            "event_disabled": skipped_event,
            "floodwait": skipped_floodwait,
            "no_message": skipped_no_message,
        },
    }
