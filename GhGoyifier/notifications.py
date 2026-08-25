# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import time
from collections import defaultdict
from typing import Any

import aiohttp

from GhGoyifier.anti_abuse import SilentDrop
from GhGoyifier.config import Config
from GhGoyifier.db.functions import Chat, EventSetting, Integration
from GhGoyifier.goygram_bot import GoyBot, inline_keyboard
from GhGoyifier.i18n import event_label

_event_names = {
    "PushEvent": "push",
    "PullRequestEvent": "pull_request",
    "IssuesEvent": "issues",
    "IssueCommentEvent": "issue_comment",
    "PullRequestReviewEvent": "pull_request_review",
    "PullRequestReviewCommentEvent": "pull_request_review_comment",
    "CommitCommentEvent": "commit_comment",
    "ReleaseEvent": "release",
    "CreateEvent": "create",
    "DeleteEvent": "delete",
    "ForkEvent": "fork",
    "WorkflowRunEvent": "workflow_run",
    "DeploymentEvent": "deployment_status",
    "DeploymentStatusEvent": "deployment_status",
    "MemberEvent": "member",
    "PublicEvent": "public",
    "WatchEvent": "star",
    "GollumEvent": "discussion",
    "PageBuildEvent": "page_build",
    "RepositoryEvent": "repository",
    "TeamEvent": "team",
    "MembershipEvent": "membership",
    "OrganizationEvent": "organization",
    "ProjectEvent": "project",
    "ProjectV2Event": "project",
    "ProjectCardEvent": "project_card",
    "PullRequestReviewThreadEvent": "pull_request_review_thread",
    "PackageEvent": "package",
    "WorkflowJobEvent": "workflow_job",
    "CheckRunEvent": "check_run",
    "CheckSuiteEvent": "check_suite",
    "StatusEvent": "status",
    "CommitStatusEvent": "status",
    "CodeScanningAlertEvent": "code_scanning",
    "SecretScanningAlertEvent": "secret_scanning",
    "RepositoryVulnerabilityAlertEvent": "vulnerability_alert",
    "SecurityAdvisoryEvent": "security_advisory",
    "LabelEvent": "label",
    "MilestoneEvent": "milestone",
    "BranchProtectionRuleEvent": "branch_protection_rule",
}
event_labels = {
    "push": "Push",
    "pull_request": "Pull request",
    "issues": "Issue",
    "issue_comment": "Issue comment",
    "pull_request_review": "Pull request review",
    "pull_request_review_comment": "Pull request review comment",
    "commit_comment": "Commit comment",
    "release": "Release",
    "workflow_run": "Workflow run",
    "deployment_status": "Deployment",
    "discussion": "Discussion",
    "discussion_comment": "Discussion comment",
    "fork": "Fork",
    "star": "Star",
    "create": "Reference created",
    "delete": "Reference deleted",
    "member": "Repository member",
    "public": "Repository visibility",
    "page_build": "Pages build",
    "repository": "Repository",
    "team": "Team",
    "membership": "Membership",
    "organization": "Organization",
    "project": "Project",
    "project_card": "Project card",
    "pull_request_review_thread": "Pull request review thread",
    "package": "Package",
    "workflow_job": "Workflow job",
    "check_run": "Check run",
    "check_suite": "Check suite",
    "status": "Commit status",
    "code_scanning": "Code scanning alert",
    "secret_scanning": "Secret scanning alert",
    "vulnerability_alert": "Vulnerability alert",
    "security_advisory": "Security advisory",
    "label": "Label",
    "milestone": "Milestone",
    "branch_protection_rule": "Branch protection rule",
}

_api = "https://api.github.com"
_seen: set[str] = set()
_headers: dict[str, dict[str, str]] = {}
_next_notifications: dict[int, float] = {}
_event_watermarks: dict[str, str] = {}
_commit_watermarks: dict[str, str] = {}
_delivered_commit_heads: set[str] = set()
_max_new_events_per_repo = 10
_started_at = time.time()
_primed = False
_log = logging.getLogger("goyifi.polling")


