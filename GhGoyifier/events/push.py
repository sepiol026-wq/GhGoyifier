# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""push — commits pushed to a branch.

File lists (added / removed / modified) come straight out of the webhook
payload — no API call needed. The line-count diff (`+N / -N`) does need an
API hit per commit, so we treat it as optional enrichment using whichever
auth context is available (GitHub App installation or PAT).
"""
import logging

from github import GithubException
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    Timeout,
)

from GhGoyifier.events._base import GitHubUser, Repository, _Base
from GhGoyifier.events._context import EventCtx, make_github_client
from GhGoyifier.events._formatting import _ as _e
from GhGoyifier.events._formatting import truncate
from GhGoyifier.events._registry import register


class CommitAuthor(_Base):
    name: str
    email: str | None = None
    username: str | None = None


class Commit(_Base):
    id: str
    message: str
    url: str
    author: CommitAuthor


    added: list[str] = []
    removed: list[str] = []
    modified: list[str] = []


class PushEvent(_Base):
    ref: str
    compare: str
    commits: list[Commit] = []
    repository: Repository
    sender: GitHubUser


def commit_message(event: PushEvent, ctx: EventCtx) -> str:
    branch = event.ref.split("/")[-1]
    repo_link_str = (
        f'<a href="{event.repository.html_url}">'
        f"{_e(event.repository.full_name)}:{_e(branch)}</a>"
    )

    if not event.commits:
        return f"<b>📏 On {repo_link_str} new empty push</b>"





    repo_api = None
    gh = make_github_client(ctx)
    if gh is not None:
        try:
            repo_api = gh.get_repo(event.repository.full_name)
        except (RequestsConnectionError, Timeout) as e:

            logging.info(
                "GitHub API unreachable for %s (transient %s); skipping diff stats",
                event.repository.full_name,
                type(e).__name__,
            )
        except GithubException as e:
            logging.warning(
                "GitHub rejected line-stat fetch for %s: HTTP %s — %s",
                event.repository.full_name,
                e.status,
                e.data,
            )
        except Exception as e:
            logging.warning(
                "Couldn't open repo %s for line-stat enrichment: %s: %s",
                event.repository.full_name,
                type(e).__name__,
                e,
            )

    blocks = []
    for c in event.commits:
        author_name = _e(c.author.name)
        if c.author.username:
            author_link = (
                f'<a href="https://github.com/{_e(c.author.username)}">'
                f"@{_e(c.author.username)}</a>"
            )
        else:
            author_link = f"<i>{author_name}</i>"





        message_text = truncate(c.message, 500)
        block = (
            f'<blockquote expandable><b>Commit '
            f'<a href="{c.url}">#{c.id[:7]}</a> by '
            f"<i>{author_name} ({author_link})</i></b>\n"
            f"<i>{_e(message_text)}</i>\n"
        )


        if c.added:
            block += (
                f"\n<b>🔧 Created files:</b>\n"
                f"<code>{_e(chr(10).join(c.added))}</code>\n"
            )
        if c.removed:
            block += (
                f"\n<b>🗑 Removed files:</b>\n"
                f"<code>{_e(chr(10).join(c.removed))}</code>\n"
            )
        if c.modified:
            block += (
                f"\n<b>🖊 Modified files:</b>\n"
                f"<code>{_e(chr(10).join(c.modified))}</code>\n"
            )





        if repo_api is not None:
            try:
                detail = repo_api.get_commit(c.id)
                add_lines = sum(f.additions for f in detail.files)
                del_lines = sum(f.deletions for f in detail.files)
                block += (
                    f"\n<b>⌨️ Diff:</b>\n"
                    f"➕ {add_lines}\n➖ {del_lines}\n"
                )
            except (RequestsConnectionError, Timeout) as e:
                logging.info(
                    "GitHub API unreachable fetching commit %s/%s "
                    "(transient %s); skipping diff stats",
                    event.repository.full_name,
                    c.id[:7],
                    type(e).__name__,
                )
            except GithubException as e:
                logging.warning(
                    "GitHub rejected diff fetch for %s/%s: HTTP %s — %s",
                    event.repository.full_name,
                    c.id[:7],
                    e.status,
                    e.data,
                )
            except Exception as e:
                logging.warning(
                    "Couldn't fetch line counts for %s/%s: %s: %s",
                    event.repository.full_name,
                    c.id[:7],
                    type(e).__name__,
                    e,
                )

        block += "</blockquote>"
        blocks.append(block)

    header = (
        f"<b>📏 On {repo_link_str} new commits!</b>\n"
        f"{len(event.commits)} commits pushed.\n"
        f'<a href="{event.compare}">Compare changes</a>\n\n'
    )
    return header + "\n".join(blocks)


register("push", PushEvent, commit_message)
