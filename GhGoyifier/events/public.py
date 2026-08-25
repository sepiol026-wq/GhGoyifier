# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""public — repo switched from private to public."""
from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import repo_link, user_link
from GhGoyifier.events._registry import register


class PublicEvent(_Base):
    repository: Repository
    sender: GitHubUser


def public_message(event: PublicEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🔓 {repo_link(event.repository)} is now public!</b>\n"
        f"By {user_link(event.sender)}"
    )


register("public", PublicEvent, public_message)
