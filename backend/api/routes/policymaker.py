"""GET /policymaker/{iso3} — aggregate dashboard view (Module 3 dual interface).

Static crawled signals (WB / ILOSTAT / Wittgenstein) are augmented with a live
**recent_signals** strip via Tavily — current news on the country's youth
labour market, automation rollouts, and training initiatives. Falls back to
an empty list if Tavily is disabled, so the dashboard always renders.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_tavily_client
from config.country_loader import load_country
from crawlers.tavily import TavilyClient
from matching.econometric import CountryDataNotFound, EconometricSignals

router = APIRouter(prefix="/policymaker", tags=["policymaker"])


@router.get("/{iso3}")
async def policymaker_dashboard(
    iso3: str,
    tavily: TavilyClient = Depends(get_tavily_client),
) -> dict:
    iso3 = iso3.upper()

    try:
        econ = EconometricSignals(iso3)
    except CountryDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        country = load_country(iso3)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    summary = econ.policymaker_summary()

    recent_signals: list[dict] = []
    if tavily.is_enabled():
        query = (
            f"{country.name} youth unemployment OR automation OR jobs training 2026 "
            "labour market"
        )
        recent_signals = await tavily.search(query, topic="news", days=180)

    summary["recent_signals"] = recent_signals
    summary["recent_signals_source"] = "tavily" if recent_signals else "static-fallback"
    return summary
