# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""ping — fired once when GitHub creates the webhook."""
from GhGoyifier.events._base import Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import repo_link
from GhGoyifier.events._registry import register


class PingEvent(_Base):
    repository: Repository


def ping_message(event: PingEvent, ctx: EventCtx) -> str:
    return f"🏓 Repo {repo_link(event.repository)} connected and sending ping!"


register("ping", PingEvent, ping_message)
