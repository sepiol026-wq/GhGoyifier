# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
from GhGoyifier.goygram_bot import inline_keyboard

integrations_header = (
    "<b>Integrations in this chat</b>\n"
    "Tap a repository to manage it, or <b>Manage events</b> to toggle event types."
)


def build_integrations_keyboard(integrations: list, is_callback: bool = False) -> dict:
    rows = [
        [(f"🔌 {item.repository_name}", "callback_data", f"integ:open:{item.id}")]
        for item in integrations
    ]
    rows.append([("✏ Manage events", "callback_data", "integ:events")])
    rows.append([("« Back" if is_callback else "✕ Close", "callback_data", "menu:home" if is_callback else "nav:close")])
    return inline_keyboard(rows)


def build_management_keyboard(integration_id: int) -> dict:
    return inline_keyboard(
        [
            [("🗑 Delete from chat", "callback_data", f"integ:del:{integration_id}")],
            [("« Back", "callback_data", "integ:list")],
        ]
    )
