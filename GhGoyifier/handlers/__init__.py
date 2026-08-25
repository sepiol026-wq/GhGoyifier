# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from __future__ import annotations

import asyncio
import html
import logging
from types import SimpleNamespace
from typing import Any

from GhGoyifier.anti_abuse import InboundAdmission, SilentDrop
from GhGoyifier.callback_vault import resolve
from GhGoyifier.config import Config
from GhGoyifier.db.functions import Chat, EventSetting, Installation, Integration, User
from GhGoyifier.goygram_bot import (
    GoyBot,
    GoyMessage,
    inline_keyboard,
    message_from_packet,
)
from GhGoyifier.keyboards.integration import (
    build_integrations_keyboard,
    build_management_keyboard,
    integrations_header,
)
from GhGoyifier.keyboards.main_menu import (
    btn_add_to_chat,
    btn_connect,
    btn_help,
    btn_my_chats,
    btn_repos,
    help_keyboard,
    main_menu_keyboard,
)
from GhGoyifier.runtime import get_bot_username
from GhGoyifier.services.integration import integrate_repo
from GhGoyifier.utils.chat_access import (
    invalidate_titles,
    list_admin_chats,
    resolve_chat_title,
)
from GhGoyifier.utils.github_access import (
    invalidate_for_user,
    list_orgs_for_user,
    list_repos_for_org,
)
from GhGoyifier.utils.github_app import install_url
from GhGoyifier.utils.group_admin import get_admin_ids, is_user_admin
from GhGoyifier.utils.hooks import (
    HookError,
    check_repo,
    get_subscribed_events_for,
    update_webhook,
    validate,
)

welcome = (
    "<h2>👋 <b>Hi! I'm a Goyifier bot.</b></h2>\n"
    "<p>I deliver GitHub notifications to Telegram using the Notifications API and efficient polling.</p>\n"
    "<hr>\n"
    "<p>📌 <b>First step:</b> tap <b>🔌 Connect</b> below to authorize me with GitHub. Then use <b>➕ Add to chat</b> to invite me to a group, and <b>🏢 Repos</b> to pick what to integrate.</p>\n"
    "<details><summary>How the setup works</summary>\n"
    "<p>Authorize GitHub, choose a repository, select a chat, then configure the event types you want to receive.</p>\n"
    "</details>\n"
)
help = (
    "<h2>❓ <b>Goyifier help</b></h2>\n"
    "<p>Use the buttons below for private-chat setup.</p>\n"
    "<hr>\n"
    "<details><summary>DM controls</summary>\n"
    "<p>🔌 <b>Connect</b> — manage GitHub authorization (App or PAT)<br>"
    "➕ <b>Add to chat</b> — invite me to a group<br>"
    "🏢 <b>Repos</b> — browse and integrate repositories<br>"
    "💬 <b>My chats</b> — manage existing integrations</p>\n"
    "</details>\n"
    "<details><summary>Group commands</summary>\n"
    "<p><code>/integrate owner/repo</code><br><code>/integrations</code><br>"
    "<code>/events</code><br><code>/set_topic</code><br><code>/reinstall</code><br>"
    "<code>/delete owner/repo</code></p>\n"
    "</details>\n"
)
pat_guide = (
    "<details><summary>Required GitHub permissions</summary>\n"
    "<p><b>Classic PAT:</b> open GitHub token settings and enable <code>repo</code> for private repositories (public repositories can use <code>public_repo</code>).</p>\n"
    "<p><b>Fine-grained PAT:</b> open GitHub token settings, select the repository, then grant <code>Contents: Read-only</code> and <code>Metadata: Read-only</code>.</p>\n"
    "<p>After changing permissions, send the new token again with <code>/token</code>. Send it only in private chat.</p>\n"
    "</details>"
)
event_labels = {
    "ping": "Ping",
    "push": "Push",
    "issues": "Issues",
    "issue_comment": "Issue comments",
    "pull_request": "Pull requests",
    "pull_request_review": "PR reviews",
    "pull_request_review_comment": "PR review comments",
    "commit_comment": "Commit comments",
    "star": "Stars",
    "fork": "Forks",
    "create": "Branch/tag created",
    "delete": "Branch/tag deleted",
    "release": "Releases",
    "workflow_run": "CI runs",
    "discussion": "Discussions",
    "discussion_comment": "Discussion comments",
    "deployment_status": "Deployments",
    "member": "Members",
    "public": "Repo made public",
}


def _is_dm(msg: GoyMessage) -> bool:
    return bool(msg.from_user and msg.chat_id == msg.from_user.id)


def _nav_button(msg: GoyMessage, route: str, label: str = "« Back") -> tuple[str, str, str]:
    return (label if msg.is_callback else "✕ Close", "callback_data", route if msg.is_callback else "nav:close")


def _state_key(msg: GoyMessage) -> tuple[int, int]:
    return int(msg.chat_id), int(msg.from_user.id)


def _command(text: str, name: str) -> bool:
    return bool(text) and text.split(maxsplit=1)[0].split("@", 1)[0] == f"/{name}"


def _args(text: str) -> str:
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