def _headers_for(token: str | None, cache_key: str) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Goyifier"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if cache_key.startswith(("events:", "commits:", "commit-range:")):
        return headers
    previous = _headers.get(cache_key, {})
    if previous.get("etag"):
        headers["If-None-Match"] = previous["etag"]
    if previous.get("last_modified"):
        headers["If-Modified-Since"] = previous["last_modified"]
    return headers


async def _get(session: aiohttp.ClientSession, path: str, token: str | None, cache_key: str) -> tuple[int, dict, Any]:
    async with session.get(f"{_api}{path}", headers=_headers_for(token, cache_key), timeout=aiohttp.ClientTimeout(total=12)) as response:
        if response.status == 304:
            return 304, dict(response.headers), None
        data = await response.json(content_type=None)
        if response.headers.get("ETag") or response.headers.get("Last-Modified"):
            _headers[cache_key] = {
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
            }
        return response.status, dict(response.headers), data


def _repository_name(value: dict) -> str:
    return str((value.get("repo") or {}).get("name") or (value.get("repository") or {}).get("full_name") or "")


async def _event_text(session: aiohttp.ClientSession, repo: str, event: dict, token: str | None, lang: str = "en") -> tuple[str, str, str]:
    event_type = _event_names.get(str(event.get("type")), "github")
    payload = event.get("payload") or {}
    actor = html.escape(str((event.get("actor") or {}).get("display_login") or (event.get("actor") or {}).get("login") or "GitHub"))
    action = html.escape(str(payload.get("action") or "updated"))
    title = html.escape(str((payload.get("release") or {}).get("name") or (payload.get("issue") or {}).get("title") or (payload.get("pull_request") or {}).get("title") or ""))
    if event_type == "push":
        branch = str(payload.get("ref") or "refs/heads/main").split("/")[-1]
        commits = list(payload.get("commits") or [])
        before = payload.get("before")
        head = payload.get("head") or payload.get("after")
        expected_count = max(int(payload.get("size") or 0), int(payload.get("distinct_size") or 0))
        if before and head and (not commits or len(commits) < expected_count):
            status, _, compared = await _get(session, f"/repos/{repo}/compare/{before}...{head}", token, f"compare:{repo}:{before}:{head}")
            if status == 200 and isinstance(compared, dict) and compared.get("commits"):
                commits = compared["commits"]
        if not commits:
            count = expected_count or 1
            return f'<b>📏 On {html.escape(repo)}:{html.escape(branch)} new commits!</b>\nCommits pushed: <b>{count}</b>\n\n<i>Commit details are temporarily unavailable.</i>', f"https://github.com/{repo}/commits/{branch}", "Open commits"
        blocks = []
        for commit in commits:
            sha = str(commit.get("sha") or commit.get("id") or "")
            detail = commit
            if sha:
                status, _, fetched = await _get(session, f"/repos/{repo}/commits/{sha}", token, f"commit:{repo}:{sha}")
                if status == 200 and isinstance(fetched, dict):
                    detail = {**commit, **fetched}
            commit_data = detail.get("commit") or {}
            commit_author = commit_data.get("author") or {}
            author_data = detail.get("author") or {}
            author_name = html.escape(str(commit_author.get("name") or author_data.get("name") or author_data.get("login") or "Unknown"))
            username = author_data.get("login")
            author = f"@{html.escape(str(username))}" if username else f"<i>{author_name}</i>"
            message = html.escape(str(detail.get("message") or commit_data.get("message") or "").split("\n", 1)[0][:500])
            url = detail.get("html_url") or f"https://github.com/{repo}/commit/{sha}"
            files = detail.get("files") or []
            added = [str(x.get("filename")) for x in files if x.get("status") == "added"]
            removed = [str(x.get("filename")) for x in files if x.get("status") == "removed"]
            modified = [str(x.get("filename")) for x in files if x.get("status") not in {"added", "removed"} and x.get("filename")]
            block = f'<blockquote expandable><b>Commit #{html.escape(sha[:7])} by {author_name} ({author})</b>\n<i>{message}</i>\n'
            if added:
                block += f"\n<b>🖊 Created files:</b>\n<code>{html.escape(chr(10).join(added))}</code>\n"
            if removed:
                block += f"\n<b>🗑 Removed files:</b>\n<code>{html.escape(chr(10).join(removed))}</code>\n"
            if modified:
                block += f"\n<b>🖊 Modified files:</b>\n<code>{html.escape(chr(10).join(modified))}</code>\n"
            if files:
                block += f"\n<b>⌨️ Diff:</b>\n➕ {sum(int(x.get('additions') or 0) for x in files)}\n➖ {sum(int(x.get('deletions') or 0) for x in files)}\n"
            blocks.append(block + "</blockquote>")
        compare_url = f"https://github.com/{repo}/compare/{before}...{head}" if before and head else f"https://github.com/{repo}/commits/{branch}"
        return f'<b>📏 On {html.escape(repo)}:{html.escape(branch)} new commits!</b>\n{len(commits)} commits pushed.\n\n' + "\n".join(blocks), compare_url, "Compare changes"
    label = event_label(lang, event_type)
    parts = [f"<b>{html.escape(label)}</b>", f"<code>{html.escape(repo)}</code>", f"{actor} {action}"]
    if title:
        parts.append(f"<i>{title}</i>")
    subject = payload.get("pull_request") or payload.get("issue") or payload.get("release") or payload.get("discussion") or payload.get("comment") or payload.get("review") or payload.get("workflow_run") or payload.get("deployment_status") or payload.get("deployment") or {}
    if not title:
        title = html.escape(str(subject.get("title") or subject.get("name") or subject.get("display_title") or ""))
        if title:
            parts.append(f"<i>{title}</i>")
    body = subject.get("body")
    if body:
        parts.append(f"<blockquote expandable>{html.escape(str(body)[:1500])}</blockquote>")
    if event_type == "pull_request" and action == "synchronize":
        parts.append("<b>New commits pushed to this pull request.</b>")
    if event_type in {"create", "delete"} and payload.get("ref"):
        parts.append(f"Reference: <code>{html.escape(str(payload['ref']))}</code> ({html.escape(str(payload.get('ref_type') or 'ref'))})")
    if event_type == "fork" and payload.get("forkee"):
        parts.append(f"Forked to <code>{html.escape(str((payload.get('forkee') or {}).get('full_name') or 'unknown'))}</code>")
    if event_type == "member" and payload.get("member"):
        parts.append(f"Member: <code>{html.escape(str((payload.get('member') or {}).get('login') or 'unknown'))}</code>")
    if event_type == "public":
        changes = (payload.get("changes") or {}).get("visibility") or {}
        old_visibility = changes.get("from") or "private"
        parts.append(f"Visibility: <code>{html.escape(str(old_visibility))}</code> → <code>public</code>")
    if event_type in {"workflow_run", "workflow_job"}:
        parts.append(f"Workflow: <code>{html.escape(str(subject.get('name') or subject.get('workflow_name') or 'unknown'))}</code>")
        if subject.get("head_branch"):
            parts.append(f"Branch: <code>{html.escape(str(subject['head_branch']))}</code>")
        if subject.get("conclusion") or subject.get("status"):
            parts.append(f"Status: <code>{html.escape(str(subject.get('conclusion') or subject.get('status')))}</code>")
    if event_type == "deployment_status":
        parts.append(f"Environment: <code>{html.escape(str(subject.get('environment') or 'unknown'))}</code>")
        parts.append(f"State: <code>{html.escape(str(subject.get('state') or subject.get('status') or 'unknown'))}</code>")
    url = subject.get("html_url") or f"https://github.com/{repo}"
    label = {
        "pull_request": "Open pull request",
        "issues": "Open issue",
        "release": "Open release",
        "discussion": "Open discussion",
        "issue_comment": "Open comment",
        "pull_request_review": "Open review",
        "pull_request_review_comment": "Open review comment",
        "commit_comment": "Open comment",
        "workflow_run": "Open workflow",
        "deployment_status": "Open deployment",
    }.get(event_type, "Open on GitHub")
    return "\n".join(parts), str(url), label


