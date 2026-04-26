"""Build a portable, OpenBadges v2 / JSON-LD skill credential.

The credential is the artifact Amara takes with her: cross-border, employer-readable,
and human-explainable. We do NOT cryptographically sign it in this prototype; we
emit a stable JSON-LD shape that downstream verifiers can re-issue with a real key.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any


CONTEXT = "https://w3id.org/openbadges/v2"
ISSUER_NAME = "UNMAPPED Open Skills Infrastructure"
ISSUER_URL = "https://github.com/unmapped/open-skills-infrastructure"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stable_id(profile_payload: dict[str, Any]) -> str:
    """Deterministic ID for the credential so re-running on identical input is idempotent."""

    blob = repr(sorted(profile_payload.items())).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()[:16]
    return f"urn:unmapped:credential:{digest}"


def build_credential(
    *,
    profile: dict[str, Any],
    risk_assessment: dict[str, Any],
    country_code: str,
    language: str,
) -> dict[str, Any]:
    """Return a JSON-LD OpenBadges v2 credential.

    The credential bundles the validated skills, the LMIC-calibrated risk view,
    and an explicit `evidence` block with provenance for every claim.
    """

    skills = profile.get("skills", [])
    isco_codes = profile.get("isco_codes", [])
    sectors = profile.get("sectors", [])

    seed = {
        "country": country_code,
        "language": language,
        "skills": [(s.get("name"), s.get("isco_code"), round(float(s.get("confidence", 0)), 2)) for s in skills],
    }

    credential = {
        "@context": CONTEXT,
        "type": "Assertion",
        "id": _stable_id(seed),
        "issuedOn": _now_iso(),
        "issuer": {
            "type": "Profile",
            "id": ISSUER_URL,
            "name": ISSUER_NAME,
            "url": ISSUER_URL,
        },
        "badge": {
            "type": "BadgeClass",
            "name": "UNMAPPED Skills Profile",
            "description": (
                "Portable, ESCO-grounded skills profile with LMIC-calibrated AI "
                "automation-risk assessment. Human-readable and explainable."
            ),
            "criteria": {
                "narrative": (
                    "Skills extracted from informal experience and matched to ESCO/ISCO. "
                    "Risk calibrated for the worker's country, rurality, and digital context."
                )
            },
        },
        "recipient": {
            "type": "id",
            "hashed": False,
            "identity": f"unmapped-anonymous-{uuid.uuid4().hex[:12]}",
            "salt": "unmapped-prototype",
        },
        "credentialSubject": {
            "country_code": country_code,
            "language": language,
            "skills": [
                {
                    "name": s.get("name"),
                    "esco_label": s.get("esco_label"),
                    "esco_uri": s.get("esco_uri"),
                    "isco_code": s.get("isco_code"),
                    "isco_label": s.get("isco_label"),
                    "sector": s.get("sector"),
                    "confidence": s.get("confidence"),
                    "match_method": s.get("match_method"),
                    "evidence": s.get("evidence"),
                }
                for s in skills
            ],
            "isco_codes": isco_codes,
            "sectors": sectors,
            "automation_risk_assessment": risk_assessment,
        },
        "evidence": [
            {
                "type": "Evidence",
                "id": "https://esco.ec.europa.eu/",
                "name": "ESCO Skills Taxonomy",
                "description": "Skills mapped to the European Skills, Competences, Qualifications and Occupations classification.",
            },
            {
                "type": "Evidence",
                "id": "https://www.ilo.org/public/english/bureau/stat/isco/isco08/",
                "name": "ISCO-08",
                "description": "Occupations classified using the ILO International Standard Classification of Occupations.",
            },
            {
                "type": "Evidence",
                "id": "https://www.oxfordmartin.ox.ac.uk/publications/the-future-of-employment/",
                "name": "Frey & Osborne 2017",
                "description": "Automation probability scores, calibrated for LMIC context.",
            },
        ],
    }

    return credential
