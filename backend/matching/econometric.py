"""Build the panel of econometric signals shown to the user.

The brief requires "at least two real econometric signals visibly to the user —
not buried in the algorithm." We surface ≥3 signals, each with an explicit
``source_url`` so the frontend can render a link beside the value.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import get_settings
from core.logging import get_logger

log = get_logger(__name__)


class CountryDataNotFound(Exception):
    """Raised when a country has not been crawled yet."""


def _load_bundle(iso3: str) -> dict[str, Any]:
    settings = get_settings()
    path = settings.processed_dir / f"{iso3.lower()}.json"
    if not path.exists():
        raise CountryDataNotFound(
            f"No processed data for {iso3}. Run `python -m scripts.crawl {iso3.upper()}`."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class EconometricSignals:
    """Read-only view over a country bundle, exposing well-formed signals."""

    def __init__(self, iso3: str, *, bundle: dict[str, Any] | None = None) -> None:
        self.iso3 = iso3.upper()
        self.bundle = bundle or _load_bundle(iso3)

    def signals_for_sector(self, sector: str) -> list[dict[str, Any]]:
        """Return ≥3 surfaced signals for the user's primary sector."""

        signals_block = self.bundle.get("econometric_signals", {})
        out: list[dict[str, Any]] = []

        wage = signals_block.get("wage_floors", {}).get(sector)
        if wage:
            out.append({**wage, "signal_type": "wage_floor", "sector": sector})

        wb = signals_block.get("worldbank_indicators", {})
        for code in ("SL.UEM.1524.ZS", "SL.EMP.GROW", "NY.GDP.MKTP.KD.ZG"):
            entry = wb.get(code)
            if entry and entry.get("value") is not None:
                out.append({**entry, "signal_type": code})

        for entry in signals_block.get("education_projections", {}).values():
            if entry and entry.get("value") is not None:
                out.append({**entry, "signal_type": "education_projection"})

        emp = signals_block.get("employment_by_sector", {}).get(sector)
        if emp and emp.get("value") is not None:
            out.append({**emp, "signal_type": "sector_employment", "sector": sector})

        return out

    def trajectory(self) -> dict[str, Any]:
        """Education projection time-series for explainability."""

        edu = self.bundle.get("econometric_signals", {}).get("education_projections", {})
        points: list[dict[str, Any]] = []
        for key, entry in sorted(edu.items()):
            if not isinstance(entry, dict):
                continue
            points.append(
                {
                    "year": entry.get("year"),
                    "value": entry.get("value"),
                    "label": "Adults 15+ with upper-secondary or higher (%)",
                    "source_url": entry.get("source_url"),
                    "note": entry.get("note"),
                }
            )
        return {
            "label": "Wittgenstein Centre SSP2 education projections",
            "source_name": "Wittgenstein Centre",
            "points": points,
        }

    def policymaker_summary(self) -> dict[str, Any]:
        """Aggregate view used by ``GET /policymaker/{iso3}``."""

        signals = self.bundle.get("econometric_signals", {})
        wb = signals.get("worldbank_indicators", {})

        sector_employment = []
        for sector, entry in signals.get("employment_by_sector", {}).items():
            if entry.get("value") is not None:
                sector_employment.append(
                    {
                        "sector": sector,
                        "employment_thousands": entry.get("value"),
                        "year": entry.get("year"),
                        "source_url": entry.get("source_url"),
                    }
                )
        sector_employment.sort(key=lambda r: r.get("employment_thousands") or 0, reverse=True)

        wage_table = []
        for sector, entry in signals.get("wage_floors", {}).items():
            if entry.get("value") is not None:
                wage_table.append(
                    {
                        "sector": sector,
                        "value": entry.get("value"),
                        "unit": entry.get("unit"),
                        "year": entry.get("year"),
                        "source_url": entry.get("source_url"),
                        "note": entry.get("note"),
                    }
                )

        return {
            "country": self.bundle.get("country_name"),
            "iso3": self.bundle.get("country_code"),
            "crawled_at": self.bundle.get("crawled_at"),
            "headline_indicators": {
                "youth_unemployment": wb.get("SL.UEM.1524.ZS"),
                "employment_growth": wb.get("SL.EMP.GROW"),
                "gdp_growth": wb.get("NY.GDP.MKTP.KD.ZG"),
                "internet_penetration": wb.get("IT.NET.USER.ZS"),
                "secondary_completion": wb.get("SE.SEC.CMPT.LO.ZS"),
            },
            "sector_employment": sector_employment,
            "wage_table": wage_table,
            "education_trajectory": self.trajectory(),
            "config": self.bundle.get("config_summary", {}),
        }