async def _present(msg: GoyMessage, app, state: str, text: str, markup: dict | None = None, data: dict | None = None):
    current = app.get_state_data(msg.chat_id, msg.from_user.id) or {}
    screen_id = msg.message_id if msg.is_callback else current.get("screen_message_id")
    if msg.is_callback and screen_id:
        try:
            await msg.bot.edit_message_text(msg.chat_id, int(screen_id), text, markup)
            app.set_state(msg.chat_id, msg.from_user.id, state, {**current, "screen_message_id": screen_id, "screen_text": text, "screen_markup": markup, **(data or {})})
            return
        except Exception:
            pass
    sent = await msg.answer(text, reply_markup=markup)
    sent_id = getattr(sent, "message_id", None)
    app.set_state(msg.chat_id, msg.from_user.id, state, {**current, "screen_message_id": sent_id, "screen_text": text, "screen_markup": markup, **(data or {})})


async def _deferred(coro, msg: GoyMessage | None = None, app=None, state: str | None = None) -> None:
    try:
        await coro
    except Exception:
        logging.getLogger("goyifi").exception("Deferred screen render failed")
        if msg is not None and app is not None and state is not None:
            try:
                await _present(msg, app, state, "❌ Couldn't load this screen. Please try again.")
            except Exception:
                logging.getLogger("goyifi").exception("Deferred error recovery failed")


async def _loading(msg: GoyMessage, app, state: str) -> None:
    await _present(msg, app, state, "<i>Loading…</i>")


async def _available_events(chat_id: int, host: str) -> set[str] | None:
    integrations = await Chat.get_integrations(chat_id)
    if not integrations:
        return None
    result = []
    for integration in integrations:
        user = await User.get_or_none(id=integration.user_id)
        if user is None or not user.token:
            return None
        result.append(
            await asyncio.to_thread(
                get_subscribed_events_for,
                user.token,
                integration.repository_name,
                host,
                integration.integration_token,
            )
        )
    if not result or any(not isinstance(item, set) for item in result):
        return None
    return set.intersection(*result)


async def _event_keyboard(chat_id: int, config: Config, msg: GoyMessage | None = None) -> tuple[str, dict]:
    available = None if config.notifications.mode == "polling" else await _available_events(chat_id, config.api.host)
    settings = await EventSetting.for_chat(chat_id)
    rows = [
        [
            (
                f"{'✅' if item.enabled else '❌'}{'⚠️' if available is not None and item.event_type != 'ping' and item.event_type not in available else ''} {event_labels.get(item.event_type, item.event_type)}",
                "callback_data",
                f"toggle_event:{item.event_type}",
            )
            for item in settings[i : i + 2]
        ]
        for i in range(0, len(settings), 2)
    ]
    stale = (
        available is not None
        and ({item.event_type for item in settings} - {"ping"}) - available
    )
    text = "✨ Github events settings"
    if stale:
        text += "\n\n⚠️ Some events are not subscribed on GitHub. Run /reinstall."
    rows.append([_nav_button(msg, "integ:list") if msg else ("« Back", "callback_data", "integ:list")])
    return text, inline_keyboard(rows)


async def _show_token(msg: GoyMessage, app, config: Config):
    user = await User.get_or_none(telegram_id=msg.from_user.id)
    installations = await Installation.for_user(user.id) if user else []
    token = user.token if user else None
    pat = "✅ Saved" if token else "❌ No token saved"
    app_line = (
        "✅ Installed for "
        + ", ".join(f"<code>{i.account_login}</code>" for i in installations)
        if installations
        else "❌ Not installed"
    )
    rows = []
    if config.github_app.is_configured:
        rows.append(
            [("🔗 Install GitHub App", "url", install_url(config, msg.from_user.id))]
        )
    rows.append(
        [("🔗 GitHub PAT settings", "url", "https://github.com/settings/tokens")]
    )
    rows.append(
        [
            ("🔄 Update PAT", "callback_data", "token:update"),
            ("🧪 Test PAT", "callback_data", "token:test"),
        ]
    )
    if token:
        rows.append([("🗑 Remove PAT", "callback_data", "token:remove")])
    rows.append([_nav_button(msg, "menu:home")])
    await _present(
        msg,
        app,
        "token_main",
        f"🔑 <b>GitHub Connection</b>\nApp: {app_line}\n\nPAT status: {pat}\n\n{pat_guide}\n\nSend a new PAT after tapping Update. The secret message is deleted.",
        inline_keyboard(rows),
    )


async def _show_orgs(msg: GoyMessage, app, config: Config):
    user = await User.get_or_none(telegram_id=msg.from_user.id)
    if user is None:
        return await _present(msg, app, "repos_orgs", "❌ You haven't authorized me with GitHub yet. Tap <b>🔌 Connect</b>.", inline_keyboard([[_nav_button(msg, 'menu:home')]]))
    try:
        orgs = await list_orgs_for_user(user, config)
    except Exception as exc:
        return await _present(msg, app, "repos_orgs", f"❌ Couldn't fetch organisations: {html.escape(str(exc)[:200])}", inline_keyboard([[_nav_button(msg, 'menu:home')]]))
    if not orgs:
        return await _present(msg, app, "repos_orgs", "❌ No GitHub accounts are available.", inline_keyboard([[_nav_button(msg, 'menu:home')]]))
    app.set_state(*_state_key(msg), "repos_orgs")
    rows = [
        [
            (
                f"{'👤' if o['is_personal'] else '🏢'} {o['login']} [{'A' if o['source'] == 'app' else 'P'}]",
                "callback_data",
                f"repos:org:{o['login']}:{int(o['is_personal'])}:{o['source']}:{o['installation_id']}",
            )
        ]
        for o in orgs
    ]
    rows.append(
        [
            ("🔄 Refresh", "callback_data", "repos:refresh"),
            _nav_button(msg, "menu:home"),
        ]
    )
    await _present(msg, app, "repos_orgs", "🏢 <b>Choose where to look</b>\n<i>[A] GitHub App • [P] Personal Access Token</i>", inline_keyboard(rows))


