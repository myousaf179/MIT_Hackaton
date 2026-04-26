"""Country-agnostic loading: every YAML must load + expose its required fields."""

from __future__ import annotations

import pytest

from config.country_loader import iter_countries, list_country_codes, load_country, load_sectors


def test_at_least_two_countries_configured() -> None:
    codes = list_country_codes()
    assert "GHA" in codes
    assert "BGD" in codes


@pytest.mark.parametrize("iso3", list_country_codes())
def test_each_country_loads(iso3: str) -> None:
    country = load_country(iso3)
    assert country.iso3 == iso3
    assert country.iso2
    assert country.languages
    assert 0.0 <= country.default_rural_share <= 1.0
    assert 0.0 <= country.itu_digital_penetration <= 1.0
    assert country.automation_calibration.urban_factor > 0


def test_iter_countries_yields_all() -> None:
    iterated = [c.iso3 for c in iter_countries()]
    assert sorted(iterated) == sorted(list_country_codes())


def test_sector_catalogue_is_consistent() -> None:
    sectors = load_sectors()
    codes = sectors.codes()
    assert "TELECOM" in codes
    assert "AGRICULTURE" in codes

    for country in iter_countries():
        for sector_code in country.sectors_of_interest:
            assert sectors.by_code(sector_code) is not None, (
                f"{country.iso3} references unknown sector '{sector_code}'."
            )
