"""Tests for the advisory telemetry plausibility ranges."""

from __future__ import annotations

from packages.electrical_engineering import TelemetryChannel, is_out_of_range
from packages.electrical_engineering.ranges import PLAUSIBILITY_RANGES


def test_every_channel_has_a_range():
    assert set(PLAUSIBILITY_RANGES) == set(TelemetryChannel)


def test_value_inside_range_is_not_flagged():
    assert is_out_of_range(TelemetryChannel.FREQUENCY_HZ, 60.0) is False


def test_value_outside_range_is_flagged():
    assert is_out_of_range(TelemetryChannel.FREQUENCY_HZ, 500.0) is True
    assert is_out_of_range(TelemetryChannel.POWER_FACTOR, 1.5) is True


def test_range_boundaries_are_inclusive():
    pf = PLAUSIBILITY_RANGES[TelemetryChannel.POWER_FACTOR]
    assert is_out_of_range(TelemetryChannel.POWER_FACTOR, pf.low) is False
    assert is_out_of_range(TelemetryChannel.POWER_FACTOR, pf.high) is False


def test_all_ranges_have_low_le_high_and_a_unit():
    for channel, plausibility in PLAUSIBILITY_RANGES.items():
        assert plausibility.low <= plausibility.high, channel
        assert plausibility.unit
