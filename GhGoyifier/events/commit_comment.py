# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""commit_comment — comment on a specific commit (outside PR review)."""

from GhGoyifier.events._base import Comment, GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class CommitCommentEvent(_Base):
    action: str
    comment: Comment
    repository: Repository
    sender: GitHubUser


def commit_comment_message(
    event: CommitCommentEvent, ctx: EventCtx
) -> str | None:
    if event.action != "created":
        return None
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on a commit in "
        f"{repo_link(event.repository)}</b>\n"
        f'<blockquote expandable>{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register("commit_comment", CommitCommentEvent, commit_comment_message)
