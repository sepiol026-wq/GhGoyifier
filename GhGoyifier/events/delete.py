# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""delete — branch or tag deleted."""
from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link
from GhGoyifier.events._registry import register


class DeleteEvent(_Base):
    ref: str
    ref_type: str
    repository: Repository
    sender: GitHubUser


def delete_message(event: DeleteEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🗑 On {repo_link(event.repository)} deleted "
        f"{_e(event.ref_type)} {_e(event.ref)}</b>"
    )


register("delete", DeleteEvent, delete_message)
