"""Base crawler with retries, caching, and provenance tracking."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import get_settings
from core.cache import FileCache
from core.logging import get_logger


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BaseCrawler:
    """Async-friendly HTTP crawler with TTL cache and structured logs.

    Subclasses set ``source_name`` and call :meth:`fetch` with a fully-formed URL.
    Every fetch records ``{source_name, url, crawled_at}`` so downstream code can
    cite every value.
    """

    source_name: str = "Generic"

    def __init__(self, *, cache: FileCache | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.settings = get_settings()
        self.log = get_logger(self.__class__.__name__)
        self.cache = cache or FileCache()
        self._owned_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "UNMAPPED-Crawler/1.0 (+hackathon prototype)"},
        )

    async def aclose(self) -> None:
        if self._owned_client:
            await self.client.aclose()

    async def __aenter__(self) -> "BaseCrawler":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def fetch(
        self,
        url: str,
        *,
        cache_key: str | None = None,
        as_text: bool = False,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Fetch a URL with retries + cache. Returns parsed JSON or raw text."""

        key = cache_key or url
        if params:
            key = key + "?" + json.dumps(params, sort_keys=True)
        cached = self.cache.get(key)
        if cached is not None:
            self.log.debug("crawler.cache_hit", url=url, source=self.source_name)
            return cached

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max(1, self.settings.http_max_retries)),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
                reraise=True,
            ):
                with attempt:
                    response = await self.client.get(url, params=params)
                    response.raise_for_status()
                    payload: Any = response.text if as_text else response.json()
        except RetryError as exc:  # pragma: no cover - exercised at runtime
            self.log.warning("crawler.fetch_failed", url=url, error=str(exc))
            raise

        self.cache.set(key, payload, source_url=url)
        self.log.info("crawler.fetched", url=url, source=self.source_name)
        return payload

    @staticmethod
    def signal(
        *,
        value: Any,
        unit: str,
        year: int | str | None,
        source_name: str,
        source_url: str,
        indicator_code: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Standard provenance envelope for any numeric data point."""

        return {
            "value": value,
            "unit": unit,
            "year": year,
            "source_name": source_name,
            "source_url": source_url,
            "indicator_code": indicator_code,
            "crawled_at": utcnow_iso(),
            "note": note,
        }
