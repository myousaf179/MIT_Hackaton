"""Simple file-based TTL cache for crawler responses.

Keys are arbitrary strings (e.g. a normalised URL); values are JSON-serialisable
dicts. Cache files live under `data/raw/<sha256>.json` so they survive process
restarts but are easy to inspect / clear.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.settings import get_settings
from core.logging import get_logger

log = get_logger(__name__)


@dataclass
class CacheEntry:
    key: str
    value: Any
    stored_at: float
    source_url: str | None = None


class FileCache:
    """Minimal TTL cache with file persistence."""

    def __init__(self, ttl_seconds: int | None = None, directory: Path | None = None) -> None:
        settings = get_settings()
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_hours * 3600
        self.directory = directory or settings.raw_dir
        self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]

    def _path(self, key: str) -> Path:
        return self.directory / f"{self._hash(key)}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("cache.read_failed", key=key, error=str(exc))
            return None

        stored_at = float(payload.get("_cache_stored_at", 0))
        if self.ttl_seconds > 0 and (time.time() - stored_at) > self.ttl_seconds:
            log.debug("cache.expired", key=key, age=time.time() - stored_at)
            return None
        return payload.get("value")

    def set(self, key: str, value: Any, source_url: str | None = None) -> None:
        path = self._path(key)
        payload = {
            "_cache_stored_at": time.time(),
            "_cache_key": key,
            "_source_url": source_url,
            "value": value,
        }
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        except OSError as exc:
            log.warning("cache.write_failed", key=key, error=str(exc))

    def clear(self) -> None:
        for path in self.directory.glob("*.json"):
            path.unlink(missing_ok=True)
