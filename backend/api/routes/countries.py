"""GET /countries — list configured countries."""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import CountryListEntry
from config.country_loader import iter_countries
from config.settings import get_settings

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=list[CountryListEntry])
def list_countries() -> list[CountryListEntry]:
    settings = get_settings()
    out: list[CountryListEntry] = []
    for cfg in iter_countries():
        bundle = settings.processed_dir / f"{cfg.iso3.lower()}.json"
        out.append(
            CountryListEntry(
                iso3=cfg.iso3,
                iso2=cfg.iso2,
                name=cfg.name,
                languages=cfg.languages,
                currency=cfg.currency,
                has_processed_data=bundle.exists(),
            )
        )
    return out