def _event_key(repo: str, event: dict) -> str:
    payload = event.get("payload") or {}
    event_type = str(event.get("type") or "")
    if event_type == "PushEvent":
        marker = [
            payload.get("ref"),
            payload.get("before"),
            payload.get("head") or payload.get("after") or event.get("id"),
            payload.get("size"),
        ]
    elif event_type in {"IssuesEvent", "IssueCommentEvent", "PullRequestEvent", "PullRequestReviewEvent", "PullRequestReviewCommentEvent"}:
        subject = payload.get("issue") or payload.get("pull_request") or payload.get("comment") or payload.get("review") or {}
        marker = [payload.get("action"), subject.get("id"), subject.get("updated_at"), subject.get("html_url")]
    else:
        marker = [payload.get("action"), payload.get("ref"), payload.get("ref_type"), payload.get("id"), event.get("created_at")]
    raw = json.dumps([repo, event_type, marker], ensure_ascii=True, sort_keys=True, default=str).encode()
    return "event:" + hashlib.sha256(raw).hexdigest()


def _notification_text(item: dict, repo: str, lang: str = "en") -> tuple[str, str, str]:
    subject = item.get("subject") or {}
    kind = html.escape(event_label(lang, str(subject.get("type") or "").lower()))
    title = html.escape(str(subject.get("title") or "GitHub notification"))
    reason = html.escape(str(item.get("reason") or "subscribed"))
    return f'<b>GitHub {kind}</b>\n<code>{html.escape(repo)}</code>\n<i>{title}</i>\nReason: {reason}', f"https://github.com/{repo}", "Open on GitHub"


