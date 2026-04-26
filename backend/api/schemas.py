"""Pydantic v2 request / response models for the public API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., min_length=1, description="Free-text description of the user's skills.")
    country_code: str = Field(..., min_length=3, max_length=3, description="ISO-3166 alpha-3 country code.")
    is_rural: bool = Field(default=False, description="Whether the user lives in a rural context.")
    language: str = Field(default="en", min_length=2, max_length=8, description="ISO-639-1 language tag.")


class Signal(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: Any
    unit: str | None = None
    year: Any = None
    source_name: str | None = None
    source_url: str | None = None
    indicator_code: str | None = None
    crawled_at: str | None = None
    note: str | None = None


class SkillEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    name: str | None = None
    esco_label: str | None = None
    esco_uri: str | None = None
    isco_code: str | None = None
    isco_label: str | None = None
    sector: str | None = None
    confidence: float
    match_method: str
    evidence: str | None = None


class Profile(BaseModel):
    model_config = ConfigDict(extra="allow")

    skills: list[SkillEntry]
    isco_codes: list[str]
    sectors: list[str]
    adjacent_skills_pool: list[str]
    human_readable_summary: list[str]


class FactorBreakdown(BaseModel):
    value: float
    explanation: str


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="allow")

    overall_risk: float | None = None
    overall_risk_percentage: float | None = None
    base_risk: float | None = None
    base_risk_percentage: float | None = None
    band: str | None = None
    assessment: str
    factors: dict[str, FactorBreakdown] = Field(default_factory=dict)
    per_skill_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    durable_skills: list[str] = Field(default_factory=list)
    vulnerable_skills: list[str] = Field(default_factory=list)
    adjacent_skills_suggested: list[str] = Field(default_factory=list)
    calibration_disclaimer: str
    source: dict[str, str]


class TrajectoryPoint(BaseModel):
    year: Any
    value: Any
    label: str | None = None
    source_url: str | None = None
    note: str | None = None


class EducationTrajectory(BaseModel):
    label: str
    source_name: str
    points: list[TrajectoryPoint]


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="allow")


class OpportunityPanel(BaseModel):
    model_config = ConfigDict(extra="allow")

    adjacent_skills: list[dict[str, Any]]
    sector_anchors: list[dict[str, Any]]
    training_pathways: list[dict[str, Any]]
    live_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    live_source: str = Field(default="static-fallback")
    note: str


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    country_code: str
    country_name: str
    language: str
    profile: Profile
    risk_assessment: RiskAssessment
    econometric_signals: list[Signal]
    education_trajectory: EducationTrajectory
    opportunities: OpportunityPanel
    portable_credential: dict[str, Any]
    disclaimer: str | None = None


class CountryListEntry(BaseModel):
    iso3: str
    iso2: str
    name: str
    languages: list[str]
    currency: str
    has_processed_data: bool


class SkillSearchResult(BaseModel):
    id: str | None = None
    esco_label: str | None = None
    isco_code: str | None = None
    sector: str | None = None


class SkillSearchResponse(BaseModel):
    query: str
    results: list[SkillSearchResult]
