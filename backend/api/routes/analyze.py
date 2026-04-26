"""POST /analyze — main youth-facing endpoint (Modules 1+2+3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_skill_matcher, get_tavily_client
from api.schemas import AnalyzeRequest, AnalyzeResponse
from config.country_loader import load_country
from core.credential import build_credential
from crawlers.tavily import TavilyClient
from matching.econometric import CountryDataNotFound, EconometricSignals
from matching.opportunities import build_opportunities_async
from matching.risk_calculator import calculate_risk
from matching.skill_matcher import SkillMatcher

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    matcher: SkillMatcher = Depends(get_skill_matcher),
    tavily: TavilyClient = Depends(get_tavily_client),
) -> AnalyzeResponse:
    iso3 = payload.country_code.upper()

    try:
        country = load_country(iso3)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        signals = EconometricSignals(iso3)
    except CountryDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    matches = matcher.extract(payload.text)
    if not matches:
        raise HTTPException(
            status_code=422,
            detail=(
                "No skills recognised. Try describing what you do day-to-day "
                "(e.g. 'I fix phones', 'I sell things at a stall', 'I farm maize')."
            ),
        )

    profile = matcher.build_profile(matches)
    risk = calculate_risk(profile=profile, country=country, is_rural=payload.is_rural)

    primary_sector = next(
        (s for s in profile["sectors"] if s),
        country.sectors_of_interest[0] if country.sectors_of_interest else "RETAIL",
    )
    econ_signals = signals.signals_for_sector(primary_sector)
    trajectory = signals.trajectory()
    opportunities = await build_opportunities_async(
        matches=matches,
        signals=signals,
        country=country,
        tavily=tavily,
    )

    credential = build_credential(
        profile=profile,
        risk_assessment=risk,
        country_code=iso3,
        language=payload.language,
    )

    return AnalyzeResponse(
        country_code=iso3,
        country_name=country.name,
        language=payload.language,
        profile=profile,
        risk_assessment=risk,
        econometric_signals=econ_signals,
        education_trajectory=trajectory,
        opportunities=opportunities,
        portable_credential=credential,
        disclaimer=country.disclaimer or None,
    )
