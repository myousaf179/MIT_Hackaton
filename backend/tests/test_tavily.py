"""Tavily integration tests.

These tests stay hermetic — no real network access. We use ``httpx.MockTransport``
to simulate Tavily's API surface so we can verify:

* The disabled-by-default fallback path (no API key → empty results).
* The live path: query is forwarded, results are normalised, and the
  opportunities builder mixes them into the panel.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from config.country_loader import load_country
from core.cache import FileCache
from crawlers.tavily import TavilyClient
from matching.econometric import EconometricSignals
from matching.opportunities import build_opportunities_async
from matching.skill_matcher import SkillMatcher


def _mock_response(query: str) -> dict[str, Any]:
    return {
        "query": query,
        "results": [
            {
                "title": f"Free training program — {query[:30]}",
                "url": "https://example.org/training/youth-2026",
                "content": "Free 12-week course in mobile repair and digital literacy.",
                "score": 0.92,
                "published_date": "2026-03-01",
            },
            {
                "title": "Local apprenticeship",
                "url": "https://example.org/apprenticeship",
                "content": "Six-month sector apprenticeship with stipend.",
                "score": 0.81,
                "published_date": "2026-02-14",
            },
        ],
    }


def _make_mock_client(captured: list[dict[str, Any]]) -> httpx.AsyncClient:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured.append(body)
        return httpx.Response(200, json=_mock_response(body.get("query", "")))

    transport = httpx.MockTransport(_handler)
    return httpx.AsyncClient(transport=transport, headers={"User-Agent": "test"})


def test_disabled_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNMAPPED_TAVILY_API_KEY", "")
    monkeypatch.setenv("UNMAPPED_ENABLE_TAVILY", "true")
    from config.settings import get_settings

    get_settings.cache_clear()
    client = TavilyClient()
    try:
        assert client.is_enabled() is False
        results = asyncio.run(client.search("anything"))
        assert results == []
    finally:
        asyncio.run(client.aclose())
        get_settings.cache_clear()


def test_search_normalises_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("UNMAPPED_TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("UNMAPPED_ENABLE_TAVILY", "true")
    monkeypatch.setenv("UNMAPPED_DATA_DIR", str(tmp_path))
    from config.settings import get_settings

    get_settings.cache_clear()
    captured: list[dict[str, Any]] = []
    http_client = _make_mock_client(captured)
    cache = FileCache(directory=tmp_path / "raw")

    async def _run() -> list[dict[str, Any]]:
        client = TavilyClient(cache=cache, client=http_client)
        try:
            return await client.search("free repair training Ghana")
        finally:
            await http_client.aclose()

    try:
        results = asyncio.run(_run())
        assert len(results) == 2
        assert results[0]["url"] == "https://example.org/training/youth-2026"
        assert results[0]["source_name"] == "Tavily"
        assert "fetched_at" in results[0]
        assert captured[0]["query"] == "free repair training Ghana"
        assert captured[0]["api_key"] == "test-key"
    finally:
        get_settings.cache_clear()


def test_opportunities_uses_live_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("UNMAPPED_TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("UNMAPPED_ENABLE_TAVILY", "true")
    from config.settings import get_settings

    get_settings.cache_clear()
    captured: list[dict[str, Any]] = []
    http_client = _make_mock_client(captured)
    cache = FileCache(directory=tmp_path / "raw")

    matcher = SkillMatcher()
    matches = matcher.extract("I fix phones and learned a bit of python")
    assert matches, "Expected matches to drive the opportunity queries."

    signals = EconometricSignals("GHA")
    country = load_country("GHA")

    async def _run() -> dict[str, Any]:
        client = TavilyClient(cache=cache, client=http_client)
        try:
            return await build_opportunities_async(
                matches=matches,
                signals=signals,
                country=country,
                tavily=client,
            )
        finally:
            await http_client.aclose()

    try:
        panel = asyncio.run(_run())
        assert panel["live_source"] == "tavily"
        assert panel["live_opportunities"], "Expected at least one live opportunity"
        first = panel["live_opportunities"][0]
        assert first["url"].startswith("https://example.org/")
        assert "matched_for" in first
        assert captured, "Tavily search should have been invoked"
        assert "Ghana" in captured[0]["query"]
    finally:
        get_settings.cache_clear()


def test_opportunities_falls_back_when_disabled() -> None:
    """Without a Tavily key, opportunities should still produce a usable panel."""

    matcher = SkillMatcher()
    matches = matcher.extract("I fix phones")
    signals = EconometricSignals("GHA")
    country = load_country("GHA")

    async def _run() -> dict[str, Any]:
        client = TavilyClient()
        try:
            return await build_opportunities_async(
                matches=matches,
                signals=signals,
                country=country,
                tavily=client,
            )
        finally:
            await client.aclose()

    panel = asyncio.run(_run())
    assert panel["live_source"] == "static-fallback"
    assert panel["live_opportunities"] == []
    assert panel["adjacent_skills"], "Adjacent panel must always be populated"
    assert panel["sector_anchors"], "Sector anchors should still surface"
