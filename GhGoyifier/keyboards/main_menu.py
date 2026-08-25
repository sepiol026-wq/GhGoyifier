# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from GhGoyifier.goygram_bot import inline_keyboard

btn_connect = "Connect"
btn_add_to_chat = "Add to chat"
btn_repos = "Repos"
btn_my_chats = "My chats"
btn_help = "Help"


def main_menu_keyboard(include_back: bool = False) -> dict:
    rows = [
        [("🔌 Connect", "callback_data", "menu:connect"), ("➕ Add to chat", "callback_data", "menu:add")],
        [("🏢 Repos", "callback_data", "menu:repos"), ("💬 My chats", "callback_data", "menu:chats")],
        [("❓ Help", "callback_data", "menu:help")],
        [("📦 GhGoyifier", "url", "https://github.com/sepiol026-wq/GhGoyifier")],
    ]
    if include_back:
        rows.append([("« Back", "callback_data", "menu:home")])
    return inline_keyboard(rows)


def help_keyboard(is_callback: bool = False) -> dict:
    return inline_keyboard([[("« Back" if is_callback else "✕ Close", "callback_data", "menu:home" if is_callback else "nav:close")]])
