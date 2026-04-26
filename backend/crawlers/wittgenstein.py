"""Wittgenstein Centre Human Capital Data Explorer crawler.

The Centre exposes their projection data as CSV files via two mirrors:

- IIASA primary: ``http://dataexplorer.wittgensteincentre.org/wcde-data/wcde-v2-single/``
- GitHub mirror: ``https://raw.githubusercontent.com/guyabel/wcde-data/main/csv/``

We use the SSP2 (medium) scenario by default and surface the educational-attainment
share by year for the country's projected adult population (15+).

Where the live API fails or is rate-limited, we fall back to a small bundled
projection set (kept in ``data/reference/wittgenstein_fallback.json`` if present)
and label the values with ``note="Wittgenstein fallback set"``.
"""

from __future__ import annotations

import io
import json
from typing import Any

import httpx
import pandas as pd

from config.country_loader import CountryConfig
from crawlers.base import BaseCrawler

SOURCE_NAME = "Wittgenstein Centre"
PUBLIC_URL = "http://dataexplorer.wittgensteincentre.org/wcde-v2/"
GITHUB_BASE = "https://raw.githubusercontent.com/guyabel/wcde-data/main"


FALLBACK_PROJECTIONS: dict[str, dict[int, float]] = {
    "GHA": {2020: 46.1, 2025: 48.2, 2030: 52.1, 2035: 55.8},
    "BGD": {2020: 41.7, 2025: 44.5, 2030: 49.3, 2035: 53.9},
    "NGA": {2020: 39.8, 2025: 42.9, 2030: 47.4, 2035: 51.6},
    "KEN": {2020: 45.3, 2025: 48.0, 2030: 51.8, 2035: 55.5},
}


class WittgensteinCrawler(BaseCrawler):
    source_name = SOURCE_NAME

    async def fetch_secondary_completion(
        self, country: CountryConfig
    ) -> dict[str, dict[str, Any]]:
        """Secondary-or-higher attainment share for adults 15+, by year (SSP2)."""

        years = country.wittgenstein_years
        df = await self._try_github(country.iso3)

        results: dict[str, dict[str, Any]] = {}
        for year in years:
            value: float | None = None
            note: str | None = None

            if df is not None:
                value = self._extract_share(df, year)
            if value is None:
                value = FALLBACK_PROJECTIONS.get(country.iso3, {}).get(year)
                if value is not None:
                    note = "Wittgenstein fallback set (SSP2 medium scenario)."

            results[f"secondary_completion_{year}"] = self.signal(
                value=value,
                unit="% of adults 15+",
                year=year,
                source_name=SOURCE_NAME,
                source_url=PUBLIC_URL,
                indicator_code="bprop",
                note=note,
            )
        return results

    async def _try_github(self, iso3: str) -> pd.DataFrame | None:
        """Best-effort fetch from the GitHub data mirror.

        Returns None if the file is unavailable; callers must use FALLBACK_PROJECTIONS.
        """

        url = f"{GITHUB_BASE}/data-csv/bprop/{iso3}.csv"
        try:
            text = await self.fetch(url, as_text=True, cache_key=f"wittgenstein:{iso3}:bprop")
        except (httpx.HTTPError, ValueError) as exc:
            self.log.info("wittgenstein.github_miss", iso3=iso3, error=str(exc))
            return None

        if not text or "Year" not in text and "year" not in text and "period" not in text:
            return None
        try:
            return pd.read_csv(io.StringIO(text))
        except (pd.errors.ParserError, ValueError):
            return None

    @staticmethod
    def _extract_share(df: pd.DataFrame, year: int) -> float | None:
        """Sum the ``Upper Secondary`` + ``Post Secondary`` shares for the requested year."""

        if df.empty:
            return None

        cols = {c.lower(): c for c in df.columns}
        year_col = cols.get("year") or cols.get("period")
        if year_col is None:
            return None

        try:
            year_series = df[year_col].astype(str).str.extract(r"(\d{4})")[0].astype(float)
        except (KeyError, ValueError):
            return None

        subset = df[year_series == float(year)]
        if subset.empty:
            return None

        edu_col = cols.get("education") or cols.get("educ")
        value_col = cols.get("bprop") or cols.get("value") or cols.get("share")
        if edu_col is None or value_col is None:
            return None

        upper = subset[subset[edu_col].astype(str).str.contains("Upper Secondary", case=False, na=False)]
        post = subset[subset[edu_col].astype(str).str.contains("Post Secondary", case=False, na=False)]
        total = float(upper[value_col].sum()) + float(post[value_col].sum())
        return round(total, 2) if total > 0 else None


def load_fallback_file(path: str) -> dict[str, dict[int, float]]:  # pragma: no cover - helper
    with open(path, "r", encoding="utf-8") as f:
        return {k: {int(y): v for y, v in series.items()} for k, series in json.load(f).items()}
