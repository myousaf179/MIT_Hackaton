"""Shared pytest fixtures.

We synthesise a minimal Ghana bundle on disk so the API can be exercised without
network calls. This is the *only* place fake data lives — it exists purely to
keep the test suite hermetic.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# Force Tavily off globally for tests so the suite is hermetic and credit-free.
# Individual tests that exercise the live path use ``monkeypatch.setenv`` to
# re-enable it with a mocked httpx transport.
os.environ["UNMAPPED_TAVILY_API_KEY"] = ""
os.environ["UNMAPPED_ENABLE_TAVILY"] = "false"


def _ensure_test_bundle(iso3: str = "GHA") -> None:
    from config.settings import get_settings  # imported lazily

    settings = get_settings()
    settings.ensure_dirs()
    bundle_path = settings.processed_dir / f"{iso3.lower()}.json"
    if bundle_path.exists():
        return

    bundle = {
        "country_code": iso3,
        "country_name": "Ghana",
        "language_default": "en",
        "currency": "GHS",
        "crawled_at": "2026-04-26T00:00:00Z",
        "config_summary": {
            "iso3": iso3,
            "iso2": "GH",
            "default_rural_share": 0.43,
            "itu_digital_penetration": 0.68,
            "automation_calibration": {
                "urban_factor": 0.85,
                "rural_factor": 0.70,
                "digital_weight": 0.4,
            },
            "sectors_of_interest": ["TELECOM", "RETAIL", "AGRICULTURE", "TECHNOLOGY"],
        },
        "data_sources": {
            "worldbank": {"base_url": "https://data.worldbank.org", "indicators": []},
            "ilostat": {"base_url": "https://ilostat.ilo.org", "sectors": []},
            "wittgenstein": {"base_url": "http://dataexplorer.wittgensteincentre.org/wcde-v2/", "indicators": []},
        },
        "econometric_signals": {
            "wage_floors": {
                "TELECOM": {
                    "value": 215.0,
                    "unit": "USD per month",
                    "year": 2023,
                    "source_name": "ILO ILOSTAT",
                    "source_url": "https://ilostat.ilo.org/data/",
                    "indicator_code": "EAR_4MTH_SEX_OCU_CUR_NB",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture — regional approximation.",
                },
                "RETAIL": {
                    "value": 145.0,
                    "unit": "USD per month",
                    "year": 2023,
                    "source_name": "ILO ILOSTAT",
                    "source_url": "https://ilostat.ilo.org/data/",
                    "indicator_code": "EAR_4MTH_SEX_OCU_CUR_NB",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture.",
                },
                "TECHNOLOGY": {
                    "value": 480.0,
                    "unit": "USD per month",
                    "year": 2023,
                    "source_name": "ILO ILOSTAT",
                    "source_url": "https://ilostat.ilo.org/data/",
                    "indicator_code": "EAR_4MTH_SEX_OCU_CUR_NB",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture.",
                },
            },
            "employment_by_sector": {
                "TELECOM": {
                    "value": 110.0,
                    "unit": "persons (thousands)",
                    "year": 2022,
                    "source_name": "ILO ILOSTAT",
                    "source_url": "https://ilostat.ilo.org/data/",
                    "indicator_code": "EMP_TEMP_SEX_ECO_NB",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture.",
                },
            },
            "worldbank_indicators": {
                "SL.UEM.1524.ZS": {
                    "value": 12.6,
                    "unit": "%",
                    "year": "2023",
                    "source_name": "World Bank WDI",
                    "source_url": "https://data.worldbank.org/indicator/SL.UEM.1524.ZS?locations=GH",
                    "indicator_code": "SL.UEM.1524.ZS",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Youth unemployment.",
                },
                "SL.EMP.GROW": {
                    "value": 1.4,
                    "unit": "%",
                    "year": "2023",
                    "source_name": "World Bank WDI",
                    "source_url": "https://data.worldbank.org/indicator/SL.EMP.GROW?locations=GH",
                    "indicator_code": "SL.EMP.GROW",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Employment growth.",
                },
                "NY.GDP.MKTP.KD.ZG": {
                    "value": 3.1,
                    "unit": "%",
                    "year": "2023",
                    "source_name": "World Bank WDI",
                    "source_url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=GH",
                    "indicator_code": "NY.GDP.MKTP.KD.ZG",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "GDP growth.",
                },
                "IT.NET.USER.ZS": {
                    "value": 68.0,
                    "unit": "%",
                    "year": "2022",
                    "source_name": "World Bank WDI",
                    "source_url": "https://data.worldbank.org/indicator/IT.NET.USER.ZS?locations=GH",
                    "indicator_code": "IT.NET.USER.ZS",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Internet usage.",
                },
                "SE.SEC.CMPT.LO.ZS": {
                    "value": 56.0,
                    "unit": "%",
                    "year": "2022",
                    "source_name": "World Bank WDI",
                    "source_url": "https://data.worldbank.org/indicator/SE.SEC.CMPT.LO.ZS?locations=GH",
                    "indicator_code": "SE.SEC.CMPT.LO.ZS",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Lower-secondary completion.",
                },
            },
            "education_projections": {
                "secondary_completion_2025": {
                    "value": 48.2,
                    "unit": "% of adults 15+",
                    "year": 2025,
                    "source_name": "Wittgenstein Centre",
                    "source_url": "http://dataexplorer.wittgensteincentre.org/wcde-v2/",
                    "indicator_code": "bprop",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture.",
                },
                "secondary_completion_2030": {
                    "value": 52.1,
                    "unit": "% of adults 15+",
                    "year": 2030,
                    "source_name": "Wittgenstein Centre",
                    "source_url": "http://dataexplorer.wittgensteincentre.org/wcde-v2/",
                    "indicator_code": "bprop",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture.",
                },
                "secondary_completion_2035": {
                    "value": 55.8,
                    "unit": "% of adults 15+",
                    "year": 2035,
                    "source_name": "Wittgenstein Centre",
                    "source_url": "http://dataexplorer.wittgensteincentre.org/wcde-v2/",
                    "indicator_code": "bprop",
                    "crawled_at": "2026-04-26T00:00:00Z",
                    "note": "Test fixture.",
                },
            },
        },
        "disclaimer": "Test bundle — values derived from public sources for offline testing.",
    }
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")


@pytest.fixture(scope="session", autouse=True)
def _bundles() -> None:
    _ensure_test_bundle("GHA")
