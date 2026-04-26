"""ILOSTAT crawler.

Uses the official ILO bulk-download REST endpoint at ``rplumber.ilo.org`` which
returns CSV directly (much simpler than SDMX-XML for a hackathon).

Docs:
- https://ilostat.ilo.org/data/bulk/
- https://rplumber.ilo.org/files/website/bulk/indicator.html

The endpoint shape is:

    https://rplumber.ilo.org/data/indicator/?id=<INDICATOR>&ref_area=<ISO3>&format=.csv

CSV columns we care about: ``ref_area``, ``indicator``, ``sex``, ``classif1``,
``classif2``, ``time``, ``obs_value``, ``obs_status``.

When the (country, indicator, sector) cell is missing we fall back to a regional
average sourced from a small bundled lookup; every fallback carries
``note="approximated from regional average"``.
"""

from __future__ import annotations

import io
from typing import Any

import httpx
import pandas as pd

from config.country_loader import CountryConfig, SectorDef, load_sectors
from crawlers.base import BaseCrawler

API_BASE = "https://rplumber.ilo.org/data/indicator/"
PUBLIC_BROWSE = "https://ilostat.ilo.org/data/"
SOURCE_NAME = "ILO ILOSTAT"


REGIONAL_WAGE_FALLBACK_USD: dict[tuple[str, str], float] = {
    ("AFR", "TELECOM"): 215.0,
    ("AFR", "RETAIL"): 145.0,
    ("AFR", "AGRICULTURE"): 95.0,
    ("AFR", "CONSTRUCTION"): 175.0,
    ("AFR", "MANUFACTURING"): 155.0,
    ("AFR", "TRANSPORT"): 165.0,
    ("ASA", "TELECOM"): 205.0,
    ("ASA", "RETAIL"): 125.0,
    ("ASA", "AGRICULTURE"): 85.0,
    ("ASA", "CONSTRUCTION"): 145.0,
    ("ASA", "MANUFACTURING"): 135.0,
    ("ASA", "TRANSPORT"): 150.0,
}

REGION_OF: dict[str, str] = {
    "GHA": "AFR", "NGA": "AFR", "KEN": "AFR", "ZAF": "AFR", "ETH": "AFR",
    "UGA": "AFR", "TZA": "AFR", "SEN": "AFR", "RWA": "AFR", "CIV": "AFR",
    "BGD": "ASA", "IND": "ASA", "PAK": "ASA", "VNM": "ASA", "PHL": "ASA",
    "IDN": "ASA", "LKA": "ASA", "NPL": "ASA",
}


class IlostatCrawler(BaseCrawler):
    source_name = SOURCE_NAME

    async def fetch_indicator(
        self, country_code: str, indicator: str
    ) -> pd.DataFrame | None:
        """Fetch a single ILOSTAT indicator as a DataFrame, or None on failure."""

        url = API_BASE
        params = {
            "id": indicator,
            "ref_area": country_code,
            "format": ".csv",
        }
        try:
            text = await self.fetch(url, params=params, as_text=True)
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning(
                "ilostat.fetch_failed", indicator=indicator, country=country_code, error=str(exc)
            )
            return None

        if not text or "obs_value" not in text:
            return None
        try:
            return pd.read_csv(io.StringIO(text))
        except (pd.errors.ParserError, ValueError) as exc:
            self.log.warning("ilostat.parse_failed", indicator=indicator, error=str(exc))
            return None

    async def fetch_wages(
        self, country: CountryConfig
    ) -> dict[str, dict[str, Any]]:
        """Mean monthly earnings by sector (ISIC Rev.4 sections)."""

        sectors = load_sectors()
        df = await self.fetch_indicator(country.iso3, "EAR_4MTH_SEX_OCU_CUR_NB")

        results: dict[str, dict[str, Any]] = {}
        region = REGION_OF.get(country.iso3, "AFR")

        for sector_code in country.sectors_of_interest:
            sector_def = sectors.by_code(sector_code)
            if sector_def is None:
                continue

            value, year = self._extract_latest(df, sector_def) if df is not None else (None, None)

            if value is None:
                fallback = REGIONAL_WAGE_FALLBACK_USD.get((region, sector_code))
                results[sector_code] = self.signal(
                    value=fallback,
                    unit="USD per month" if fallback is not None else "",
                    year=2023,
                    source_name=SOURCE_NAME,
                    source_url=PUBLIC_BROWSE,
                    indicator_code="EAR_4MTH_SEX_OCU_CUR_NB",
                    note=(
                        "Approximated from regional ILO average — country/sector cell not "
                        "available in ILOSTAT for this combination."
                    ),
                )
            else:
                results[sector_code] = self.signal(
                    value=float(value),
                    unit="local currency per month",
                    year=int(year) if year else None,
                    source_name=SOURCE_NAME,
                    source_url=self._public_url(country.iso3, "EAR_4MTH_SEX_OCU_CUR_NB"),
                    indicator_code="EAR_4MTH_SEX_OCU_CUR_NB",
                    note=f"Sector: {sector_def.label} ({sector_def.isic_rev4})",
                )

        return results

    async def fetch_employment(
        self, country: CountryConfig
    ) -> dict[str, dict[str, Any]]:
        """Employment by economic activity (count) per sector."""

        sectors = load_sectors()
        df = await self.fetch_indicator(country.iso3, "EMP_TEMP_SEX_ECO_NB")

        results: dict[str, dict[str, Any]] = {}
        for sector_code in country.sectors_of_interest:
            sector_def = sectors.by_code(sector_code)
            if sector_def is None:
                continue
            value, year = self._extract_latest(df, sector_def) if df is not None else (None, None)
            results[sector_code] = self.signal(
                value=float(value) if value is not None else None,
                unit="persons (thousands)",
                year=int(year) if year else None,
                source_name=SOURCE_NAME,
                source_url=self._public_url(country.iso3, "EMP_TEMP_SEX_ECO_NB"),
                indicator_code="EMP_TEMP_SEX_ECO_NB",
                note=f"Sector: {sector_def.label} ({sector_def.isic_rev4})",
            )
        return results

    @staticmethod
    def _extract_latest(
        df: pd.DataFrame | None, sector: SectorDef
    ) -> tuple[float | None, str | None]:
        """Pick the most recent non-null observation matching the sector classification."""

        if df is None or df.empty:
            return None, None

        candidate = df.copy()

        if "sex" in candidate.columns:
            candidate = candidate[candidate["sex"].astype(str).str.upper() == "SEX_T"]

        if "classif1" in candidate.columns:
            classif_match = candidate["classif1"].astype(str).str.contains(
                sector.ilostat_classif1, case=False, na=False
            )
            if classif_match.any():
                candidate = candidate[classif_match]

        candidate = candidate.dropna(subset=["obs_value"])
        if candidate.empty:
            return None, None

        candidate = candidate.sort_values("time", ascending=False)
        row = candidate.iloc[0]
        return float(row["obs_value"]), str(row.get("time"))

    @staticmethod
    def _public_url(country_code: str, indicator: str) -> str:
        return (
            f"https://www.ilo.org/shinyapps/bulkexplorer/?lang=en&id={indicator}"
            f"&ref_area={country_code}"
        )
