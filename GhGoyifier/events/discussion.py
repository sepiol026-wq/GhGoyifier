# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""discussion — GitHub Discussions: created/closed/reopened/answered."""

from GhGoyifier.events._base import Discussion, GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class DiscussionEvent(_Base):
    action: str
    discussion: Discussion
    repository: Repository
    sender: GitHubUser


_interesting = {"created", "closed", "reopened", "answered"}
_iconS = {"created": "💭", "closed": "🔒", "reopened": "🔓", "answered": "✅"}


def discussion_message(
    event: DiscussionEvent, ctx: EventCtx
) -> str | None:
    if event.action not in _interesting:
        return None
    icon = _iconS.get(event.action, "💭")
    body = truncate(event.discussion.body, 300)
    body_block = (
        f'<blockquote expandable>{_e(body)}</blockquote>\n'
        if body else ""
    )
    return (
        f"<b>{icon} {user_link(event.sender)} {_e(event.action)} discussion "
        f'<a href="{event.discussion.html_url}">#{event.discussion.number}</a> '
        f"in {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.discussion.title)}</i>\n"
        f"{body_block}"
    )


register("discussion", DiscussionEvent, discussion_message)
