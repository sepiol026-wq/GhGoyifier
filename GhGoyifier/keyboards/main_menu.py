# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from GhGoyifier.goygram_bot import inline_keyboard
from GhGoyifier.callback_vault import protect
from GhGoyifier.i18n import flags, tr

from goygram.types.kbd import KbdBuilder

btn_connect = "Connect"
btn_add_to_chat = "Add to chat"
btn_repos = "Repos"
btn_my_chats = "My chats"
btn_help = "Help"


def main_menu_keyboard(include_back: bool = False, lang: str = "en") -> dict:
    rows = [
        [(tr(lang, "menu.connect"), "callback_data", "menu:connect"), (tr(lang, "menu.add"), "callback_data", "menu:add")],
        [(tr(lang, "menu.repos"), "callback_data", "menu:repos"), (tr(lang, "menu.chats"), "callback_data", "menu:chats")],
        [(tr(lang, "menu.help"), "callback_data", "menu:help")],
        [(tr(lang, "menu.project"), "url", "https://github.com/sepiol026-wq/GhGoyifier")],
    ]
    if include_back:
        rows.append([("« Back", "callback_data", "menu:home")])
    return inline_keyboard(rows)


def help_keyboard(is_callback: bool = False, lang: str = "en") -> dict:
    return inline_keyboard([[("« Back" if is_callback else tr(lang, "language.close"), "callback_data", "menu:home" if is_callback else "nav:close")]])


def language_keyboard(lang: str) -> dict:
    builder = KbdBuilder(kind="inline")
    for code in ("en", "ru"):
        builder.btn(
            tr(lang, "language.en" if code == "en" else "language.ru"),
            callback_data=protect(f"lang:set:{code}"),
            icon_custom_emoji_id=flags[code].split('emoji-id="', 1)[1].split('"', 1)[0],
        )
    builder.row()
    builder.btn(tr(lang, "language.close"), callback_data=protect("nav:close"))
    builder.row()
    return builder.to_dict()
