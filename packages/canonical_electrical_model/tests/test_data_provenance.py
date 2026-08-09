"""Tests for DataProvenance and is_customer_sourced."""

from __future__ import annotations

import pytest

from packages.canonical_electrical_model import DataProvenance, is_customer_sourced

# Expected classification for every member: True only for CUSTOMER_* provenances.
_EXPECTED = {
    DataProvenance.SYNTHETIC: False,
    DataProvenance.SIMULATED: False,
    DataProvenance.OPERATOR_ENTERED: False,
    DataProvenance.NAMEPLATE: False,
    DataProvenance.CUSTOMER_HISTORIAN: True,
    DataProvenance.CUSTOMER_METER: True,
    DataProvenance.CUSTOMER_LIMS: True,
    DataProvenance.THIRD_PARTY: False,
}


def test_expected_map_covers_every_member() -> None:
    assert set(_EXPECTED) == set(DataProvenance)


@pytest.mark.parametrize("member, expected", list(_EXPECTED.items()), ids=lambda x: str(x))
def test_is_customer_sourced_is_correct(member: DataProvenance, expected: bool) -> None:
    assert is_customer_sourced(member) is expected


def test_is_customer_sourced_accepts_raw_string_value() -> None:
    assert is_customer_sourced("CUSTOMER_METER") is True
    assert is_customer_sourced("THIRD_PARTY") is False


def test_third_party_is_not_customer_sourced() -> None:
    assert is_customer_sourced(DataProvenance.THIRD_PARTY) is False
