"""Reachable-opportunity surfacing.

This is Module 3's user-facing output: not aspirational matching, but **honest,
grounded** matching anchored to the user's matched skills and the country's
sector wage table.

We compose three opportunity types:

1. **Adjacent skill paths** — concrete capabilities the user could add to lift
   resilience. Drawn from each matched skill's ``adjacent_skills`` list.
2. **Sector wage anchors** — for the user's top sectors, the actual ILO wage
   floor with the source link.
3. **Training pathway hints** — durable-skill-aligned next steps. When Tavily
   is configured these are **live, country-specific** results from a web
   search; otherwise we fall back to a small curated dictionary so the demo
   keeps working offline.
"""

from __future__ import annotations

from typing import Any

from config.country_loader import CountryConfig
from core.logging import get_logger
from crawlers.tavily import TavilyClient
from matching.econometric import EconometricSignals
from matching.skill_matcher import SkillMatch

log = get_logger(__name__)


_TRAINING_HINTS: dict[str, list[str]] = {
    "TECHNOLOGY": [
        "Free Code Camp — Responsive Web Design (https://www.freecodecamp.org/learn)",
        "MIT OpenCourseWare — Introduction to Computer Science",
        "Andela Learning Community / ALX Africa cohort programs",
    ],
    "TELECOM": [
        "ITU Academy free courses on mobile network basics (https://academy.itu.int/)",
        "Local TVET diploma in Electronics Repair",
    ],
    "RETAIL": [
        "ILO 'Start and Improve Your Business' (SIYB) curriculum",
        "Mobile-money agent certification (where available locally)",
    ],
    "AGRICULTURE": [
        "FAO e-learning Academy on Climate-Smart Agriculture",
        "AGRA / national extension service short courses",
    ],
    "MANUFACTURING": [
        "Better Work programme (ILO) modules on factory skills",
        "Local TVET diploma in machine operation / quality control",
    ],
    "TRANSPORT": [
        "Defensive driving certification",
        "Logistics & last-mile micro-credential (Coursera financial-aid tier)",
    ],
    "EDUCATION": [
        "TeachUNITED / national teacher-training short courses",
        "Open University free education modules",
    ],
    "HEALTH": [
        "WHO OpenWHO free courses (https://openwho.org/)",
        "National community health worker (CHW) curriculum",
    ],
    "CONSTRUCTION": [
        "ILO Skills for Trade and Economic Diversification (STED)",
        "Site-safety and scaffold certification through local TVET",
    ],
}


