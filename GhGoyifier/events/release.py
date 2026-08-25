# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""release — release published / edited / deleted."""

from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class Release(_Base):
    name: str | None = None
    tag_name: str
    html_url: str
    body: str | None = None
    prerelease: bool = False
    draft: bool = False
    author: GitHubUser


class ReleaseEvent(_Base):
    action: str
    release: Release
    repository: Repository
    sender: GitHubUser


def release_message(event: ReleaseEvent, ctx: EventCtx) -> str | None:
    if event.action != "published":
        return None
    if event.release.draft:
        return None

    title = event.release.name or event.release.tag_name
    pre = " <i>(prerelease)</i>" if event.release.prerelease else ""
    notes = truncate(event.release.body, 500)
    notes_block = (
        f'<blockquote expandable>{_e(notes)}</blockquote>\n'
        if notes else ""
    )
    return (
        f"<b>🚀 New release on {repo_link(event.repository)}{pre}</b>\n"
        f'<a href="{event.release.html_url}"><b>{_e(event.release.tag_name)}</b></a> — '
        f"<i>{_e(title)}</i>\n"
        f"By {user_link(event.release.author)}\n"
        f"{notes_block}"
    )


register("release", ReleaseEvent, release_message)
