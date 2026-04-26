"""GET /signals/{iso3}/{sector} — single-sector signal lookup."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import Signal
from matching.econometric import CountryDataNotFound, EconometricSignals

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/{iso3}/{sector}", response_model=list[Signal])
def get_sector_signals(iso3: str, sector: str) -> list[Signal]:
    try:
        econ = EconometricSignals(iso3.upper())
    except CountryDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    signals = econ.signals_for_sector(sector.upper())
    if not signals:
        raise HTTPException(
            status_code=404,
            detail=f"No signals available for {iso3}/{sector}.",
        )
    return [Signal(**s) for s in signals]
