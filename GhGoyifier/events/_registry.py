# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
"""Registry mapping GitHub event names to (schema, formatter).

Each event module calls ``register(name, schema_cls, formatter)`` at import
time; ``app.events.__init__`` imports them all to populate the registry.
"""
import logging
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from GhGoyifier.events._context import EventCtx

T = TypeVar("T", bound=BaseModel)
Formatter = Callable[[T, EventCtx], str | None]
_AnyFormatter = Callable[[BaseModel, EventCtx], str | None]

event_handlers: dict[str, tuple[type[BaseModel], _AnyFormatter]] = {}


def register(
    name: str, schema_cls: type[T], formatter: Formatter[T]
) -> None:
    if name in event_handlers:
        raise RuntimeError(f"Event {name!r} is already registered")




    event_handlers[name] = (schema_cls, formatter)


def get_subscribed_events() -> list[str]:
    """Events the bot subscribes to on the GitHub side. ``ping`` is always
    delivered automatically by GitHub on hook creation, so it's excluded."""
    return sorted(name for name in event_handlers if name != "ping")


def build_message(event: str, payload: dict, ctx: EventCtx) -> str | None:
    """Parse the payload via the registered schema and run the formatter.

    Returns None for unknown events, schema-validation failures, or when
    a formatter chooses to skip the event (e.g. uninteresting action sub-type).
    """
    handler = event_handlers.get(event)
    if handler is None:
        return None
    schema_cls, formatter = handler
    try:
        parsed = schema_cls.model_validate(payload)
    except ValidationError as e:
        logging.warning("Schema validation failed for event %s: %s", event, e)
        return None
    try:
        return formatter(parsed, ctx)
    except Exception:
        logging.exception("Formatter failed for event %s", event)
        return None
