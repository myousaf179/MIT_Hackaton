"""ESCO REST API crawler.

We use ESCO mainly to enrich the local ``skills_taxonomy.json`` with real ESCO
URIs, preferred labels, and alternative labels. The taxonomy is the source of
truth at runtime, but `build_taxonomy` and the optional `enable_esco_fallback`
path can call this crawler.

Docs: https://ec.europa.eu/esco/api/doc/esco_api_doc.html
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from crawlers.base import BaseCrawler

API_BASE = "https://ec.europa.eu/esco/api"
SOURCE_NAME = "ESCO"


class EscoCrawler(BaseCrawler):
    source_name = SOURCE_NAME

    async def search_skill(
        self,
        text: str,
        *,
        language: str = "en",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search ESCO for skills matching free-text input."""

        params = {
            "language": language,
            "type": "skill",
            "text": text,
            "limit": str(limit),
        }
        url = f"{API_BASE}/search?{urlencode(params)}"
        try:
            payload = await self.fetch(url, cache_key=f"esco:search:{language}:{text}:{limit}")
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("esco.search_failed", text=text, error=str(exc))
            return []

        results: list[dict[str, Any]] = []
        embedded = payload.get("_embedded") if isinstance(payload, dict) else None
        if not embedded:
            return results

        for hit in embedded.get("results", [])[:limit]:
            uri = hit.get("uri") or hit.get("_links", {}).get("self", {}).get("href")
            results.append(
                {
                    "esco_uri": uri,
                    "esco_label": hit.get("title") or hit.get("preferredLabel"),
                    "alternative_labels": hit.get("alternativeLabel", []),
                    "description": (hit.get("description") or {}).get("en", {}).get("literal", ""),
                    "language": language,
                    "source_url": uri or API_BASE,
                    "source_name": SOURCE_NAME,
                }
            )
        return results

    async def get_skill_by_uri(self, uri: str, *, language: str = "en") -> dict[str, Any] | None:
        """Fetch a single skill by its ESCO URI."""

        params = {"uris": uri, "language": language}
        url = f"{API_BASE}/resource/skill?{urlencode(params)}"
        try:
            payload = await self.fetch(url, cache_key=f"esco:skill:{language}:{uri}")
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("esco.skill_failed", uri=uri, error=str(exc))
            return None
        return payload if isinstance(payload, dict) else None