def _build_static_pathways(sectors: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for sector in sectors:
        for hint in _TRAINING_HINTS.get(sector, []):
            out.append({"sector": sector, "pathway": hint, "source": "static-fallback"})
    return out


def _adjacent_panel(matches: list[SkillMatch]) -> list[dict[str, str]]:
    adjacent: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in matches:
        for skill_label in match.skill.get("adjacent_skills", []):
            if skill_label in seen:
                continue
            seen.add(skill_label)
            adjacent.append(
                {
                    "label": skill_label,
                    "anchor_skill": match.skill.get("esco_label", ""),
                    "rationale": (
                        f"Direct adjacency to '{match.skill.get('esco_label')}' — "
                        "builds on what you already do."
                    ),
                }
            )
        if len(adjacent) >= 8:
            break
    return adjacent


def _sector_anchors(sectors: list[str], signals: EconometricSignals) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for sector in sectors[:3]:
        sector_signals = signals.signals_for_sector(sector)
        wage = next((s for s in sector_signals if s.get("signal_type") == "wage_floor"), None)
        emp = next(
            (s for s in sector_signals if s.get("signal_type") == "sector_employment"),
            None,
        )
        anchors.append({"sector": sector, "wage_floor": wage, "sector_employment": emp})
    return anchors


def _ordered_sectors(matches: list[SkillMatch]) -> list[str]:
    sectors: list[str] = []
    for match in matches:
        sector = match.skill.get("sector")
        if sector and sector not in sectors:
            sectors.append(sector)
    return sectors


def _empty_panel() -> dict[str, Any]:
    return {
        "adjacent_skills": [],
        "sector_anchors": [],
        "training_pathways": [],
        "live_opportunities": [],
        "live_source": "none",
        "note": "Add more detail about your skills to see reachable opportunities.",
    }


def build_opportunities(
    *,
    matches: list[SkillMatch],
    signals: EconometricSignals,
) -> dict[str, Any]:
    """Synchronous builder — used when Tavily is disabled or unavailable."""

    if not matches:
        return _empty_panel()

    sectors = _ordered_sectors(matches)
    return {
        "adjacent_skills": _adjacent_panel(matches),
        "sector_anchors": _sector_anchors(sectors, signals),
        "training_pathways": _build_static_pathways(sectors[:3]),
        "live_opportunities": [],
        "live_source": "static-fallback",
        "note": (
            "These are grounded, reachable opportunities — adjacent to skills you already have. "
            "They are not aspirational suggestions disconnected from local realities."
        ),
    }


async def build_opportunities_async(
    *,
    matches: list[SkillMatch],
    signals: EconometricSignals,
    country: CountryConfig,
    tavily: TavilyClient | None = None,
) -> dict[str, Any]:
    """Async builder that surfaces live, country-specific opportunities via Tavily.

    Always returns a valid panel:
    - Tavily disabled / no key → static fallback path (offline-safe).
    - Tavily enabled → live results merged with the adjacent + anchor panels.
    """

    if not matches:
        return _empty_panel()

    sectors = _ordered_sectors(matches)
    adjacent = _adjacent_panel(matches)
    anchors = _sector_anchors(sectors, signals)
    static_pathways = _build_static_pathways(sectors[:3])

    if tavily is None or not tavily.is_enabled():
        return {
            "adjacent_skills": adjacent,
            "sector_anchors": anchors,
            "training_pathways": static_pathways,
            "live_opportunities": [],
            "live_source": "static-fallback",
            "note": (
                "These are grounded, reachable opportunities — adjacent to skills you "
                "already have. Live web-sourced opportunities are disabled "
                "(set UNMAPPED_TAVILY_API_KEY to enable)."
            ),
        }

    live: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    queries = _opportunity_queries(matches, country)

    for query in queries[:4]:
        results = await tavily.search(query["q"], topic="general")
        for hit in results:
            url = hit.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            live.append(
                {
                    **hit,
                    "matched_for": {
                        "sector": query["sector"],
                        "skill": query["skill"],
                        "query": query["q"],
                    },
                }
            )
        if len(live) >= 8:
            break

    return {
        "adjacent_skills": adjacent,
        "sector_anchors": anchors,
        "training_pathways": static_pathways,
        "live_opportunities": live[:8],
        "live_source": "tavily" if live else "static-fallback",
        "note": (
            "These are grounded, reachable opportunities. 'Live opportunities' are "
            "current web results retrieved via Tavily for your country and skills."
        ),
    }


def _opportunity_queries(
    matches: list[SkillMatch], country: CountryConfig
) -> list[dict[str, str]]:
    """Compose targeted opportunity queries for the user's top skills/sectors."""

    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    location = country.name

    for match in matches:
        sector = match.skill.get("sector") or "GENERIC"
        skill_label = match.skill.get("esco_label") or ""
        key = (sector, skill_label)
        if key in seen or not skill_label:
            continue
        seen.add(key)
        out.append(
            {
                "sector": sector,
                "skill": skill_label,
                "q": (
                    f"free or low-cost training program {skill_label} {location} 2026 "
                    f"OR youth apprenticeship {sector.lower()} {location}"
                ),
            }
        )

    if not out:
        out.append(
            {
                "sector": "GENERIC",
                "skill": "general",
                "q": f"youth employment training program {location} 2026",
            }
        )
    return out
