# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""GitHub event schemas + Telegram message formatters.

Each event lives in its own module (``push.py``, ``release.py``, …) and
registers itself with the registry on import. Importing this package is
enough to populate the registry — consumers just call ``build_message``.
"""
from GhGoyifier.events import (
    commit_comment as _commit_comment,
)
from GhGoyifier.events import (
    create as _create,
)
from GhGoyifier.events import (
    delete as _delete,
)
from GhGoyifier.events import (
    deployment_status as _deployment_status,
)
from GhGoyifier.events import (
    discussion as _discussion,
)
from GhGoyifier.events import (
    discussion_comment as _discussion_comment,
)
from GhGoyifier.events import (
    fork as _fork,
)
from GhGoyifier.events import (
    issue_comment as _issue_comment,
)
from GhGoyifier.events import (
    issues as _issues,
)
from GhGoyifier.events import (
    member as _member,
)
from GhGoyifier.events import (
    ping as _ping,
)
from GhGoyifier.events import (
    public as _public,
)
from GhGoyifier.events import (
    pull_request as _pull_request,
)
from GhGoyifier.events import (
    pull_request_review as _pull_request_review,
)
from GhGoyifier.events import (
    pull_request_review_comment as _pull_request_review_comment,
)
from GhGoyifier.events import (
    push as _push,
)
from GhGoyifier.events import (
    release as _release,
)
from GhGoyifier.events import (
    star as _star,
)
from GhGoyifier.events import (
    workflow_run as _workflow_run,
)
from GhGoyifier.events._context import EventCtx
from GhGoyifier.events._registry import (
    build_message,
    event_handlers,
    get_subscribed_events,
)

__all__ = [
    "EventCtx",
    "_commit_comment",
    "_create",
    "_delete",
    "_deployment_status",
    "_discussion",
    "_discussion_comment",
    "_fork",
    "_issue_comment",
    "_issues",
    "_member",
    "_ping",
    "_public",
    "_pull_request",
    "_pull_request_review",
    "_pull_request_review_comment",
    "_push",
    "_release",
    "_star",
    "_workflow_run",
    "build_message",
    "event_handlers",
    "get_subscribed_events",
]
