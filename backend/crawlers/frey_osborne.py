"""Frey & Osborne automation-probability loader.

Loads the bundled CSV (occupation × probability) and provides lookups by
ISCO-08 4-digit code via a SOC→ISCO crosswalk.

Citation:
    Frey, C. B., & Osborne, M. A. (2017). The future of employment: How susceptible are jobs to computerisation?
    Technological Forecasting and Social Change, 114, 254-280.
    https://doi.org/10.1016/j.techfore.2016.08.019
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from config.settings import get_settings
from core.logging import get_logger

log = get_logger(__name__)

SOURCE_NAME = "Frey & Osborne (2017)"
SOURCE_URL = "https://www.oxfordmartin.ox.ac.uk/publications/the-future-of-employment/"


@lru_cache
def load_frey_osborne() -> dict[str, dict[str, str | float]]:
    """Return ``{soc_code: {label, probability}}`` from the bundled CSV.

    The CSV columns are: ``soc_code,label,probability``.
    """

    settings = get_settings()
    path = settings.reference_dir / "frey_osborne_2017.csv"
    if not path.exists():
        log.warning("frey_osborne.csv_missing", path=str(path))
        return {}

    out: dict[str, dict[str, str | float]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            soc = (row.get("soc_code") or "").strip()
            if not soc:
                continue
            try:
                prob = float(row.get("probability") or 0)
            except ValueError:
                continue
            out[soc] = {
                "label": (row.get("label") or "").strip(),
                "probability": prob,
            }
    return out


@lru_cache
def load_soc_to_isco() -> dict[str, str]:
    """Return ``{soc_code: isco08_code}`` crosswalk from the bundled CSV."""

    settings = get_settings()
    path = settings.reference_dir / "soc_to_isco08.csv"
    if not path.exists():
        log.warning("soc_to_isco.csv_missing", path=str(path))
        return {}

    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            soc = (row.get("soc_code") or "").strip()
            isco = (row.get("isco08_code") or "").strip()
            if soc and isco:
                out[soc] = isco
    return out


@lru_cache
def isco_to_probability() -> dict[str, float]:
    """Aggregate Frey-Osborne probability by ISCO-08 code (mean of mapped SOCs)."""

    fo = load_frey_osborne()
    crosswalk = load_soc_to_isco()
    if not fo or not crosswalk:
        return {}

    bucket: dict[str, list[float]] = {}
    for soc, isco in crosswalk.items():
        prob = fo.get(soc, {}).get("probability")
        if isinstance(prob, (int, float)):
            bucket.setdefault(isco, []).append(float(prob))

    return {isco: round(sum(probs) / len(probs), 4) for isco, probs in bucket.items() if probs}


def lookup_isco_risk(isco_code: str, *, default: float = 0.5) -> tuple[float, str]:
    """Return (probability, source_note) for the given ISCO-08 code."""

    table = isco_to_probability()
    if isco_code in table:
        return table[isco_code], f"Frey-Osborne mean over SOCs mapping to ISCO {isco_code}"

    parent = isco_code[:3]
    if parent and parent in table:
        return table[parent], f"Frey-Osborne mean over ISCO 3-digit parent {parent}"

    return default, "No Frey-Osborne mapping; defaulted to 0.5 (uncertain)"


def metadata() -> dict[str, str]:
    return {"source_name": SOURCE_NAME, "source_url": SOURCE_URL}
