# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""issue_comment — comments on issues AND on PRs (without code line)."""

from GhGoyifier.events._base import Comment, GitHubUser, Issue, Repository, _Base
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import repo_link, truncate, user_link
from GhGoyifier.events._registry import register


class IssueCommentEvent(_Base):
    action: str
    comment: Comment
    issue: Issue
    repository: Repository
    sender: GitHubUser


def issue_comment_message(
    event: IssueCommentEvent, ctx: EventCtx
) -> str | None:
    if event.action != "created":
        return None

    is_pr = event.issue.pull_request is not None
    label = "PR" if is_pr else "issue"
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on "
        f'<a href="{event.issue.html_url}">{label} #{event.issue.number}</a> '
        f"in {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.issue.title)}</i>\n"
        f'<blockquote expandable>{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register("issue_comment", IssueCommentEvent, issue_comment_message)