async def _show_repos(msg: GoyMessage, app, config: Config, data: dict):
    user = await User.get_or_none(telegram_id=msg.from_user.id)
    org = {
        "login": data["org"],
        "is_personal": data["personal"],
        "source": data["source"],
        "installation_id": data["installation"],
    }
    try:
        repos = await list_repos_for_org(user, org, config)
    except Exception as exc:
        return await _present(msg, app, "repos_list", f"❌ {html.escape(str(exc)[:200])}", inline_keyboard([[_nav_button(msg, 'repos:back_orgs')]]), data=data)
    integrated = {
        r.repository_name for r in await Integration.filter(user_id=user.id).all()
    }
    rows = [
        [
            (
                f"{'✅ ' if r['full_name'] in integrated else ''}{'🔒' if r['private'] else '🔓'} {r['name']}",
                "callback_data",
                f"repos:repo:{r['full_name']}",
            )
        ]
        for r in repos
    ]
    rows.append(
        [
            ("« Orgs", "callback_data", "repos:back_orgs"),
            ("🔄 Refresh", "callback_data", "repos:refresh"),
        ]
    )
    await _present(msg, app, "repos_list", f"<b>{html.escape(data['org'])}</b> — {len(rows) - 1} repos", inline_keyboard(rows), data=data)


async def _show_my_chats(msg: GoyMessage, app):
    user = await User.get_or_none(telegram_id=msg.from_user.id)
    rows = (
        await Integration.filter(user_id=user.id).prefetch_related("chat")
        if user
        else []
    )
    by_chat = {}
    for item in rows:
        by_chat.setdefault(item.chat.chat_id, []).append(item)
    buttons = [
        [(f"💬 chat {cid} ({len(items)})", "callback_data", f"mychat:{cid}")]
        for cid, items in by_chat.items()
    ]
    buttons.append(
        [
            ("🔄 Refresh", "callback_data", "mychats:refresh"),
            _nav_button(msg, "menu:home"),
        ]
    )
    await _present(msg, app, "mychats", "💬 <b>Your chats with integrations</b>" if by_chat else "💬 <b>You don't have any integrations yet.</b>", inline_keyboard(buttons))


