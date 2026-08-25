# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""fork — repo forked."""
from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link
from GhGoyifier.events._registry import register


class ForkEvent(_Base):
    forkee: Repository
    repository: Repository
    sender: GitHubUser


def fork_message(event: ForkEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🍴 {repo_link(event.repository)} forked</b>\n\n"
        f"<i>Total forks count is now:</i> <code>{event.repository.forks}</code>\n"
        f'<i>Fork link:</i> <a href="{event.forkee.html_url}">'
        f"{_e(event.forkee.full_name)}</a>"
    )


register("fork", ForkEvent, fork_message)
