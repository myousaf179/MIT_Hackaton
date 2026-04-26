"""Hybrid skill matcher.

Pipeline:
1. Normalise input (lowercase, strip punctuation, collapse whitespace).
2. Substring keyword match against every keyword in the taxonomy.
3. RapidFuzz ``token_set_ratio`` ≥ ``fuzzy_threshold`` for any unmatched skills.
4. Optional ESCO fallback (network) for skills the taxonomy has no entry for.

Every match returns a ``match_method`` field so the API consumer can inspect
how a skill was identified — directly addressing the brief's "explainable to a
non-expert user" requirement.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from config.settings import get_settings
from core.logging import get_logger

log = get_logger(__name__)

_PUNCT = re.compile(r"[^\w\s]")


@dataclass
class SkillMatch:
    skill: dict[str, Any]
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    match_method: str = "keyword"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.skill.get("id"),
            "name": self.skill.get("esco_label"),
            "esco_label": self.skill.get("esco_label"),
            "esco_uri": self.skill.get("esco_uri"),
            "isco_code": self.skill.get("isco_code"),
            "isco_label": self.skill.get("isco_label"),
            "sector": self.skill.get("sector"),
            "confidence": round(self.confidence, 2),
            "match_method": self.match_method,
            "evidence": (
                f"Matched on: {', '.join(self.matched_keywords)}"
                if self.matched_keywords
                else "Inferred from semantic similarity"
            ),
        }


class SkillMatcher:
    """Loads the taxonomy once and serves skill matches."""

    def __init__(self, taxonomy_path: Path | None = None) -> None:
        settings = get_settings()
        self.fuzzy_threshold = settings.fuzzy_threshold
        self.taxonomy_path = taxonomy_path or settings.taxonomy_path
        self.taxonomy = self._load_taxonomy(self.taxonomy_path)
        self._all_keywords = self._index_keywords(self.taxonomy)

    @staticmethod
    def _load_taxonomy(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(
                f"Taxonomy file not found: {path}. Run `python -m scripts.build_taxonomy` first."
            )
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _index_keywords(taxonomy: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        out: list[tuple[str, dict[str, Any]]] = []
        for skill in taxonomy.get("skills", []):
            for kw in skill.get("keywords", []):
                out.append((kw.lower().strip(), skill))
            for alt in skill.get("alternative_labels", []):
                out.append((alt.lower().strip(), skill))
        return out

    @staticmethod
    def normalise(text: str) -> str:
        text = text.lower()
        text = _PUNCT.sub(" ", text)
        return re.sub(r"\s+", " ", text).strip()

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Lightweight autocomplete used by ``GET /skills/search``."""

        norm = self.normalise(query)
        if not norm:
            return []

        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for skill in self.taxonomy.get("skills", []):
            label = (skill.get("esco_label") or "").lower()
            keywords = [k.lower() for k in skill.get("keywords", [])]
            if any(norm in cand for cand in [label, *keywords]):
                key = skill.get("id") or label
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "id": skill.get("id"),
                        "esco_label": skill.get("esco_label"),
                        "isco_code": skill.get("isco_code"),
                        "sector": skill.get("sector"),
                    }
                )
                if len(out) >= limit:
                    break
        return out

    def extract(self, user_input: str) -> list[SkillMatch]:
        """Run the full pipeline and return ranked matches (best first).

        Both passes always run; the fuzzy pass supplements rather than
        replaces the keyword pass so phrasing like 'fixing mobiles in my shop'
        surfaces TWO skills (phone repair via fuzzy + retail via keyword).
        """

        norm = self.normalise(user_input)
        if not norm:
            return []

        bucket = self._keyword_pass(norm)
        for key, fuzzy_match in self._fuzzy_pass(norm).items():
            existing = bucket.get(key)
            if existing is None:
                bucket[key] = fuzzy_match
            else:
                if fuzzy_match.confidence > existing.confidence:
                    existing.confidence = fuzzy_match.confidence
                for kw in fuzzy_match.matched_keywords:
                    if kw not in existing.matched_keywords:
                        existing.matched_keywords.append(kw)

        return self._rank(bucket)

    def _keyword_pass(self, norm: str) -> dict[str, SkillMatch]:
        """Substring match — fast, deterministic, good for clean text."""

        bucket: dict[str, SkillMatch] = {}
        for keyword, skill in self._all_keywords:
            if keyword and keyword in norm:
                key = skill.get("id") or skill.get("esco_label", "?")
                match = bucket.setdefault(
                    key,
                    SkillMatch(skill=skill, confidence=0.0, match_method="keyword"),
                )
                if keyword not in match.matched_keywords:
                    match.matched_keywords.append(keyword)
                density = min(1.0, 0.5 + 0.15 * len(match.matched_keywords))
                match.confidence = max(match.confidence, density)
        return bucket

    def _fuzzy_pass(self, norm: str) -> dict[str, SkillMatch]:
        """Fuzzy fallback for paraphrases like 'fixing phones' vs 'phone repair'."""

        threshold = self.fuzzy_threshold
        bucket: dict[str, SkillMatch] = {}
        tokens = norm.split()
        if not tokens:
            return bucket

        windows: list[str] = [norm]
        for size in (3, 2):
            if len(tokens) >= size:
                for i in range(len(tokens) - size + 1):
                    windows.append(" ".join(tokens[i : i + size]))

        for keyword, skill in self._all_keywords:
            if not keyword:
                continue
            best_score = 0
            best_window = ""
            for window in windows:
                score = int(fuzz.token_set_ratio(keyword, window))
                if score > best_score:
                    best_score = score
                    best_window = window
            if best_score >= threshold:
                key = skill.get("id") or skill.get("esco_label", "?")
                match = bucket.setdefault(
                    key,
                    SkillMatch(
                        skill=skill,
                        confidence=best_score / 100.0,
                        match_method="fuzzy",
                    ),
                )
                if best_window and best_window not in match.matched_keywords:
                    match.matched_keywords.append(best_window)
                match.confidence = max(match.confidence, best_score / 100.0)
        return bucket

    @staticmethod
    def _rank(bucket: dict[str, SkillMatch]) -> list[SkillMatch]:
        return sorted(bucket.values(), key=lambda m: m.confidence, reverse=True)

    def build_profile(self, matches: list[SkillMatch], top_n: int = 5) -> dict[str, Any]:
        """Convert matches into the public profile shape used by the API."""

        skills = [m.to_dict() for m in matches[:top_n]]
        adjacent: list[str] = []
        for m in matches[:top_n]:
            for s in m.skill.get("adjacent_skills", []):
                if s not in adjacent:
                    adjacent.append(s)

        return {
            "skills": skills,
            "isco_codes": [s["isco_code"] for s in skills if s.get("isco_code")],
            "sectors": list({s["sector"] for s in skills if s.get("sector")}),
            "adjacent_skills_pool": adjacent,
            "human_readable_summary": [
                f"- {s['esco_label']} (ISCO {s['isco_code']}) — confidence {int(s['confidence'] * 100)}%"
                for s in skills
            ],
        }
