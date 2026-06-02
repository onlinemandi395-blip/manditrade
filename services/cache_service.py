from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from services.json_service import JsonService


class CacheService:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self.json_service = JsonService()
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}

    def _make_key(self, namespace: str, key: str, role_scope: str = "") -> str:
        return f"{namespace}::{role_scope}::{key}"

    def get_json(self, path: Path, fallback=None, *, role_scope: str = "", ttl_seconds: int | None = None):
        cache_key = self._make_key("json", str(path), role_scope)
        now = time.time()
        entry = self._cache.get(cache_key)
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        if entry and (now - entry["stored_at"]) <= ttl:
            return entry["value"]
        if not path.exists():
            value = fallback if fallback is not None else {}
        else:
            value = self.json_service.read_json(path, fallback if fallback is not None else {})
        self._cache[cache_key] = {"value": value, "stored_at": now}
        return value

    def get_or_set(self, namespace: str, key: str, builder, *, role_scope: str = "", ttl_seconds: int | None = None):
        cache_key = self._make_key(namespace, key, role_scope)
        now = time.time()
        entry = self._cache.get(cache_key)
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        if entry and (now - entry["stored_at"]) <= ttl:
            return entry["value"]
        value = builder()
        self._cache[cache_key] = {"value": value, "stored_at": now}
        return value

    def invalidate(self, namespace: str = "", key_contains: str = "") -> None:
        keys = list(self._cache.keys())
        for key in keys:
            if namespace and not key.startswith(f"{namespace}::"):
                continue
            if key_contains and key_contains not in key:
                continue
            self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
