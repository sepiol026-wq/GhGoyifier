# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""Small helpers shared between formatters (HTML escaping, link helpers, truncation)."""
from html import escape as _escape

from GhGoyifier.events._base import GitHubUser, Repository

_ = _escape


def truncate(text: str | None, limit: int = 400) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def user_link(user: GitHubUser) -> str:
    url = user.html_url or f"https://github.com/{user.login}"
    return f'<a href="{url}">@{_(user.login)}</a>'


def repo_link(repo: Repository) -> str:
    return f'<a href="{repo.html_url}">{_(repo.full_name)}</a>'
