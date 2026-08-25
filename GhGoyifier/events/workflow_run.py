# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""workflow_run — GitHub Actions workflow finished."""

from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, user_link
from GhGoyifier.events._registry import register


class WorkflowRun(_Base):
    name: str
    html_url: str
    head_branch: str | None = None
    head_sha: str
    status: str
    conclusion: str | None = None
    run_attempt: int = 1
    actor: GitHubUser


class WorkflowRunEvent(_Base):
    action: str
    workflow_run: WorkflowRun
    repository: Repository
    sender: GitHubUser


_icon_by_conclusion = {
    "success": "✅",
    "failure": "❌",
    "cancelled": "⚪",
    "skipped": "⏭",
    "timed_out": "⌛",
    "action_required": "⚠️",
    "neutral": "➖",
}


def workflow_run_message(
    event: WorkflowRunEvent, ctx: EventCtx
) -> str | None:
    if event.action != "completed":
        return None

    run = event.workflow_run
    icon = _icon_by_conclusion.get(run.conclusion or "", "ℹ️")
    branch = f":{_e(run.head_branch)}" if run.head_branch else ""
    attempt = f" (attempt #{run.run_attempt})" if run.run_attempt > 1 else ""
    return (
        f"<b>{icon} Workflow <i>{_e(run.name)}</i> "
        f"{_e(run.conclusion or run.status)} on {repo_link(event.repository)}{branch}</b>\n"
        f"By {user_link(run.actor)}{attempt}\n"
        f'<a href="{run.html_url}">View run</a>'
    )


register("workflow_run", WorkflowRunEvent, workflow_run_message)
