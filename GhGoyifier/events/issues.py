# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""issues — issue opened/closed/reopened/etc."""

from GhGoyifier.events._base import GitHubUser, Issue, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, user_link
from GhGoyifier.events._registry import register


class IssuesEvent(_Base):
    action: str
    issue: Issue
    repository: Repository
    sender: GitHubUser


_interesting = {"opened", "closed", "reopened", "assigned"}


def issue_message(event: IssuesEvent, ctx: EventCtx) -> str | None:
    if event.action not in _interesting:
        return None
    return (
        f"<b>📌 On {repo_link(event.repository)} {_e(event.action)} issue!</b>\n\n"
        f"<i>{_e(event.issue.title)}</i>\n"
        f'<a href="{event.issue.html_url}">#{event.issue.number}</a> by '
        f"{user_link(event.issue.user)}"
    )


register("issues", IssuesEvent, issue_message)
