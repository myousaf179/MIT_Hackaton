"""Per-country crawler CLI.

Usage:
    python -m scripts.crawl GHA
    python -m scripts.crawl GHA BGD
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from config.country_loader import list_country_codes
from core.logging import configure_logging, get_logger
from crawlers.orchestrator import crawl_country

log = get_logger("crawl")


async def _run(codes: list[str]) -> None:
    for code in codes:
        log.info("crawl.start", country=code)
        try:
            await crawl_country(code)
            log.info("crawl.done", country=code)
        except Exception as exc:  # pragma: no cover - reported to user
            log.error("crawl.failed", country=code, error=str(exc))


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Crawl real data for one or more countries.")
    parser.add_argument(
        "countries",
        nargs="*",
        help="ISO-3 codes (e.g. GHA BGD). Defaults to every configured country.",
    )
    args = parser.parse_args(argv)

    codes = [c.upper() for c in args.countries] or list_country_codes()
    if not codes:
        print("No countries configured. Add a YAML to config/countries/.", file=sys.stderr)
        return 1

    asyncio.run(_run(codes))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
