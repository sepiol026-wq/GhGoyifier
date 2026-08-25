# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import re
from html import escape

EMOJI: dict[str, tuple[str, str]] = {
    "✅": ("5271529115491511946", "✅"),
    "❌": ("5388785832956016892", "❌"),
    "❎": ("5388785832956016892", "❌"),
    "⚠️": ("5355133243773435190", "⚠️"),
    "⚠": ("5355133243773435190", "⚠️"),
    "⚪️": ("5323420197397215872", "⚪️"),
    "⚪": ("5323420197397215872", "⚪️"),
    "⭐️": ("5289728073040672852", "⭐️"),
    "🔄": ("5253464392850221514", "🔃"),
    "🔃": ("5253464392850221514", "🔃"),
    "🗑": ("5255831443816327915", "🗑"),
    "🔗": ("5253490441826870592", "🔗"),
    "🔌": ("5253490441826870592", "🔗"),
    "👋": ("4918354603281482671", "👋"),
    "📌": ("5253961389285845297", "📌"),
    "📦": ("5325732612084351248", "📦"),
    "🏢": ("5118686540985271080", "💼"),
    "💼": ("5118686540985271080", "💼"),
    "➕": ("4918438965029110683", "🆕"),
    "➖": ("5116204921766544244", "⏬"),
    "🆕": ("4918438965029110683", "🆕"),
    "💬": ("5429259122262422749", "💬"),
    "❓": ("5116240346656801621", "❓"),
    "🔑": ("5255713220546538619", "💳"),
    "🧪": ("5134183530313548836", "🧪"),
    "🔒": ("4904500559203009298", "🔒"),
    "🔓": ("5400257862402325744", "🔓"),
    "👤": ("5255835635704408236", "👤"),
    "📝": ("5256230583717079814", "📝"),
    "✏": ("5282819631029958269", "✒️"),
    "✏️": ("5282819631029958269", "✒️"),
    "✒": ("5282819631029958269", "✒️"),
    "✒️": ("5282819631029958269", "✒️"),
    "🟣": ("5122933683820430249", "⭕️"),
    "👥": ("5255835635704408236", "👤"),
    "🏓": ("5422543773391408326", "🎲"),
    "🎲": ("5422543773391408326", "🎲"),
    "📏": ("5253961389285845297", "📌"),
    "📥": ("5325732612084351248", "📦"),
    "🚀": ("5274168450204316527", "🛸"),
    "🛸": ("5274168450204316527", "🛸"),
    "🍴": ("4915883064350999336", "🍴"),
    "💭": ("5325642653994336033", "💭"),
    "🚢": ("5226576540367598508", "🚚"),
    "🚚": ("5226576540367598508", "🚚"),
    "🔧": ("5445245780812119048", "🔧"),
    "🔴": ("5122933683820430249", "⭕️"),
    "🖇": ("5253490441826870592", "🔗"),
    "🖊": ("5282819631029958269", "✒️"),
    "⌨️": ("5289835022021310150", "💻"),
    "💻": ("5289835022021310150", "💻"),
    "🚨": ("5116508099213001597", "🚨"),
    "🎉": ("5366045973988522066", "✨"),
    "✨": ("5366045973988522066", "✨"),
    "💡": ("5366402052547165699", "💡"),
    "ℹ️": ("5366402052547165699", "💡"),
}

_sorted = sorted(EMOJI, key=len, reverse=True)
_tag_re = re.compile(r"(<[^>]+>)")
_emoji_re = re.compile("|".join(re.escape(item) for item in _sorted))
_link_re = re.compile(r"(?:<a href=[\"'](https?://github\.com/[^\"']+)[\"'][^>]*>(.*?)</a>|(https?://github\.com/[^\s<]+))", re.IGNORECASE)


def premiumize_html(text: str) -> str:
    chunks = _tag_re.split(str(text))
    for index, chunk in enumerate(chunks):
        if chunk.startswith("<") and chunk.endswith(">"):
            continue

        def replace(match: re.Match[str]) -> str:
            emoji_id, rendered = EMOJI[match.group(0)]
            return f"<tg-emoji emoji-id={emoji_id}>{rendered}</tg-emoji>"

        chunks[index] = _emoji_re.sub(replace, chunk)
    return "".join(chunks)


def rich_html(text: str) -> str:
    rendered = premiumize_html(text)
    chunks = _tag_re.split(rendered)
    in_pre = False
    for index, chunk in enumerate(chunks):
        if chunk.startswith("<") and chunk.endswith(">"):
            tag = chunk.lower()
            if tag.startswith("<pre") and not tag.startswith("</"):
                in_pre = True
            elif tag.startswith("</pre"):
                in_pre = False
            continue
        if not in_pre:
            chunks[index] = chunk.replace("\n", "<br>")
    return "".join(chunks)


def button_icon(text: str) -> tuple[str, str | None]:
    for glyph in _sorted:
        if text.startswith(glyph):
            emoji_id, _ = EMOJI[glyph]
            return text[len(glyph):].lstrip(), emoji_id
    return text, None


def extract_github_buttons(text: str, markup: dict | None = None) -> tuple[str, dict | None]:
    links: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        url = match.group(1) or match.group(3)
        label = re.sub(r"<[^>]+>", "", match.group(2) or "Open on GitHub").strip()
        if not any(existing == url for existing, _ in links):
            links.append((url, label or "Open on GitHub"))
        return label or "Open on GitHub"

    text = _link_re.sub(replace, text)
    if not links:
        return text, markup
    rows = [[{"text": label, "url": url, "icon_custom_emoji_id": EMOJI["🔗"][0]}] for url, label in links]
    if markup and "inline_keyboard" in markup:
        markup = {**markup, "inline_keyboard": [*markup["inline_keyboard"], *rows]}
    elif not markup:
        markup = {"inline_keyboard": rows}
    return text, markup


def rich_button_rows(markup: dict | None) -> str:
    if not markup or not markup.get("inline_keyboard"):
        return ""
    rows = []
    for row in markup["inline_keyboard"]:
        buttons = []
        for button in row:
            label = escape(str(button.get("text", "")))
            emoji_id = button.get("icon_custom_emoji_id")
            if emoji_id:
                rendered = next((glyph for ident, glyph in EMOJI.values() if ident == str(emoji_id)), "")
                if rendered:
                    label = f"<tg-emoji emoji-id={emoji_id}>{rendered}</tg-emoji> {label}"
            if button.get("url"):
                button_type = "url"
                attr = f'url="{escape(str(button["url"]), quote=True)}"'
            elif button.get("callback_data") is not None:
                button_type = "callback_data"
                attr = f'data="{escape(str(button["callback_data"]), quote=True)}"'
            else:
                continue
            style = f' style="{escape(str(button["style"]), quote=True)}"' if button.get("style") else ""
            buttons.append(f'<tg-button type="{button_type}"{style} {attr}>{label}</tg-button>')
        if buttons:
            rows.append("<tg-button-row>" + "".join(buttons) + "</tg-button-row>")
    return "".join(rows)
