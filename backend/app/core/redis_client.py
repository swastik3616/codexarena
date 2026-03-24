from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Optional

import redis

from app.core.config import settings

_redis_lock = threading.Lock()
_redis_instance: Any | None = None


class _MemoryPubSub:
    def __init__(self, store: "MemoryRedis", ignore_subscribe_messages: bool = True):
        self._store = store
        self._ignore = ignore_subscribe_messages
        self._channels: set[str] = set()

    def subscribe(self, *channels: str) -> None:
        for ch in channels:
            self._channels.add(ch)

    def close(self) -> None:
        return None

    def get_message(self, ignore_subscribe_messages: bool = True, timeout: float = 0.1) -> dict[str, Any] | None:
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            for ch in list(self._channels):
                q = self._store._pubsub_queues.get(ch)
                if q and len(q) > 0:
                    return q.popleft()
            time.sleep(0.005)
        return None


class MemoryRedis:
    """
    In-process Redis stand-in when no server is available (local dev without Docker Redis).
    Not suitable for multi-process production use.
    """

    def __init__(self) -> None:
        self._kv: dict[str, Any] = {}
        self._kv_exp: dict[str, float] = {}
        self._lists: dict[str, list[Any]] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._counters: dict[str, int] = {}
        self._pubsub_queues: dict[str, Deque[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def _cleanup_key(self, key: str) -> None:
        exp = self._kv_exp.get(key)
        if exp is not None and time.time() >= exp:
            self._kv.pop(key, None)
            self._kv_exp.pop(key, None)
            self._counters.pop(key, None)

    def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False, **kwargs: Any) -> bool | None:
        with self._lock:
            self._cleanup_key(key)
            if nx and key in self._kv:
                return False
            self._kv[key] = value
            if ex is not None:
                self._kv_exp[key] = time.time() + float(ex)
            return True

    def get(self, key: str) -> Any:
        with self._lock:
            self._cleanup_key(key)
            return self._kv.get(key)

    def delete(self, *names: str) -> int:
        removed = 0
        with self._lock:
            for key in names:
                self._cleanup_key(key)
                if key in self._kv or key in self._counters:
                    removed += 1
                self._kv.pop(key, None)
                self._kv_exp.pop(key, None)
                self._counters.pop(key, None)
                self._lists.pop(key, None)
                self._zsets.pop(key, None)
        return removed

    def incr(self, key: str) -> int:
        with self._lock:
            self._cleanup_key(key)
            self._counters[key] = self._counters.get(key, 0) + 1
            self._kv[key] = str(self._counters[key])
            return self._counters[key]

    def expire(self, key: str, ex: int) -> bool:
        with self._lock:
            if key not in self._kv and key not in self._counters and key not in self._lists and key not in self._zsets:
                return False
            self._kv_exp[key] = time.time() + float(ex)
            return True

    def rpush(self, key: str, value: Any) -> int:
        with self._lock:
            self._lists.setdefault(key, []).append(value)
            return len(self._lists[key])

    def lrange(self, key: str, start: int, end: int) -> list[Any]:
        with self._lock:
            items = self._lists.get(key, [])
            if end == -1:
                end = len(items) - 1
            if not items:
                return []
            return items[start : end + 1]

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        with self._lock:
            z = self._zsets.setdefault(key, {})
            added = 0
            for member, score in mapping.items():
                if member not in z:
                    added += 1
                z[member] = float(score)
            return added

    def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> list[Any]:
        with self._lock:
            z = self._zsets.get(key, {})
            ordered = sorted(z.items(), key=lambda x: (x[1], x[0]))
            if end == -1:
                slice_items = ordered[start:]
            else:
                slice_items = ordered[start : end + 1]
            if withscores:
                return [(m, s) for m, s in slice_items]
            return [m for m, _ in slice_items]

    def publish(self, channel: str, message: str) -> int:
        with self._lock:
            q = self._pubsub_queues.setdefault(channel, deque())
            q.append({"type": "message", "channel": channel, "data": message})
            return 1

    def pubsub(self, ignore_subscribe_messages: bool = True) -> _MemoryPubSub:
        return _MemoryPubSub(self, ignore_subscribe_messages=ignore_subscribe_messages)

    def ping(self) -> bool:
        return True


def get_redis_client() -> Any:
    """
    Return a shared Redis client, or MemoryRedis if the configured server is unreachable.
    """
    global _redis_instance
    with _redis_lock:
        if _redis_instance is not None:
            return _redis_instance
        try:
            r = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=2.0,
            )
            r.ping()
            _redis_instance = r
        except Exception:
            _redis_instance = MemoryRedis()
        return _redis_instance
