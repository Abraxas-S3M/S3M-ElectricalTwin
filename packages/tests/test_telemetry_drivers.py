"""Tests for the deterministic physical driver functions."""

from __future__ import annotations

from datetime import datetime

from packages.reference_facility.telemetry import (
    ambient_response,
    ambient_temperature_c,
    clear_sky_irradiance,
    cloud_attenuation,
    occupancy_factor,
    shift_factor,
)

_MONDAY = datetime(2026, 1, 5)  # a weekday
_SATURDAY = datetime(2026, 1, 10)  # a weekend day


def test_shift_factor_within_unit_range():
    for hour in range(24):
        assert 0.0 <= shift_factor(_MONDAY.replace(hour=hour)) <= 1.0


def test_shift_factor_weekend_lower_than_weekday_midshift():
    weekday = shift_factor(_MONDAY.replace(hour=10))
    weekend = shift_factor(_SATURDAY.replace(hour=10))
    assert weekend < weekday


def test_shift_factor_has_midshift_dip():
    peak = shift_factor(_MONDAY.replace(hour=10))
    changeover = shift_factor(_MONDAY.replace(hour=14))
    assert changeover < peak


def test_occupancy_factor_within_unit_range():
    for hour in range(24):
        assert 0.0 <= occupancy_factor(_MONDAY.replace(hour=hour)) <= 1.0


def test_occupancy_peaks_during_working_hours():
    day = occupancy_factor(_MONDAY.replace(hour=10))
    night = occupancy_factor(_MONDAY.replace(hour=3))
    assert day > night


def test_ambient_temperature_peaks_in_afternoon():
    afternoon = ambient_temperature_c(_MONDAY.replace(hour=15))
    predawn = ambient_temperature_c(_MONDAY.replace(hour=3))
    assert afternoon > predawn


def test_ambient_temperature_has_seasonal_variation():
    winter = ambient_temperature_c(datetime(2026, 1, 15, 15))
    summer = ambient_temperature_c(datetime(2026, 7, 15, 15))
    assert summer > winter


def test_ambient_response_zero_when_cool():
    assert ambient_response(18.0) == 0.0
    assert ambient_response(30.0) > 0.0


def test_clear_sky_zero_at_night_positive_midday():
    assert clear_sky_irradiance(_MONDAY.replace(hour=2)) == 0.0
    assert clear_sky_irradiance(_MONDAY.replace(hour=22)) == 0.0
    assert clear_sky_irradiance(_MONDAY.replace(hour=12)) > 0.0


def test_cloud_attenuation_in_range_and_deterministic():
    moment = _MONDAY.replace(hour=12)
    first = cloud_attenuation(moment, seed=42)
    second = cloud_attenuation(moment, seed=42)
    assert first == second
    assert 0.0 <= first <= 1.0


def test_cloud_attenuation_depends_on_seed():
    moment = _MONDAY.replace(hour=12)
    samples = {cloud_attenuation(moment, seed=s) for s in range(20)}
    # Different seeds must not all collapse to a single cloud value.
    assert len(samples) > 1