async def _send(bot: GoyBot, integration: Integration, rendered: tuple[str, str, str]) -> None:
    chat = integration.chat
    if chat is None:
        return
    kwargs = {"message_thread_id": chat.topic_id} if chat.topic_id else {}
    text, url, label = rendered
    try:
        await bot.send_message(chat.chat_id, text, reply_markup=inline_keyboard([[(f"🔗 {label}", "url", url)]]), **kwargs)
    except SilentDrop:
        return


async def _poll_notifications(session: aiohttp.ClientSession, bot: GoyBot, integrations: list[Integration]) -> None:
    by_user: dict[int, list[Integration]] = defaultdict(list)
    for item in integrations:
        if item.user and item.user.token:
            by_user[item.user.id].append(item)
    now = time.time()
    for user_id, items in by_user.items():
        if _next_notifications.get(user_id, 0) > now:
            continue
        token = items[0].user.token
        status, headers, data = await _get(session, "/notifications?all=false&participating=false&per_page=50", token, f"notifications:{user_id}")
        _log.info("notifications fetch user=%s status=%s items=%s", user_id, status, len(data) if isinstance(data, list) else 0)
        try:
            _next_notifications[user_id] = now + max(15, int(headers.get("X-Poll-Interval", "60")))
        except ValueError:
            _next_notifications[user_id] = now + 60
        if status != 200 or not isinstance(data, list):
            continue
        for item in data:
            key = f"notification:{user_id}:{item.get('id')}:{item.get('updated_at')}"
            repo = str((item.get("repository") or {}).get("full_name") or "")
            matches = [x for x in items if x.repository_name == repo]
            if not matches or key in _seen:
                continue
            _seen.add(key)
            if not _primed:
                continue
            for integration in matches:
                if await EventSetting.is_enabled(integration.chat.chat_id, "issues"):
                    await _send(bot, integration, _notification_text(item, repo, await Chat.get_language(integration.chat.chat_id)))


