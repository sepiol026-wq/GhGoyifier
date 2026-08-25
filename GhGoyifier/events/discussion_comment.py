# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""discussion_comment — comments on a discussion."""

from GhGoyifier.events._base import Comment, Discussion, GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class DiscussionCommentEvent(_Base):
    action: str
    comment: Comment
    discussion: Discussion
    repository: Repository
    sender: GitHubUser


def discussion_comment_message(
    event: DiscussionCommentEvent, ctx: EventCtx
) -> str | None:
    if event.action != "created":
        return None
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on discussion "
        f'<a href="{event.discussion.html_url}">#{event.discussion.number}</a> '
        f"in {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.discussion.title)}</i>\n"
        f'<blockquote expandable>{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register(
    "discussion_comment", DiscussionCommentEvent, discussion_comment_message
)
