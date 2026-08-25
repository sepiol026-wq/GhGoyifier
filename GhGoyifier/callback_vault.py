# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from GhGoyifier.secret_store import decrypt, encrypt

_prefix = "cb1_"
_ttl_seconds = 86400
_max_entries = 20000


@dataclass
class _Entry:
    encrypted: str
    expires_at: float


_entries: dict[str, _Entry] = {}


def _purge(now: float) -> None:
    expired = [key for key, entry in _entries.items() if entry.expires_at <= now]
    for key in expired:
        _entries.pop(key, None)
    if len(_entries) > _max_entries:
        for key, _ in sorted(_entries.items(), key=lambda item: item[1].expires_at)[: len(_entries) - _max_entries]:
            _entries.pop(key, None)


def protect(value: str) -> str:
    now = time.time()
    _purge(now)
    handle = _prefix + secrets.token_urlsafe(12)
    _entries[handle] = _Entry(encrypt(value), now + _ttl_seconds)
    return handle


def resolve(value: str | None) -> str | None:
    if not value or not value.startswith(_prefix):
        return None
    now = time.time()
    entry = _entries.get(value)
    if entry is None or entry.expires_at <= now:
        _entries.pop(value, None)
        return None
    return decrypt(entry.encrypted)
