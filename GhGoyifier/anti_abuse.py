# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


class SilentDrop(Exception):
    pass


@dataclass
class _Bucket:
    tokens: float
    updated: float


class InboundAdmission:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._seen_updates: dict[str, float] = {}
        self._active: dict[str, int] = {}
        self._leases: dict[int, str] = {}
        self._global = _Bucket(120.0, time.monotonic())


    def _take(self, bucket: _Bucket, capacity: float, refill: float, now: float) -> bool:
        bucket.tokens = min(capacity, bucket.tokens + max(0.0, now - bucket.updated) * refill)
        bucket.updated = now
        if bucket.tokens < 1.0:
            return False
        bucket.tokens -= 1.0
        return True

    def _update_key(self, obj: Any, kind: str) -> str | None:
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            update_id = raw.get("update_id")
            if update_id is not None:
                return f"{kind}:{update_id}"
        return None

    def admit(self, obj: Any, kind: str) -> bool:
        now = time.monotonic()
        update_key = self._update_key(obj, kind)
        if update_key is not None:
            previous = self._seen_updates.get(update_key)
            if previous is not None and now - previous < 300.0:
                return False
            self._seen_updates[update_key] = now
            if len(self._seen_updates) > 10000:
                cutoff = now - 300.0
                self._seen_updates = {key: value for key, value in self._seen_updates.items() if value >= cutoff}
        user_id = getattr(obj, "from_id", None)
        if user_id is None:
            user = getattr(obj, "from_user", None)
            user_id = getattr(user, "id", None)
        chat_id = getattr(obj, "chat_id", None)
        user_key = f"user:{user_id}" if user_id is not None else None
        chat_key = f"chat:{chat_id}" if chat_id is not None else None
        if not self._take(self._global, 120.0, 20.0, now):
            return False
        if user_key is not None:
            bucket = self._buckets.setdefault(user_key, _Bucket(12.0, now))
            capacity, refill = (12.0, 3.0) if kind == "callback" else (8.0, 1.5)
            if not self._take(bucket, capacity, refill, now):
                return False
        if chat_key is not None:
            bucket = self._buckets.setdefault(chat_key, _Bucket(30.0, now))
            if not self._take(bucket, 30.0, 6.0, now):
                return False
        if user_id is not None:
            active_key = f"{kind}:{user_id}"
            if self._active.get(active_key, 0) >= 3:
                return False
            self._active[active_key] = self._active.get(active_key, 0) + 1
            self._leases[id(obj)] = active_key
        return True

    def release(self, obj: Any) -> None:
        active_key = self._leases.pop(id(obj), None)
        if active_key is not None:
            count = self._active.get(active_key, 0)
            if count <= 1:
                self._active.pop(active_key, None)
            else:
                self._active[active_key] = count - 1


class OutboundGuard:
    def __init__(self) -> None:
        self._global = _Bucket(40.0, time.monotonic())
        self._chats: dict[str, _Bucket] = {}
        self.blocked_until = 0.0

    def allow(self, method: str, chat_id: int | str | None) -> bool:
        if method not in {"sendMessage", "sendRichMessage", "editMessageText", "editMessageReplyMarkup", "deleteMessage", "answerCallbackQuery"}:
            return True
        now = time.monotonic()
        if now < self.blocked_until:
            return False
        if not self._take(self._global, 40.0, 12.0, now):
            return False
        if chat_id is not None:
            key = str(chat_id)
            bucket = self._chats.setdefault(key, _Bucket(8.0, now))
            if not self._take(bucket, 8.0, 2.5, now):
                return False
        return True

    @staticmethod
    def _take(bucket: _Bucket, capacity: float, refill: float, now: float) -> bool:
        bucket.tokens = min(capacity, bucket.tokens + max(0.0, now - bucket.updated) * refill)
        bucket.updated = now
        if bucket.tokens < 1.0:
            return False
        bucket.tokens -= 1.0
        return True

    def trip(self, retry_after: int) -> None:
        self.blocked_until = max(self.blocked_until, time.monotonic() + min(max(retry_after, 1), 3600))
