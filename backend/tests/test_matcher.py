"""Smoke tests for the hybrid skill matcher on Amara-style phrasings."""

from __future__ import annotations

import pytest

from matching.skill_matcher import SkillMatcher


@pytest.fixture(scope="module")
def matcher() -> SkillMatcher:
    return SkillMatcher()


def test_amara_phrasing_phone_repair(matcher: SkillMatcher) -> None:
    matches = matcher.extract("I have been running a phone repair business since I was 17")
    assert matches, "Phone-repair phrasing must match the seed taxonomy."
    top = matches[0]
    assert top.skill["isco_code"] == "7421"
    assert top.match_method in {"keyword", "fuzzy"}


def test_amara_phrasing_python(matcher: SkillMatcher) -> None:
    matches = matcher.extract("I taught myself basic python coding from YouTube")
    skills = [m.skill["isco_code"] for m in matches]
    assert "2512" in skills, "Python phrasing must surface ISCO 2512 (Software Developers)."


def test_fuzzy_handles_paraphrase(matcher: SkillMatcher) -> None:
    matches = matcher.extract("I'm fixing mobiles in my shop")
    isco_codes = {m.skill["isco_code"] for m in matches}
    assert "7421" in isco_codes, (
        "Fuzzy matching must catch 'fixing mobiles' even though the keyword "
        "is 'mobile repair' / 'phone repair'."
    )


def test_blank_input_returns_empty(matcher: SkillMatcher) -> None:
    assert matcher.extract("   ") == []


def test_search_autocomplete(matcher: SkillMatcher) -> None:
    results = matcher.search("python")
    assert results, "Autocomplete must return at least one result for 'python'."
    assert all("isco_code" in r for r in results)


def test_build_profile_shape(matcher: SkillMatcher) -> None:
    matches = matcher.extract("I sell goods at my stall and keep the books")
    profile = matcher.build_profile(matches)
    assert "skills" in profile and "isco_codes" in profile
    assert profile["sectors"], "Profile must list at least one sector."
    assert all(0.0 <= s["confidence"] <= 1.0 for s in profile["skills"])
