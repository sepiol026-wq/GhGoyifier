# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""pull_request_review_comment — line-level comment on a PR diff."""

from GhGoyifier.events._base import Comment, GitHubUser, PullRequest, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class PullRequestReviewCommentEvent(_Base):
    action: str
    comment: Comment
    pull_request: PullRequest
    repository: Repository
    sender: GitHubUser


def pull_request_review_comment_message(
    event: PullRequestReviewCommentEvent, ctx: EventCtx
) -> str | None:
    if event.action != "created":
        return None

    path = f" <code>{_e(event.comment.path)}</code>" if event.comment.path else ""
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on "
        f'<a href="{event.pull_request.html_url}">PR #{event.pull_request.number}</a>'
        f"{path} in {repo_link(event.repository)}</b>\n"
        f'<blockquote expandable>{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register(
    "pull_request_review_comment",
    PullRequestReviewCommentEvent,
    pull_request_review_comment_message,
)
