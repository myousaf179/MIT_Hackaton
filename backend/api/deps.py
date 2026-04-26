"""FastAPI dependency providers (singletons created on app startup)."""

from __future__ import annotations

from functools import lru_cache

from crawlers.tavily import TavilyClient
from matching.skill_matcher import SkillMatcher

_tavily_singleton: TavilyClient | None = None


@lru_cache
def get_skill_matcher() -> SkillMatcher:
    """Cached matcher — taxonomy is loaded once per process."""

    return SkillMatcher()


def get_tavily_client() -> TavilyClient:
    """Process-wide Tavily client.

    Reused across requests so the underlying httpx.AsyncClient pools connections.
    Closed in the FastAPI lifespan shutdown handler.
    """

    global _tavily_singleton
    if _tavily_singleton is None:
        _tavily_singleton = TavilyClient()
    return _tavily_singleton


async def close_tavily_client() -> None:
    global _tavily_singleton
    if _tavily_singleton is not None:
        await _tavily_singleton.aclose()
        _tavily_singleton = None
