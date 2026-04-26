"""Pre-crawl the demo countries (GHA + BGD) so the API has data on first start.

Usage:
    python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio

from config.country_loader import list_country_codes
from core.logging import configure_logging, get_logger
from crawlers.orchestrator import crawl_country

log = get_logger("seed_demo")


async def _seed() -> None:
    codes = list_country_codes()
    log.info("seed.start", countries=codes)
    for code in codes:
        try:
            await crawl_country(code)
        except Exception as exc:  # pragma: no cover - reported to user
            log.error("seed.country_failed", country=code, error=str(exc))
    log.info("seed.complete")


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    asyncio.run(_seed())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
