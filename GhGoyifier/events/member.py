# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""member — collaborator added / removed / edited."""

from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import repo_link, user_link
from GhGoyifier.events._registry import register


class MemberEvent(_Base):
    action: str
    member: GitHubUser
    repository: Repository
    sender: GitHubUser


def member_message(event: MemberEvent, ctx: EventCtx) -> str | None:
    if event.action != "added":
        return None
    return (
        f"<b>👥 {user_link(event.member)} added as collaborator to "
        f"{repo_link(event.repository)}</b>\n"
        f"By {user_link(event.sender)}"
    )


register("member", MemberEvent, member_message)
