# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""pull_request_review — someone submitted a review on a PR."""

from GhGoyifier.events._base import GitHubUser, PullRequest, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class Review(_Base):
    state: str
    body: str | None = None
    html_url: str
    user: GitHubUser


class PullRequestReviewEvent(_Base):
    action: str
    review: Review
    pull_request: PullRequest
    repository: Repository
    sender: GitHubUser


def pull_request_review_message(
    event: PullRequestReviewEvent, ctx: EventCtx
) -> str | None:
    if event.action != "submitted":
        return None

    icon, verb = {
        "approved": ("✅", "approved"),
        "changes_requested": ("🔴", "requested changes on"),
        "commented": ("💬", "commented on"),
        "dismissed": ("⚪", "dismissed review on"),
    }.get(event.review.state, ("📝", event.review.state))

    body_block = ""
    if event.review.body:
        body_block = (
            f'<blockquote expandable>'
            f"{_e(truncate(event.review.body, 300))}"
            f"</blockquote>\n"
        )

    return (
        f"<b>{icon} {user_link(event.review.user)} {verb} "
        f'<a href="{event.pull_request.html_url}">PR #{event.pull_request.number}</a> '
        f"on {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.pull_request.title)}</i>\n"
        f"{body_block}"
        f'<a href="{event.review.html_url}">View review</a>'
    )


register("pull_request_review", PullRequestReviewEvent, pull_request_review_message)
