"""Master crawler: build the per-country bundle in ``data/processed/<iso3>.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from config.country_loader import CountryConfig, load_country, load_sectors
from config.settings import get_settings
from core.logging import get_logger
from crawlers.base import utcnow_iso
from crawlers.ilostat import IlostatCrawler
from crawlers.wittgenstein import WittgensteinCrawler
from crawlers.worldbank import WorldBankCrawler

log = get_logger(__name__)


async def crawl_country(iso3: str) -> dict[str, Any]:
    """Crawl every configured source for a country and persist the bundle."""

    settings = get_settings()
    country = load_country(iso3)
    sectors = load_sectors()
    log.info("orchestrator.start", iso3=country.iso3, name=country.name)

    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "UNMAPPED-Crawler/1.0"},
    ) as client:
        worldbank = WorldBankCrawler(client=client)
        ilostat = IlostatCrawler(client=client)
        wittgenstein = WittgensteinCrawler(client=client)

        wb_data = await worldbank.fetch_country(country)
        wages = await ilostat.fetch_wages(country)
        employment = await ilostat.fetch_employment(country)
        education = await wittgenstein.fetch_secondary_completion(country)

    bundle: dict[str, Any] = {
        "country_code": country.iso3,
        "country_name": country.name,
        "language_default": country.languages[0] if country.languages else "en",
        "currency": country.currency,
        "crawled_at": utcnow_iso(),
        "config_summary": {
            "iso3": country.iso3,
            "iso2": country.iso2,
            "default_rural_share": country.default_rural_share,
            "itu_digital_penetration": country.itu_digital_penetration,
            "automation_calibration": country.automation_calibration.model_dump(),
            "sectors_of_interest": country.sectors_of_interest,
            "sector_definitions": [
                sectors.by_code(c).model_dump()
                for c in country.sectors_of_interest
                if sectors.by_code(c) is not None
            ],
        },
        "data_sources": {
            "worldbank": {
                "base_url": "https://data.worldbank.org",
                "indicators": list(wb_data.keys()),
            },
            "ilostat": {
                "base_url": "https://ilostat.ilo.org",
                "sectors": list(wages.keys()),
            },
            "wittgenstein": {
                "base_url": "http://dataexplorer.wittgensteincentre.org/wcde-v2/",
                "indicators": list(education.keys()),
            },
        },
        "econometric_signals": {
            "wage_floors": wages,
            "employment_by_sector": employment,
            "worldbank_indicators": wb_data,
            "education_projections": education,
        },
        "disclaimer": country.disclaimer,
    }

    output = settings.processed_dir / f"{country.iso3.lower()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2, default=str)

    _update_sources_registry(settings.sources_registry, country, bundle)

    log.info("orchestrator.complete", iso3=country.iso3, output=str(output))
    return bundle


def _update_sources_registry(registry_path: Path, country: CountryConfig, bundle: dict[str, Any]) -> None:
    """Append every URL we used to a master sources.json registry."""

    registry: dict[str, Any] = {}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            registry = {}

    urls: set[str] = set()
    for group in bundle["econometric_signals"].values():
        for entry in group.values():
            if isinstance(entry, dict) and entry.get("source_url"):
                urls.add(str(entry["source_url"]))

    registry[country.iso3] = {
        "last_crawled": bundle["crawled_at"],
        "urls": sorted(urls),
    }

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
