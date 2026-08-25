# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
import ipaddress
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from github import (
    Auth,
    BadCredentialsException,
    Github,
    GithubException,
    UnknownObjectException,
)
from github.Repository import Repository

from GhGoyifier.events import get_subscribed_events


@dataclass
class HookError:
    code: str
    message: str
    detail: str | None = None


def _gh(token: str | None = None) -> Github:
    return Github(auth=Auth.Token(token)) if token else Github()


def _explain(e: GithubException, repo_name: str = "") -> HookError:
    status = getattr(e, "status", None)
    data = e.data if isinstance(e.data, dict) else {}
    api_msg = data.get("message", "")

    if isinstance(e, BadCredentialsException) or status == 401:
        return HookError(
            "auth",
            "Your GitHub token is invalid or expired. Send a new one in DM via /token.",
            api_msg,
        )

    if isinstance(e, UnknownObjectException) or status == 404:
        target = repo_name or "the requested resource"
        return HookError(
            "not_found",
            f"Repository <code>{target}</code> not found, or your token doesn't have "
            "access to it.\n"
            "• Check the spelling: <code>username/repository</code>.\n"
            "• For <b>private</b> repos your token must have the <code>repo</code> scope.",
            api_msg,
        )

    if status == 403:
        return HookError(
            "no_permission",
            "GitHub denied the request. Common reasons:\n"
            "• Your token is missing the <code>admin:repo_hook</code> scope "
            "(required to manage webhooks).\n"
            "• You are <b>not the owner</b> of the repository and don't have "
            "admin/maintain access — only owners or admins can install webhooks.\n"
            "• You hit the GitHub API rate limit. Try again later.",
            api_msg,
        )

    if status == 422 and "already exists" in api_msg.lower():
        return HookError(
            "exists",
            "A webhook with the same URL already exists on this repository.",
            api_msg,
        )

    if status == 422:
        errors = data.get("errors") or []
        details = "; ".join(
            str(item.get("message") or item.get("code") or item)
            for item in errors
            if isinstance(item, dict)
        )
        return HookError(
            "validation",
            "GitHub rejected the webhook settings. "
            + (f"<code>{details}</code>" if details else "Check that the public HTTPS URL is valid."),
            api_msg,
        )

    return HookError(
        "unknown",
        f"GitHub API error ({status}): {api_msg or 'unknown'}",
        str(data),
    )


def _hook_url(host: str, endpoint: str) -> str:
    base = host.strip().rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Webhook host must be a full public http(s) URL, for example https://bot.example.com")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"} or (address and (address.is_private or address.is_loopback)):
        raise ValueError("Webhook host must be publicly reachable by GitHub; localhost/private addresses cannot receive GitHub webhooks")
    return f"{base}/webhook/{quote(endpoint, safe='')}"


def _host_error(error: ValueError) -> HookError:
    return HookError("config", str(error))


def _explain_webhook_access(e: GithubException, repo_name: str) -> HookError:
    status = getattr(e, "status", None)
    data = e.data if isinstance(e.data, dict) else {}
    api_msg = data.get("message", "")
    if status in (401, 403, 404):
        return HookError(
            "no_permission",
            f"Repository <code>{repo_name}</code> is accessible, but GitHub denied webhook management.\n"
            "• Classic PAT: enable <code>admin:repo_hook</code>.\n"
            "• Fine-grained PAT: grant repository <code>Administration: Read and write</code>.\n"
            "• Then replace the saved token with <code>/token</code> and retry.",
            api_msg,
        )
    return _explain(e, repo_name)


def create_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
) -> HookError | None:
    """Create a GitHub webhook for `integration` repo. Returns None on success."""
    try:
        target_url = _hook_url(host, endpoint)
    except ValueError as e:
        return _host_error(e)
    config = {"url": target_url, "content_type": "json", "secret": endpoint}
    events = get_subscribed_events()
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
    except GithubException as e:
        return _explain(e, integration)
    try:
        repo.create_hook("web", config, events, active=True)
        return None
    except GithubException as e:
        return _explain_webhook_access(e, integration)


def update_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
) -> HookError | None:
    """Re-sync the GitHub-side webhook event subscription with the bot's
    current list. If a hook with our URL exists, edit it; otherwise create
    a fresh one. Returns None on success."""
    try:
        target_url = _hook_url(host, endpoint)
    except ValueError as e:
        return _host_error(e)
    config = {"url": target_url, "content_type": "json", "secret": endpoint}
    events = get_subscribed_events()
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
    except GithubException as e:
        return _explain(e, integration)
    try:
        existing = None
        for hook in repo.get_hooks():
            if hook.config.get("url", "") == target_url:
                existing = hook
                break

        if existing is not None:
            existing.edit(name="web", config=config, events=events, active=True)
        else:
            repo.create_hook("web", config, events, active=True)
        return None
    except GithubException as e:
        return _explain_webhook_access(e, integration)


def get_subscribed_events_for(
    gh_token: str, integration: str, host: str, endpoint: str
) -> set[str] | HookError:
    """Return the set of events the GitHub webhook is currently subscribed to,
    or a HookError if we can't reach GitHub / the hook doesn't exist."""
    try:
        target_url = _hook_url(host, endpoint)
    except ValueError as e:
        return _host_error(e)
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
        for hook in repo.get_hooks():
            if hook.config.get("url", "") == target_url:
                return set(hook.events or [])
        return HookError(
            "not_found",
            f"No webhook with our URL was found on <code>{integration}</code>. "
            "Use /reinstall to reinstall it.",
        )
    except GithubException as e:
        return _explain(e, integration)


def validate(token: str) -> bool | HookError:
    """Validate a GitHub PAT. Returns True on success or HookError on failure."""
    if not (token.startswith("ghp_") or token.startswith("github_pat_")):
        return HookError(
            "auth",
            "Token format looks wrong. Use a Personal Access Token that starts "
            "with <code>ghp_</code> (classic) or <code>github_pat_</code> (fine-grained).",
        )
    try:
        g = _gh(token)
        _ = g.get_user().login
        return True
    except GithubException as e:
        return _explain(e)


def check_repo(token: str | None, repo: str) -> Repository | HookError:
    """Return the Repository, or HookError on failure."""
    try:
        g = _gh(token)
        return g.get_repo(repo)
    except GithubException as e:
        return _explain(e, repo)


def get_repos(token: str) -> list | HookError:
    try:
        g = _gh(token)
        return list(g.get_user().get_repos())
    except GithubException as e:
        return _explain(e)
