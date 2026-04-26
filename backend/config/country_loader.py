"""Load and validate country / sector YAML configuration files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .settings import get_settings


class AutomationCalibration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    urban_factor: float = Field(ge=0.0, le=2.0)
    rural_factor: float = Field(ge=0.0, le=2.0)
    digital_weight: float = Field(ge=0.0, le=1.0, default=0.4)


class CountryConfig(BaseModel):
    """Validated representation of `config/countries/<ISO3>.yaml`."""

    model_config = ConfigDict(extra="ignore")

    iso3: str
    iso2: str
    name: str
    display_name_local: str = ""

    languages: list[str] = Field(default_factory=lambda: ["en"])
    currency: str = "USD"

    default_rural_share: float = Field(ge=0.0, le=1.0, default=0.5)
    itu_digital_penetration: float = Field(ge=0.0, le=1.0, default=0.5)

    automation_calibration: AutomationCalibration = Field(
        default_factory=lambda: AutomationCalibration(urban_factor=0.85, rural_factor=0.70)
    )

    sectors_of_interest: list[str] = Field(default_factory=list)
    ilostat_indicators: list[str] = Field(default_factory=list)
    worldbank_indicators: list[str] = Field(default_factory=list)
    wittgenstein_years: list[int] = Field(default_factory=lambda: [2025, 2030, 2035])

    disclaimer: str = ""


class SectorDef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    label: str
    isic_rev4: str
    ilostat_classif1: str
    related_isco_codes: list[str] = Field(default_factory=list)


class SectorCatalogue(BaseModel):
    sectors: list[SectorDef]

    def by_code(self, code: str) -> SectorDef | None:
        return next((s for s in self.sectors if s.code == code), None)

    def codes(self) -> list[str]:
        return [s.code for s in self.sectors]


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_country(iso3: str) -> CountryConfig:
    """Load a single country YAML by ISO3 code (case-insensitive)."""

    settings = get_settings()
    iso3 = iso3.upper()
    path = settings.countries_dir / f"{iso3}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No country config at {path}. "
            f"Copy `config/countries/_template.yaml` to `{iso3}.yaml` to add it."
        )
    return CountryConfig.model_validate(_load_yaml(path))


def list_country_codes() -> list[str]:
    """All configured country ISO3 codes (excluding the template)."""

    settings = get_settings()
    codes: list[str] = []
    for path in sorted(settings.countries_dir.glob("*.yaml")):
        if path.stem.startswith("_"):
            continue
        codes.append(path.stem.upper())
    return codes


def iter_countries() -> Iterable[CountryConfig]:
    for code in list_country_codes():
        yield load_country(code)


@lru_cache
def load_sectors() -> SectorCatalogue:
    settings = get_settings()
    path = settings.config_dir / "sectors.yaml"
    return SectorCatalogue.model_validate(_load_yaml(path))