async def on_message(msg: Any, app, config: Config, bot: GoyBot):
    message = message_from_packet(bot, msg)
    if not message.from_user:
        return
    text = message.text.strip()
    if message.chat_id == message.from_user.id and text == btn_connect:
        app.set_state(*_state_key(message), "token_main")
        return await _show_token(message, app, config)
    if message.chat_id == message.from_user.id and text == btn_add_to_chat:
        bot_username = get_bot_username()
        if not bot_username:
            return await message.answer(
                "Bot identity is not available yet. Please try again in a moment."
            )
        url = f"https://t.me/{bot_username}?startgroup=true&admin=pin_messages+manage_topics"
        return await message.answer(
            "Tap below to pick a group and add me as an administrator.",
            reply_markup=inline_keyboard([[("➕ Pick a group", "url", url)]]),
        )
    if message.chat_id == message.from_user.id and text == btn_repos:
        return await _show_orgs(message, app, config)
    if message.chat_id == message.from_user.id and text == btn_my_chats:
        return await _show_my_chats(message, app)
    if message.chat_id == message.from_user.id and text == btn_help:
        return await message.answer(help, reply_markup=help_keyboard())
    if _command(text, "start"):
        if message.chat_id != message.from_user.id:
            return await message.answer("Please send /start in private chat.")
        if not await User.is_registered(message.from_user.id):
            await User.register(message.from_user.id)
        arg = _args(text)
        if arg.startswith("installed_"):
            try:
                inst = await Installation.get_by_installation_id(int(arg[10:]))
            except ValueError:
                inst = None
            if inst:
                return await message.answer(
                    f"✅ <b>GitHub App installed</b> for <code>{inst.account_login}</code>.",
                    reply_markup=main_menu_keyboard(),
                )
        return await message.answer(welcome, reply_markup=main_menu_keyboard())
    if _command(text, "help"):
        if message.chat_id != message.from_user.id:
            return await message.answer("Please send /help in private chat.")
        return await message.answer(help, reply_markup=help_keyboard())
    if _command(text, "mail"):
        if message.chat_id != config.settings.owner_id:
            return await message.answer(
                "This command can only be used by the bot owner."
            )
        parts = text.split(maxsplit=2)
        if len(parts) < 3 or parts[1].lower() not in {"users", "chats", "all"}:
            return await message.answer("Usage:\n/mail [users|chats|all] <message>")
        users = await User.all() if parts[1].lower() in {"users", "all"} else []
        chats = await Chat.all() if parts[1].lower() in {"chats", "all"} else []
        await message.answer(
            f"Broadcast started.\nTotal recipients: {len(users) + len(chats)}"
        )
        sent_users = sent_chats = 0
        for recipient in users:
            try:
                await bot.send_message(
                    recipient.telegram_id, parts[2], disable_web_page_preview=True
                )
                sent_users += 1
            except Exception:
                pass
        for recipient in chats:
            try:
                await bot.send_message(
                    recipient.chat_id,
                    parts[2],
                    message_thread_id=recipient.topic_id or None,
                    disable_web_page_preview=True,
                )
                sent_chats += 1
            except Exception:
                pass
        return await message.answer(
            f"Broadcast finished.\nSuccessfully delivered to {sent_users} users and {sent_chats} chats."
        )
    if _command(text, "error"):
        if message.from_user.id != config.settings.owner_id:
            return await message.answer("You are not allowed to use this command.")
        raise RuntimeError("This is a test error for debugging purposes.")
    if _command(text, "install") and _is_dm(message):
        if not config.github_app.is_configured:
            return await message.answer(
                "GitHub App authentication isn't configured. Use <b>🔌 Connect</b>."
            )
        return await message.answer(
            "Click below to install the GitHub App.",
            reply_markup=inline_keyboard(
                [
                    [
                        (
                            "🔗 Install GitHub App",
                            "url",
                            install_url(config, message.from_user.id),
                        )
                    ]
                ]
            ),
        )
    if _command(text, "token"):
        if not _is_dm(message):
            return await message.answer(
                "Please use /token in private chat — your token is sensitive."
            )
        arg = _args(text)
        if arg:
            try:
                await message.delete()
            except Exception:
                pass
            result = validate(arg)
            if isinstance(result, HookError):
                return await message.answer(f"❌ {result.message}")
            if not await User.get_or_none(telegram_id=message.from_user.id):
                await User.register(message.from_user.id)
            await User.write_token(message.from_user.id, arg)
            return await message.answer("✅ Token saved.")
        app.set_state(*_state_key(message), "token_main")
        return await _show_token(message, app, config)
    state = app.get_state(*_state_key(message))
    if state == "token_input" and _is_dm(message):
        try:
            await message.delete()
        except Exception:
            pass
        result = validate(text)
        if isinstance(result, HookError):
            return await message.answer(f"❌ {result.message}")
        await User.write_token(message.from_user.id, text)
        app.set_state(*_state_key(message), "token_main")
        return await _show_token(message, app, config)
    if _command(text, "integrate"):
        if _is_dm(message):
            return await message.answer(
                "This command works only in a group or channel."
            )
        admins = await get_admin_ids(bot, message.chat_id)
        if admins is None or message.from_user.id not in admins:
            return await message.answer(
                "Only chat administrators can use this command."
            )
        repo = _args(text)
        if not repo or "/" not in repo:
            return await message.answer(
                "Invalid command. Use <code>/integrate username/repository</code>"
            )
        result = await integrate_repo(
            bot, message.chat_id, message.from_user.id, repo, config
        )
        return await message.answer(
            result.message if result.success else f"❌ {result.message}"
        )
    if _command(text, "integrations"):
        if _is_dm(message):
            return await message.answer(
                "This command works only in a group or channel."
            )
        if not await is_user_admin(bot, int(message.chat_id or 0), message.from_user.id):
            return await message.answer("Only chat administrators can use this command.")
        await Chat.ensure_registered(message.chat_id)
        items = await Chat.get_integrations(message.chat_id)
        return await message.answer(
            integrations_header if items else "No integrations in this chat yet.",
            reply_markup=build_integrations_keyboard(items) if items else inline_keyboard([[('✕ Close', 'callback_data', 'nav:close')]]),
        )
    if _command(text, "events"):
        if _is_dm(message):
            return await _show_my_chats(message, app)
        if not await is_user_admin(
            bot, int(message.chat_id or 0), message.from_user.id
        ):
            return await message.answer(
                "Only administrators can change event settings."
            )
        await Chat.ensure_registered(message.chat_id)
        event_text, event_markup = await _event_keyboard(int(message.chat_id), config, message)
        return await message.answer(event_text, reply_markup=event_markup)
    if _command(text, "delete"):
        if _is_dm(message) or not await is_user_admin(
            bot, message.chat_id, message.from_user.id
        ):
            return await message.answer(
                "Only chat administrators can use this command."
            )
        repo = _args(text)
        item = await Integration.get_by_chat_and_repo(message.chat_id, repo)
        if not item:
            return await message.answer(
                f"Repository <code>{repo}</code> is not integrated in this chat."
            )
        await Integration.delete_by_id(item.id)
        return await message.answer(f"✅ Repository <code>{repo}</code> removed.")
    if _command(text, "set_topic"):
        if _is_dm(message) or not await is_user_admin(
            bot, message.chat_id, message.from_user.id
        ):
            return await message.answer("Only administrators can use this command.")
        if not message.message_thread_id:
            return await message.answer("Send /set_topic from inside a forum topic.")
        await Chat.ensure_registered(message.chat_id)
        await Chat.set_topic(message.chat_id, message.message_thread_id)
        return await message.answer("✅ Topic set.")
    if _command(text, "reinstall"):
        if _is_dm(message) or not await is_user_admin(
            bot, message.chat_id, message.from_user.id
        ):
            return await message.answer("Only administrators can run /reinstall.")
        if config.notifications.mode == "polling":
            return await message.answer("Polling notifications are active. This command is not needed in the current mode.")
        items = await Chat.get_integrations(message.chat_id)
        good, bad = [], []
        for item in items:
            user = await User.get_or_none(id=item.user_id)
            if not user or not user.token:
                bad.append((item.repository_name, "No GitHub token saved."))
                continue
            result = await asyncio.to_thread(
                update_webhook,
                config.api.host,
                item.integration_token,
                user.token,
                item.repository_name,
            )
            (good if not isinstance(result, HookError) else bad).append(
                item.repository_name
                if not isinstance(result, HookError)
                else (item.repository_name, result.message)
            )
        return await message.answer(
            "✅ Updated: " + ", ".join(good) if good else "❌ No webhooks updated."
        )
    if _is_dm(message) and text and not text.startswith("/"):
        user = await User.get_or_none(telegram_id=message.from_user.id)
        if not user:
            return await message.answer("You are not registered. Please use /start.")
        if user.token:
            repo = check_repo(user.token, text)
            return await message.answer(
                f"❌ {repo.message}"
                if isinstance(repo, HookError)
                else f"<b><a href='https://github.com/{repo.full_name}'>{repo.full_name}</a></b> ⭐ {repo.stargazers_count}\n<i>{repo.description or 'No description'}</i>"
            )
        result = validate(text)
        if isinstance(result, HookError):
            return await message.answer(f"❌ {result.message}")
        await User.write_token(message.from_user.id, text)
        return await message.answer("✅ Token saved.")


