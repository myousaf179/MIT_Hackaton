"""Rebuild / enrich the local skills taxonomy.

Modes:
- ``--validate`` (default): just validates the existing JSON shape.
- ``--expand QUERY...``: queries the live ESCO API for each free-text query and
  appends new skills if no equivalent already exists in the taxonomy.

Examples:
    python -m scripts.build_taxonomy --validate
    python -m scripts.build_taxonomy --expand "data analysis" "graphic design"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from config.settings import get_settings
from core.logging import configure_logging, get_logger
from crawlers.esco import EscoCrawler

log = get_logger("build_taxonomy")


def _load_taxonomy() -> dict[str, Any]:
    settings = get_settings()
    path = settings.taxonomy_path
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_taxonomy(taxonomy: dict[str, Any]) -> None:
    settings = get_settings()
    settings.taxonomy_path.write_text(
        json.dumps(taxonomy, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _validate(taxonomy: dict[str, Any]) -> int:
    skills = taxonomy.get("skills", [])
    if not isinstance(skills, list) or not skills:
        log.error("taxonomy.invalid", reason="skills missing or empty")
        return 1

    required = {"id", "esco_label", "isco_code", "sector", "keywords"}
    missing: list[str] = []
    for entry in skills:
        gaps = required - set(entry)
        if gaps:
            missing.append(f"{entry.get('id', '?')}: missing {sorted(gaps)}")
    if missing:
        for m in missing:
            log.error("taxonomy.missing_field", detail=m)
        return 1

    log.info("taxonomy.valid", skill_count=len(skills))
    return 0


async def _expand(queries: list[str]) -> int:
    taxonomy = _load_taxonomy()
    existing_uris = {s.get("esco_uri") for s in taxonomy.get("skills", [])}
    existing_labels = {(s.get("esco_label") or "").lower() for s in taxonomy.get("skills", [])}
    added = 0

    async with EscoCrawler() as esco:
        for query in queries:
            results = await esco.search_skill(query, limit=3)
            for hit in results:
                uri = hit.get("esco_uri")
                label = (hit.get("esco_label") or "").lower()
                if not uri or uri in existing_uris or label in existing_labels:
                    continue
                taxonomy["skills"].append(
                    {
                        "id": f"skill.{label.replace(' ', '_')[:48]}",
                        "esco_label": hit.get("esco_label"),
                        "esco_uri": uri,
                        "isco_code": "0000",
                        "isco_label": "Mapping pending — please assign manually",
                        "sector": "GENERIC",
                        "keywords": [query, *hit.get("alternative_labels", [])],
                        "alternative_labels": hit.get("alternative_labels", []),
                        "adjacent_skills": [],
                    }
                )
                existing_uris.add(uri)
                existing_labels.add(label)
                added += 1

    _save_taxonomy(taxonomy)
    log.info("taxonomy.expanded", added=added, total=len(taxonomy.get("skills", [])))
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Rebuild or validate the skills taxonomy.")
    parser.add_argument("--validate", action="store_true", help="Validate the existing taxonomy.")
    parser.add_argument(
        "--expand",
        nargs="+",
        metavar="QUERY",
        help="One or more free-text queries to fetch from ESCO and append.",
    )
    args = parser.parse_args(argv)

    if args.expand:
        return asyncio.run(_expand(args.expand))

    taxonomy = _load_taxonomy()
    return _validate(taxonomy)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
