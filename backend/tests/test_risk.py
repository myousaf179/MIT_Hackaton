"""Risk math invariants."""

from __future__ import annotations

from config.country_loader import load_country
from matching.risk_calculator import calculate_risk
from matching.skill_matcher import SkillMatcher


def _profile_for(text: str) -> dict:
    matcher = SkillMatcher()
    matches = matcher.extract(text)
    return matcher.build_profile(matches)


def test_calibrated_risk_is_lower_than_base() -> None:
    profile = _profile_for("I sell things at a retail shop")
    country = load_country("GHA")
    risk = calculate_risk(profile=profile, country=country, is_rural=False)

    assert risk["overall_risk"] is not None
    assert risk["base_risk"] is not None
    assert risk["overall_risk"] <= risk["base_risk"], (
        "LMIC calibration must never *increase* risk above the Frey-Osborne baseline."
    )


def test_rural_factor_lowers_risk() -> None:
    profile = _profile_for("I farm crops")
    country = load_country("GHA")
    urban = calculate_risk(profile=profile, country=country, is_rural=False)
    rural = calculate_risk(profile=profile, country=country, is_rural=True)
    assert rural["overall_risk"] <= urban["overall_risk"], (
        "Rural calibration factor must be at most equal to urban factor."
    )


def test_factors_are_explained() -> None:
    profile = _profile_for("I drive a taxi in Accra")
    country = load_country("GHA")
    risk = calculate_risk(profile=profile, country=country, is_rural=False)
    assert {"frey_osborne_base", "digital_factor", "rurality_factor"} <= set(risk["factors"])
    for factor in risk["factors"].values():
        assert factor["explanation"], "Every factor must carry a human-readable explanation."


def test_risk_bounds() -> None:
    profile = _profile_for("I cook at a chop bar and sell food")
    country = load_country("GHA")
    risk = calculate_risk(profile=profile, country=country, is_rural=False)
    assert 0.0 <= risk["overall_risk"] <= 1.0


def test_no_skills_returns_none() -> None:
    profile = {"isco_codes": [], "skills": [], "sectors": [], "adjacent_skills_pool": []}
    country = load_country("GHA")
    risk = calculate_risk(profile=profile, country=country, is_rural=False)
    assert risk["overall_risk"] is None