async def on_callback(cb: Any, app, config: Config, bot: GoyBot):
    user_id = int(cb.from_id or 0)
    chat_id = cb.chat_id
    raw_data = str(cb.data or "")
    data = resolve(raw_data)
    if data is None:
        await cb.answer("This button has expired. Please open the menu again.", alert=True)
        return
    raw = cb.raw.get("raw", {}) if isinstance(cb.raw, dict) else {}
    callback_message = (
        raw.get("callback_query", {}).get("message") if isinstance(raw, dict) else None
    )
    msg = GoyMessage(
        bot,
        callback_message
        or {"chat": {"id": chat_id}, "message_id": cb.msg_id, "text": cb.text},
        is_callback=True,
    )
    msg.from_user = SimpleNamespace(id=user_id)
    if msg.chat_id != chat_id or msg.message_id != cb.msg_id:
        await cb.answer("This button is no longer valid.", alert=True)
        return
    if data.startswith(("integ:", "toggle_event:")) and not await is_user_admin(bot, chat_id, user_id):
        await cb.answer("Only chat administrators can use this menu.", alert=True)
        return
    if data.startswith(("repos:", "mychat:", "mychats", "myinteg:", "mydelete:", "myevents:", "myevent:", "token:")) and chat_id != user_id:
        await cb.answer("This menu is available only in private chat.", alert=True)
        return
    if data == "menu:connect":
        app.set_state(chat_id, user_id, "token_main")
        await cb.answer()
        return await _show_token(msg, app, config)
    if data == "menu:home":
        await cb.answer()
        return await msg.answer(welcome, reply_markup=main_menu_keyboard())
    if data == "menu:add":
        bot_username = get_bot_username()
        if not bot_username:
            await cb.answer()
            return await msg.answer("Bot identity is not available yet. Please try again in a moment.")
        url = f"https://t.me/{bot_username}?startgroup=true&admin=pin_messages+manage_topics"
        await cb.answer()
        return await msg.answer("Tap below to pick a group and add me as an administrator.", reply_markup=inline_keyboard([[('➕ Pick a group', 'url', url)], [("« Back", "callback_data", "menu:home")]]))
    if data == "menu:repos":
        await cb.answer()
        await _loading(msg, app, "repos_orgs")
        asyncio.create_task(_deferred(_show_orgs(msg, app, config), msg, app, "repos_orgs"))
        return
    if data == "menu:chats":
        await cb.answer()
        await _loading(msg, app, "mychats")
        asyncio.create_task(_deferred(_show_my_chats(msg, app), msg, app, "mychats"))
        return
    if data == "menu:help":
        await cb.answer()
        return await msg.answer(help, reply_markup=help_keyboard(True))
    if data == "nav:close":
        try:
            await msg.delete()
        except Exception:
            pass
        app.clear_state(chat_id, user_id)
        await cb.answer()
        return
    if data == "token:update":
        if chat_id != user_id:
            return await cb.answer("This action is available only in private chat.", alert=True)
        app.set_state(chat_id, user_id, "token_input")
        await cb.answer()
        return await msg.answer(
            "📥 Send your Personal Access Token. This message will be deleted.\n\nUse the permissions shown in the PAT menu.",
            reply_markup=inline_keyboard([[('« Back', 'callback_data', 'token:main')]])
        )
    if data == "token:test":
        if chat_id != user_id:
            return await cb.answer("This action is available only in private chat.", alert=True)
        user = await User.get_or_none(telegram_id=user_id)
        result = (
            validate(user.token)
            if user and user.token
            else HookError("auth", "No token to test.")
        )
        return await cb.answer(
            "✅ Token is valid."
            if not isinstance(result, HookError)
            else f"❌ {str(result.message)[:180]}",
            alert=True,
        )
    if data == "token:remove":
        if chat_id != user_id:
            return await cb.answer("This action is available only in private chat.", alert=True)
        app.set_state(chat_id, user_id, "token_remove_confirm")
        await cb.answer()
        return await msg.answer(
            "⚠️ Are you sure you want to remove your token? Polling notifications for private repositories will stop until you add a new token.",
            reply_markup=inline_keyboard(
                [
                    [
                        ("✅ Yes, remove", "callback_data", "token:remove_confirm"),
                        ("◀️ Cancel", "callback_data", "token:main"),
                    ]
                ]
            ),
        )
    if data == "token:remove_confirm":
        if chat_id != user_id:
            return await cb.answer("This action is available only in private chat.", alert=True)
        await User.filter(telegram_id=user_id).update(token=None)
        app.clear_state(chat_id, user_id)
        await cb.answer("Token removed.", alert=True)
        return await _show_token(msg, app, config)
    if data == "token:main":
        if chat_id != user_id:
            return await cb.answer("This action is available only in private chat.", alert=True)
        app.set_state(chat_id, user_id, "token_main")
        await cb.answer()
        return await _show_token(msg, app, config)
    if data == "repos:refresh":
        state_data = app.get_state_data(chat_id, user_id) or {}
        user = await User.get_or_none(telegram_id=user_id)
        if user is not None:
            await invalidate_for_user(user, config)
        if app.get_state(chat_id, user_id) == "repos_list":
            await cb.answer()
            await _loading(msg, app, "repos_list")
            asyncio.create_task(_deferred(_show_repos(msg, app, config, state_data), msg, app, "repos_list"))
            return
        await cb.answer()
        await _loading(msg, app, "repos_orgs")
        asyncio.create_task(_deferred(_show_orgs(msg, app, config), msg, app, "repos_orgs"))
        return
    if data == "repos:back_orgs":
        await cb.answer()
        await _loading(msg, app, "repos_orgs")
        asyncio.create_task(_deferred(_show_orgs(msg, app, config), msg, app, "repos_orgs"))
        return
    if data == "repos:back_repos":
        state_data = app.get_state_data(chat_id, user_id) or {}
        await cb.answer()
        await _loading(msg, app, "repos_list")
        asyncio.create_task(_deferred(_show_repos(msg, app, config, state_data), msg, app, "repos_list"))
        return
    if data.startswith("repos:org:"):
        _, _, org, personal, source, installation = data.split(":", 5)
        app.set_state(
            chat_id,
            user_id,
            "repos_list",
            {
                "org": org,
                "personal": bool(int(personal)),
                "source": source,
                "installation": int(installation),
            },
        )
        await cb.answer()
        await _loading(msg, app, "repos_list")
        asyncio.create_task(_deferred(_show_repos(
            msg, app, config, app.get_state_data(chat_id, user_id) or {}
        ), msg, app, "repos_list"))
        return
    if data.startswith("repos:repo:"):
        repo_name = data[11:]
        state_data = app.get_state_data(chat_id, user_id) or {}
        await _loading(msg, app, "repos_repo")
        user = await User.get_or_none(telegram_id=user_id)
        org = {
            "login": state_data.get("org", ""),
            "is_personal": state_data.get("personal", False),
            "source": state_data.get("source", "pat"),
            "installation_id": state_data.get("installation", 0),
        }
        repos = await list_repos_for_org(user, org, config)
        repo = next((item for item in repos if item["full_name"] == repo_name), None)
        if repo is None:
            return await cb.answer("Repository is no longer available.", alert=True)
        integrated = await Integration.filter(
            repository_name=repo_name
        ).prefetch_related("chat")
        chat_lines = []
        for item in integrated:
            try:
                chat_lines.append(f"• <code>chat {item.chat.chat_id}</code>")
            except Exception:
                pass
        app.set_state(chat_id, user_id, "repos_repo", {**state_data, "repo": repo_name})
        text = f"<b>{html.escape(repo_name)}</b>\n{'🔒 Private' if repo['private'] else '🔓 Public'} • ⭐ {repo['stars']} • {'✅ Admin' if repo['permissions_admin'] else '⚠️ No admin'}\nSource: {'🔗 GitHub App' if repo['source'] == 'app' else '🔑 Personal Access Token'}\n<i>{html.escape(repo['description'] or 'no description')}</i>\n\n🔌 <b>Integrations:</b>\n{chr(10).join(chat_lines) if chat_lines else '<i>not integrated yet</i>'}"
        rows = []
        if repo["permissions_admin"]:
            rows.append(
                [("➕ Integrate into a chat…", "callback_data", "repos:choose_chat")]
            )
        rows.append([("« Back to repos", "callback_data", "repos:back_repos")])
        return await msg.answer(text, reply_markup=inline_keyboard(rows))
    if data == "repos:choose_chat":
        state_data = app.get_state_data(chat_id, user_id) or {}
        repo_name = state_data.get("repo")
        if not await is_user_admin(bot, chat_id, user_id):
            return await cb.answer("Only chat administrators can integrate repositories.", alert=True)
        await cb.answer()
        await _loading(msg, app, "repos_choose_chat")
        chats = await list_admin_chats(bot, user_id)
        existing = await Integration.filter(repository_name=repo_name).prefetch_related(
            "chat"
        )
        blocked = set()
        for item in existing:
            try:
                blocked.add(item.chat.chat_id)
            except Exception:
                pass
        available = [item for item in chats if item["chat_id"] not in blocked]
        rows = [
            [(f"💬 {item['title']}", "callback_data", f"repos:chat:{item['chat_id']}")]
            for item in available
        ]
        rows.append(
            [("« Back to repo", "callback_data", "repos:repo:" + str(repo_name))]
        )
        if not available:
            return await msg.answer(
                "No available chats. Add me as an administrator to a group first.",
                reply_markup=inline_keyboard(rows),
            )
        app.set_state(chat_id, user_id, "repos_choose_chat", state_data)
        return await msg.answer(
            f"<b>Pick a chat to integrate <code>{html.escape(str(repo_name))}</code> into</b>\nOnly chats where I'm a member and you're an administrator are listed.",
            reply_markup=inline_keyboard(rows),
        )
    if data.startswith("repos:chat:"):
        state_data = app.get_state_data(chat_id, user_id) or {}
        repo_name = state_data.get("repo")
        target_chat = int(data.rsplit(":", 1)[1])
        result = await integrate_repo(bot, target_chat, user_id, repo_name, config)
        if result.success:
            try:
                await bot.send_message(
                    target_chat,
                    f"✅ Repository <code>{html.escape(repo_name)}</code> integrated.\nUse /events to configure event types.",
                )
            except Exception:
                pass
            return await msg.answer(
                f"🎉 <b>Done!</b>\n{result.message}",
                reply_markup=inline_keyboard(
                    [
                        [
                            ("« Back to repos", "callback_data", "repos:back_repos"),
                        ]
                    ]
                ),
            )
        return await msg.answer(
            f"❌ <b>Couldn't integrate</b>\n{result.message}",
            reply_markup=inline_keyboard(
                [[("« Back to repo", "callback_data", "repos:repo:" + str(repo_name))]]
            ),
        )
    if data.startswith("toggle_event:"):
        event = data.split(":", 1)[1]
        if not await is_user_admin(bot, chat_id, user_id):
            return await cb.answer("Only chat administrators can change event settings.", alert=True)
        setting = await EventSetting.get_or_none(chat_id=chat_id, event_type=event)
        available = None if config.notifications.mode == "polling" else await _available_events(int(chat_id), config.api.host)
        if (
            setting
            and available is not None
            and event != "ping"
            and event not in available
            and not setting.enabled
        ):
            return await cb.answer(
                "This event isn't subscribed on GitHub. Run /reinstall first.",
                alert=True,
            )
        if setting:
            setting.enabled = not setting.enabled
            await setting.save()
        await cb.answer(
            f"{event} {'enabled' if setting and setting.enabled else 'disabled'}"
        )
        event_text, event_markup = await _event_keyboard(chat_id, config, msg)
        return await _present(msg, app, "events", event_text, event_markup)
    if data == "integ:list":
        await cb.answer()
        items = await Chat.get_integrations(chat_id)
        return (
            await msg.edit_text(integrations_header, build_integrations_keyboard(items, True))
            if items
            else await msg.edit_text("No integrations in this chat anymore.", inline_keyboard([[_nav_button(msg, "menu:home")]]))
        )
    if data.startswith("integ:del:"):
        await cb.answer()
        item = await Integration.get_by_id(int(data.rsplit(":", 1)[1]))
        if item is None or item.chat_id != chat_id or not await is_user_admin(bot, chat_id, user_id):
            return await cb.answer("Only chat administrators can remove this integration.", alert=True)
        await Integration.delete_by_id(item.id)
        return await msg.edit_text("✅ Integration removed.")
    if data.startswith("integ:open:"):
        await cb.answer()
        item = await Integration.get_by_id(int(data.rsplit(":", 1)[1]))
        if item is not None and (item.chat_id != chat_id or not await is_user_admin(bot, chat_id, user_id)):
            return await cb.answer("Only chat administrators can view this integration.", alert=True)
        return (
            await msg.edit_text(
                f"<b>{item.repository_name}</b>\nAuth source: <code>{item.auth_source}</code>",
                build_management_keyboard(item.id),
            )
            if item
            else await cb.answer("Integration not found.", alert=True)
        )
    if data == "integ:events":
        if not await is_user_admin(bot, chat_id, user_id):
            return await cb.answer(
                "Only administrators can change event settings.", alert=True
            )
        await _loading(msg, app, "events")
        event_text, event_markup = await _event_keyboard(chat_id, config, msg)
        return await msg.answer(event_text, reply_markup=event_markup)
    if data.startswith("mychat:"):
        selected_chat = int(data.rsplit(":", 1)[1])
        await _loading(msg, app, "mychat_detail")
        current_user = await User.get_or_none(telegram_id=user_id)
        items = await Integration.filter(user_id=current_user.id).prefetch_related("chat").all() if current_user else []
        items = [item for item in items if item.chat and item.chat.chat_id == selected_chat]
        if not items:
            return await cb.answer("This chat is not linked to your integrations.", alert=True)
        title = await resolve_chat_title(bot, selected_chat)
        rows = [
            [
                (
                    f"🔌 {item.repository_name}",
                    "callback_data",
                    f"myinteg:{item.id}:{selected_chat}",
                )
            ]
            for item in items
        ]
        rows.append([("✏ Manage events", "callback_data", f"myevents:{selected_chat}")])
        rows.append([("« Back", "callback_data", "mychats")])
        app.set_state(chat_id, user_id, "mychat_detail", {"chat_id": selected_chat})
        return await msg.answer(
            f"<b>{html.escape(title)}</b>  <i>(id {selected_chat})</i>\n\nTap an integration to manage it, or manage events.",
            reply_markup=inline_keyboard(rows),
        )
    if data == "mychats:refresh":
        invalidate_titles()
        return await _show_my_chats(msg, app)
    if data == "mychats":
        return await _show_my_chats(msg, app)
    if data.startswith("myinteg:"):
        _, integration_id, selected_chat = data.split(":", 2)
        item = await Integration.get_by_id(int(integration_id))
        current_user = await User.get_or_none(telegram_id=user_id)
        if item is None or current_user is None or item.user_id != current_user.id or item.chat_id != int(selected_chat):
            return await cb.answer("Integration not found.", alert=True)
        app.set_state(
            chat_id,
            user_id,
            "myintegration_detail",
            {"chat_id": int(selected_chat), "integration_id": int(integration_id)},
        )
        return await msg.answer(
            f"<b>{html.escape(item.repository_name)}</b>\nAdded {item.created_at:%Y-%m-%d %H:%M UTC}\nAuth source: <code>{item.auth_source}</code>\n\n<i>Deleting removes this polling integration.</i>",
            reply_markup=inline_keyboard(
                [
                    [
                        (
                            "🗑 Delete from chat",
                            "callback_data",
                            f"mydelete:{integration_id}:{selected_chat}",
                        )
                    ],
                    [("« Back to chat", "callback_data", f"mychat:{selected_chat}")],
                ]
            ),
        )
    if data.startswith("mydelete:"):
        _, integration_id, selected_chat = data.split(":", 2)
        if not await is_user_admin(bot, int(selected_chat), user_id):
            return await cb.answer("You're no longer a chat administrator.", alert=True)
        item = await Integration.get_by_id(int(integration_id))
        current_user = await User.get_or_none(telegram_id=user_id)
        if item is None or current_user is None or item.user_id != current_user.id or item.chat_id != int(selected_chat):
            return await cb.answer("Integration not found.", alert=True)
        await Integration.delete_by_id(int(integration_id))
        await cb.answer("Integration removed.", alert=True)
        return await msg.answer(
            "Integration removed.",
            reply_markup=inline_keyboard(
                [[("« Back to chat", "callback_data", f"mychat:{selected_chat}")]]
            ),
        )
    if data.startswith("myevents:"):
        selected_chat = int(data.rsplit(":", 1)[1])
        if not await is_user_admin(bot, selected_chat, user_id):
            return await cb.answer("You're no longer a chat administrator.", alert=True)
        await _loading(msg, app, "myevents")
        settings = await EventSetting.for_chat(selected_chat)
        rows = [
            [
                (
                    f"{'✅' if item.enabled else '❌'} {event_labels.get(item.event_type, item.event_type)}",
                    "callback_data",
                    f"myevent:{selected_chat}:{item.event_type}",
                )
                for item in settings[i : i + 2]
            ]
            for i in range(0, len(settings), 2)
        ]
        rows.append([("« Back to chat", "callback_data", f"mychat:{selected_chat}")])
        return await msg.answer(
            f"✨ <b>Events for {html.escape(await resolve_chat_title(bot, selected_chat))}</b>",
            reply_markup=inline_keyboard(rows),
        )
    if data.startswith("myevent:"):
        _, selected_chat, event = data.split(":", 2)
        selected_chat = int(selected_chat)
        if not await is_user_admin(bot, selected_chat, user_id):
            return await cb.answer("You're no longer a chat administrator.", alert=True)
        setting = await EventSetting.get_or_none(
            chat_id=selected_chat, event_type=event
        )
        if setting is not None:
            setting.enabled = not setting.enabled
            await setting.save()
        await cb.answer(
            f"{event} {'enabled' if setting and setting.enabled else 'disabled'}"
        )
        settings = await EventSetting.for_chat(selected_chat)
        rows = [
            [
                (
                    f"{'✅' if item.enabled else '❌'} {event_labels.get(item.event_type, item.event_type)}",
                    "callback_data",
                    f"myevent:{selected_chat}:{item.event_type}",
                )
                for item in settings[i : i + 2]
            ]
            for i in range(0, len(settings), 2)
        ]
        rows.append([("« Back to chat", "callback_data", f"mychat:{selected_chat}")])
        return await _present(
            msg,
            app,
            "myevents",
            f"✨ <b>Events for {html.escape(await resolve_chat_title(bot, selected_chat))}</b>",
            inline_keyboard(rows),
        )


def register_handlers(app, config: Config, bot: GoyBot) -> None:
    admission = InboundAdmission()

    async def message_handler(msg: Any):
        if not admission.admit(msg, "message"):
            return
        try:
            await on_message(msg, app, config, bot)
        except SilentDrop:
            return
        except Exception as exc:
            logging.getLogger("goyifi").exception("Message handler failed")
            try:
                await bot.send_message(
                    config.settings.owner_id,
                    f"<b>❌ Handler error</b>\n<code>{html.escape(type(exc).__name__)}: {html.escape(str(exc))}</code>",
                )
            except Exception:
                pass
        finally:
            admission.release(msg)

    async def callback_handler(cb: Any):
        if not admission.admit(cb, "callback"):
            return
        try:
            await on_callback(cb, app, config, bot)
        except SilentDrop:
            return
        except Exception as exc:
            logging.getLogger("goyifi").exception("Callback handler failed")
            try:
                await bot.send_message(
                    config.settings.owner_id,
                    f"<b>❌ Callback error</b>\n<code>{html.escape(type(exc).__name__)}: {html.escape(str(exc))}</code>",
                )
            except Exception:
                pass
        finally:
            admission.release(cb)

    app.on_msg(message_handler)
    app.on_cb(callback_handler)
