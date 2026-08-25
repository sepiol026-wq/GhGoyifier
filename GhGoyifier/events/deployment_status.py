# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""deployment_status — deployment status transitions."""

from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, user_link
from GhGoyifier.events._registry import register


class DeploymentStatus(_Base):
    state: str
    description: str | None = None
    environment: str
    target_url: str | None = None
    creator: GitHubUser


class Deployment(_Base):
    sha: str
    ref: str
    environment: str
    creator: GitHubUser


class DeploymentStatusEvent(_Base):
    deployment_status: DeploymentStatus
    deployment: Deployment
    repository: Repository
    sender: GitHubUser


_icon = {
    "success": "✅",
    "failure": "❌",
    "error": "❌",
    "pending": "⏳",
    "queued": "⏳",
    "in_progress": "🔄",
    "inactive": "⚪",
}


def deployment_status_message(
    event: DeploymentStatusEvent, ctx: EventCtx
) -> str | None:
    state = event.deployment_status.state
    icon = _icon.get(state, "🚢")

    target = ""
    if event.deployment_status.target_url:
        target = (
            f'\n<a href="{event.deployment_status.target_url}">View deployment</a>'
        )

    desc = ""
    if event.deployment_status.description:
        desc = f"\n<i>{_e(event.deployment_status.description)}</i>"

    return (
        f"<b>{icon} Deployment to <code>{_e(event.deployment_status.environment)}</code> "
        f"— {_e(state)} on {repo_link(event.repository)}</b>\n"
        f"By {user_link(event.deployment_status.creator)}"
        f"{desc}{target}"
    )


register(
    "deployment_status", DeploymentStatusEvent, deployment_status_message
)