async def _poll_events(session: aiohttp.ClientSession, bot: GoyBot, integrations: list[Integration], config: Config) -> None:
    by_repo: dict[tuple[str, str], list[Integration]] = defaultdict(list)
    for item in integrations:
        token = item.user.token if item.user else None
        if token is None and not config.notifications.none_auth_perm:
            continue
        by_repo[(item.repository_name, token or "")].append(item)
    for (repo, token), items in by_repo.items():
        key = f"events:{repo}:{hash(token)}"
        status, _, data = await _get(session, f"/repos/{repo}/events?per_page=100", token or None, key)
        _log.info("events fetch repo=%s status=%s items=%s", repo, status, len(data) if isinstance(data, list) else 0)
        if status != 200 or not isinstance(data, list):
            continue
        watermark = _event_watermarks.get(key)
        ordered = sorted(data, key=lambda event: (str(event.get("created_at") or ""), str(event.get("id") or "")))
        if watermark is None:
            if ordered:
                newest = ordered[-1]
                _event_watermarks[key] = f"{newest.get('created_at') or ''}:{newest.get('id') or ''}"
            continue
        delivered = 0
        newest_marker = watermark
        for event in ordered:
            marker = f"{event.get('created_at') or ''}:{event.get('id') or ''}"
            if marker <= watermark:
                continue
            event_key = _event_key(repo, event)
            if event_key in _seen:
                continue
            _seen.add(event_key)
            newest_marker = max(newest_marker, marker)
            event_type = _event_names.get(str(event.get("type")))
            if not event_type:
                continue
            event_payload = event.get("payload") or {}
            if event_type == "push" and not event_payload.get("commits") and not event_payload.get("before"):
                continue
            event_head = str(event_payload.get("head") or "")
            if event_type == "push" and event_head and event_head in _delivered_commit_heads:
                continue
            for integration in items:
                if await EventSetting.is_enabled(integration.chat.chat_id, event_type):
                    await _send(bot, integration, await _event_text(session, repo, event, token or None, await Chat.get_language(integration.chat.chat_id)))
            if event_type == "push" and event_head:
                _delivered_commit_heads.add(event_head)
            delivered += 1
            if delivered >= _max_new_events_per_repo:
                break
        _event_watermarks[key] = newest_marker
        _log.info("events processed repo=%s new=%s", repo, delivered)


async def _poll_commits(session: aiohttp.ClientSession, bot: GoyBot, integrations: list[Integration], config: Config) -> None:
    by_repo: dict[tuple[str, str], list[Integration]] = defaultdict(list)
    for item in integrations:
        token = item.user.token if item.user else None
        if token is None and not config.notifications.none_auth_perm:
            continue
        by_repo[(item.repository_name, token or "")].append(item)
    for (repo, token), items in by_repo.items():
        key = f"commits:{repo}:{hash(token)}"
        status, _, commits = await _get(session, f"/repos/{repo}/commits?per_page=20", token or None, key)
        if status != 200 or not isinstance(commits, list) or not commits:
            _log.info("commits fetch repo=%s status=%s items=%s", repo, status, len(commits) if isinstance(commits, list) else 0)
            continue
        latest = str(commits[0].get("sha") or "")
        previous = _commit_watermarks.get(key)
        if previous is None:
            _commit_watermarks[key] = latest
            _log.info("commits baseline repo=%s sha=%s", repo, latest[:7])
            continue
        if latest == previous:
            continue
        if latest in _delivered_commit_heads:
            _commit_watermarks[key] = latest
            continue
        status, _, compared = await _get(session, f"/repos/{repo}/compare/{previous}...{latest}", token or None, f"commit-range:{repo}:{previous}:{latest}")
        new_commits = compared.get("commits") if status == 200 and isinstance(compared, dict) else None
        if not new_commits:
            new_commits = [item for item in commits if str(item.get("sha") or "") != previous]
        if new_commits:
            event = {"type": "PushEvent", "repo": {"name": repo}, "payload": {"ref": "refs/heads/main", "before": previous, "head": latest, "size": len(new_commits), "commits": new_commits}}
            for integration in items:
                if await EventSetting.is_enabled(integration.chat.chat_id, "push"):
                    rendered = await _event_text(session, repo, event, token or None, await Chat.get_language(integration.chat.chat_id))
                    await _send(bot, integration, rendered)
            _delivered_commit_heads.add(latest)
            _log.info("commits processed repo=%s new=%s", repo, len(new_commits))
        _commit_watermarks[key] = latest


async def poll_once(bot: GoyBot, config: Config) -> None:
    integrations = await Integration.all().prefetch_related("chat", "user")
    async with aiohttp.ClientSession() as session:
        await _poll_notifications(session, bot, integrations)
        await _poll_events(session, bot, integrations, config)
        await _poll_commits(session, bot, integrations, config)


def _cleanup() -> None:
    if len(_seen) > 100000:
        keep = list(_seen)[-50000:]
        _seen.clear()
        _seen.update(keep)


async def poll_loop(bot: GoyBot, config: Config) -> None:
    global _primed
    while True:
        try:
            await poll_once(bot, config)
            _primed = True
            _cleanup()
        except asyncio.CancelledError:
            raise
        except Exception:
            import logging
            logging.getLogger("goyifi").exception("GitHub polling cycle failed")
        await asyncio.sleep(max(15, config.notifications.poll_interval))
