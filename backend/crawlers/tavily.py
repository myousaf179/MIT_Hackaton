"""Tavily Search / Extract client.

Tavily is used for two things only (chosen so the demo stays tight):

1. **Live opportunities** — country + skill specific search for training programs,
   apprenticeships, and reachable jobs surfaced by ``/analyze``.
2. **Policymaker news strip** — recent labour-market news for the
   ``/policymaker/{iso3}`` aggregate dashboard.

If ``UNMAPPED_ENABLE_TAVILY`` is false or ``UNMAPPED_TAVILY_API_KEY`` is empty,
:meth:`TavilyClient.is_enabled` returns False and the rest of the codebase
falls back to the offline static path. The demo always works.

Docs: https://docs.tavily.com/
"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from config.settings import get_settings
from core.cache import FileCache
from core.logging import get_logger
from crawlers.base import utcnow_iso

log = get_logger(__name__)

API_BASE = "https://api.tavily.com"
SOURCE_NAME = "Tavily"


Topic = Literal["general", "news", "finance"]


class TavilyClient:
    """Thin async wrapper around Tavily's `/search` endpoint with caching."""

    def __init__(
        self,
        *,
        cache: FileCache | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = get_settings()
        self.cache = cache or FileCache()
        self._owned_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds,
            headers={"User-Agent": "UNMAPPED-Tavily/1.0"},
        )

    def is_enabled(self) -> bool:
        return bool(self.settings.enable_tavily and self.settings.tavily_api_key)

    async def aclose(self) -> None:
        if self._owned_client:
            await self.client.aclose()

    async def __aenter__(self) -> "TavilyClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def search(
        self,
        query: str,
        *,
        topic: Topic = "general",
        max_results: int | None = None,
        days: int | None = None,
        include_answer: bool = False,
    ) -> list[dict[str, Any]]:
        """Run a Tavily search and return normalised result dicts.

        Each result has the shape::

            {
              "title": "...",
              "url": "https://...",
              "snippet": "...",
              "score": 0.91,
              "published_date": "2026-03-12",
              "source_name": "Tavily",
              "fetched_at": "2026-04-26T..."
            }

        Returns an empty list (no exception) if the client is disabled or the
        request fails — keeps callers simple.
        """

        if not self.is_enabled():
            return []

        max_results = max_results or self.settings.tavily_max_results
        cache_key = f"tavily:{topic}:{days}:{max_results}:{query.strip().lower()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            log.debug("tavily.cache_hit", query=query)
            return cached

        payload: dict[str, Any] = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "topic": topic,
            "max_results": max_results,
            "include_answer": include_answer,
        }
        if topic == "news" and days is not None:
            payload["days"] = days

        try:
            response = await self.client.post(f"{API_BASE}/search", json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("tavily.search_failed", query=query, error=str(exc))
            return []

        results = self._normalise(data)
        self.cache.set(cache_key, results, source_url=f"{API_BASE}/search")
        log.info("tavily.searched", query=query, count=len(results))
        return results

    @staticmethod
    def _normalise(payload: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for hit in (payload.get("results") or [])[:25]:
            url = hit.get("url")
            if not url:
                continue
            out.append(
                {
                    "title": (hit.get("title") or "").strip(),
                    "url": url,
                    "snippet": (hit.get("content") or "").strip()[:500],
                    "score": hit.get("score"),
                    "published_date": hit.get("published_date"),
                    "source_name": SOURCE_NAME,
                    "fetched_at": utcnow_iso(),
                }
            )
        return out
