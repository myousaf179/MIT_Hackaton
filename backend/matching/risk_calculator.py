"""LMIC-calibrated AI automation-risk calculator.

Inputs:
- Skills profile (with ISCO-08 codes per skill)
- Country config (digital penetration, automation calibration factors)
- Whether the user is in a rural context

Output: a fully-broken-down risk assessment so the frontend can show
"Why is your risk 38%?" — the brief's core explainability requirement.
"""

from __future__ import annotations

from typing import Any

from config.country_loader import CountryConfig
from crawlers.frey_osborne import lookup_isco_risk, metadata as fo_metadata

DURABLE_THRESHOLD = 0.35


def _classify(risk: float) -> tuple[str, str]:
    """Map a risk score to a band + plain-language explanation."""

    if risk < 0.30:
        return (
            "low",
            "Low automation risk. Your skills are largely durable in the AI era — "
            "build adjacent capabilities to compound your strengths.",
        )
    if risk < 0.60:
        return (
            "medium",
            "Medium automation risk. Some parts of your work could be automated. "
            "Consider building the adjacent skills below to increase resilience.",
        )
    return (
        "high",
        "High automation risk. Focus on the durable skills you already have, and "
        "the adjacent skills below — they are most resistant to automation.",
    )


def calculate_risk(
    *,
    profile: dict[str, Any],
    country: CountryConfig,
    is_rural: bool,
) -> dict[str, Any]:
    """Compute calibrated risk + factor breakdown.

    Formula::

        base_risk          = mean(frey_osborne[isco_code])
        digital_factor     = 1 - itu_digital_penetration * digital_weight
        rurality_factor    = rural_factor if is_rural else urban_factor
        calibrated_risk    = base_risk * digital_factor * rurality_factor
    """

    isco_codes: list[str] = profile.get("isco_codes", [])
    skills: list[dict[str, Any]] = profile.get("skills", [])

    if not isco_codes:
        return {
            "overall_risk": None,
            "band": None,
            "assessment": "No matched skills — unable to compute automation risk.",
            "factors": {},
            "durable_skills": [],
            "vulnerable_skills": [],
            "adjacent_skills_suggested": [],
            "calibration_disclaimer": _disclaimer(),
            "source": fo_metadata(),
        }

    per_skill_base: list[dict[str, Any]] = []
    base_total = 0.0
    for code, skill in zip(isco_codes, skills):
        prob, source_note = lookup_isco_risk(code)
        per_skill_base.append(
            {
                "skill_name": skill.get("name"),
                "isco_code": code,
                "frey_osborne_probability": prob,
                "source_note": source_note,
            }
        )
        base_total += prob
    base_risk = base_total / len(per_skill_base)

    cal = country.automation_calibration
    digital_factor = max(0.0, 1.0 - country.itu_digital_penetration * cal.digital_weight)
    rurality_factor = cal.rural_factor if is_rural else cal.urban_factor

    calibrated = base_risk * digital_factor * rurality_factor
    calibrated = round(min(1.0, max(0.0, calibrated)), 4)
    base_risk = round(base_risk, 4)

    durable_skills: list[str] = []
    vulnerable_skills: list[str] = []
    for entry in per_skill_base:
        skill_calibrated = entry["frey_osborne_probability"] * digital_factor * rurality_factor
        if skill_calibrated < DURABLE_THRESHOLD:
            durable_skills.append(entry["skill_name"])
        else:
            vulnerable_skills.append(entry["skill_name"])

    band, assessment = _classify(calibrated)

    return {
        "overall_risk": calibrated,
        "overall_risk_percentage": round(calibrated * 100, 1),
        "base_risk": base_risk,
        "base_risk_percentage": round(base_risk * 100, 1),
        "band": band,
        "assessment": assessment,
        "factors": {
            "frey_osborne_base": {
                "value": base_risk,
                "explanation": "Average Frey-Osborne probability across the user's matched ISCO codes.",
            },
            "digital_factor": {
                "value": round(digital_factor, 4),
                "explanation": (
                    f"Adjusts for {country.name}'s internet penetration of "
                    f"{country.itu_digital_penetration:.0%} (weight = {cal.digital_weight})."
                ),
            },
            "rurality_factor": {
                "value": rurality_factor,
                "explanation": (
                    "Rural workers face slower automation diffusion than urban workers."
                    if is_rural
                    else "Urban LMIC workers see slightly slower diffusion than the high-income baseline."
                ),
            },
        },
        "per_skill_breakdown": per_skill_base,
        "durable_skills": durable_skills,
        "vulnerable_skills": vulnerable_skills,
        "adjacent_skills_suggested": profile.get("adjacent_skills_pool", [])[:5],
        "calibration_disclaimer": _disclaimer(),
        "source": fo_metadata(),
    }


def _disclaimer() -> str:
    return (
        "Frey-Osborne probabilities are derived from US occupational task profiles; "
        "the LMIC calibration applied here is a transparent heuristic, not a validated "
        "model. Treat figures as directional, not predictive."
    )
