"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Pydantic-settings model. All env vars are prefixed `UNMAPPED_`."""

    model_config = SettingsConfigDict(
        env_prefix="UNMAPPED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO")
    cache_ttl_hours: int = Field(default=24, ge=0)
    enable_embeddings: bool = Field(default=False)
    enable_esco_fallback: bool = Field(default=True)
    http_timeout_seconds: float = Field(default=20.0, gt=0)
    http_max_retries: int = Field(default=3, ge=0)
    fuzzy_threshold: int = Field(default=80, ge=0, le=100)

    enable_tavily: bool = Field(default=True)
    tavily_api_key: str = Field(default="")
    tavily_max_results: int = Field(default=5, ge=1, le=20)
    tavily_news_days: int = Field(default=180, ge=1, le=365)

    data_dir: Path = Field(default=REPO_ROOT / "data")
    config_dir: Path = Field(default=REPO_ROOT / "config")

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def reference_dir(self) -> Path:
        return self.data_dir / "reference"

    @property
    def countries_dir(self) -> Path:
        return self.config_dir / "countries"

    @property
    def sources_registry(self) -> Path:
        return self.data_dir / "sources.json"

    @property
    def taxonomy_path(self) -> Path:
        return self.processed_dir / "skills_taxonomy.json"

    def ensure_dirs(self) -> None:
        for path in (self.raw_dir, self.processed_dir, self.reference_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""

    settings = Settings()
    settings.ensure_dirs()
    return settings
