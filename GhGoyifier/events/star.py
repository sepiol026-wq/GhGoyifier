# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""star — repo starred / unstarred."""
from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import repo_link, user_link
from GhGoyifier.events._registry import register


class StarEvent(_Base):
    action: str
    repository: Repository
    sender: GitHubUser


def star_message(event: StarEvent, ctx: EventCtx) -> str:
    verb = "added" if event.action == "created" else "removed"
    return (
        f"<b>⭐️ On {repo_link(event.repository)} {verb} star!</b>\n\n"
        f"Total stars: <i>{event.repository.stargazers_count}</i>\n"
        f"User: {user_link(event.sender)}"
    )


register("star", StarEvent, star_message)
