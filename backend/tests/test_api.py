"""Smoke tests for the public API surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_lists_countries() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "available_countries" in body
    assert "GHA" in body["available_countries"]


def test_countries_endpoint() -> None:
    response = client.get("/countries")
    assert response.status_code == 200
    countries = response.json()
    iso3_codes = {c["iso3"] for c in countries}
    assert "GHA" in iso3_codes
    assert "BGD" in iso3_codes


def test_skills_search() -> None:
    response = client.get("/skills/search", params={"q": "phone"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "phone"
    assert any(r["isco_code"] == "7421" for r in body["results"])


def test_analyze_amara_demo() -> None:
    payload = {
        "text": "I fix phones and learned a bit of python from YouTube",
        "country_code": "GHA",
        "is_rural": False,
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["country_code"] == "GHA"
    assert body["profile"]["skills"], "Must surface at least one matched skill."
    assert body["risk_assessment"]["overall_risk"] is not None
    assert len(body["econometric_signals"]) >= 3, (
        "Brief requires ≥2 surfaced signals; we surface ≥3 for a stronger demo."
    )
    for signal in body["econometric_signals"]:
        assert signal.get("source_url"), "Every signal must carry a source_url for trust."

    credential = body["portable_credential"]
    assert credential["@context"].startswith("https://w3id.org/openbadges")
    assert credential["credentialSubject"]["country_code"] == "GHA"

    opportunities = body["opportunities"]
    assert "live_opportunities" in opportunities
    assert opportunities["live_source"] in {"tavily", "static-fallback"}


def test_analyze_unknown_country() -> None:
    payload = {"text": "I farm", "country_code": "ZZZ"}
    response = client.post("/analyze", json=payload)
    assert response.status_code == 404


def test_policymaker_endpoint() -> None:
    response = client.get("/policymaker/GHA")
    assert response.status_code == 200
    body = response.json()
    assert body["iso3"] == "GHA"
    assert "headline_indicators" in body
    assert "wage_table" in body
    assert "recent_signals" in body
    assert body["recent_signals_source"] in {"tavily", "static-fallback"}
