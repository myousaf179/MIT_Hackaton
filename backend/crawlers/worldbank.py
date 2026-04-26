"""World Bank World Development Indicators (WDI) crawler.

Public, no-auth REST endpoint. Returns the most recent non-null observation per
indicator with full provenance.

Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
"""

from __future__ import annotations

from typing import Any

import httpx

from config.country_loader import CountryConfig
from crawlers.base import BaseCrawler

API_BASE = "https://api.worldbank.org/v2"
SOURCE_NAME = "World Bank WDI"

INDICATOR_LABELS: dict[str, dict[str, str]] = {
    "SL.EMP.GROW": {"label": "Employment to population ratio growth", "unit": "%"},
    "SL.UEM.1524.ZS": {"label": "Youth unemployment (15-24)", "unit": "%"},
    "NY.GDP.MKTP.KD.ZG": {"label": "GDP growth", "unit": "%"},
    "IT.NET.USER.ZS": {"label": "Internet users", "unit": "% of population"},
    "SE.SEC.CMPT.LO.ZS": {"label": "Lower-secondary completion rate", "unit": "%"},
    "SL.TLF.TOTL.IN": {"label": "Total labor force", "unit": "people"},
    "SP.RUR.TOTL.ZS": {"label": "Rural population share", "unit": "% of total"},
}


class WorldBankCrawler(BaseCrawler):
    source_name = SOURCE_NAME

    async def fetch_indicator(self, country_code: str, indicator: str) -> dict[str, Any]:
        """Return the most recent non-null observation for one indicator."""

        url = f"{API_BASE}/country/{country_code}/indicator/{indicator}"
        params = {"format": "json", "per_page": "60"}

        try:
            payload = await self.fetch(url, params=params)
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("worldbank.fetch_failed", indicator=indicator, error=str(exc))
            return self.signal(
                value=None,
                unit=INDICATOR_LABELS.get(indicator, {}).get("unit", ""),
                year=None,
                source_name=SOURCE_NAME,
                source_url=self._public_url(country_code, indicator),
                indicator_code=indicator,
                note=f"Fetch failed: {exc.__class__.__name__}",
            )

        latest_value = None
        latest_year: str | None = None
        if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
            for entry in payload[1]:
                if entry.get("value") is not None:
                    latest_value = entry["value"]
                    latest_year = entry.get("date")
                    break

        meta = INDICATOR_LABELS.get(indicator, {"label": indicator, "unit": ""})
        return self.signal(
            value=latest_value,
            unit=meta["unit"],
            year=latest_year,
            source_name=SOURCE_NAME,
            source_url=self._public_url(country_code, indicator),
            indicator_code=indicator,
            note=meta["label"] if latest_value is not None else "No non-null observation in series",
        )

    async def fetch_country(self, country: CountryConfig) -> dict[str, dict[str, Any]]:
        """Fetch every WDI indicator declared in the country YAML."""

        results: dict[str, dict[str, Any]] = {}
        for indicator in country.worldbank_indicators:
            results[indicator] = await self.fetch_indicator(country.iso3, indicator)
        return results

    @staticmethod
    def _public_url(country_code: str, indicator: str) -> str:
        return f"https://data.worldbank.org/indicator/{indicator}?locations={country_code}"
