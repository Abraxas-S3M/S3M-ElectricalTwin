"""Tests for the standards-derived numeric constants."""

from __future__ import annotations

import math

from packages.electrical_engineering import constants


def test_sqrt3_value():
    assert math.isclose(constants.SQRT3, math.sqrt(3.0), rel_tol=1e-15)


def test_iec_event_thresholds():
    assert constants.SAG_RESIDUAL_VOLTAGE_LOWER_PU == 0.1
    assert constants.SAG_RESIDUAL_VOLTAGE_UPPER_PU == 0.9
    assert constants.SWELL_VOLTAGE_PU == 1.1
    assert constants.INTERRUPTION_VOLTAGE_PU == 0.1
    # 3 minute short/long interruption boundary expressed in seconds.
    assert constants.INTERRUPTION_SHORT_LONG_BOUNDARY_SECONDS == 180.0


def test_ieee519_voltage_distortion_buckets_are_consistent():
    labels_from_limits = set(constants.VOLTAGE_DISTORTION_THD_LIMIT_PERCENT)
    labels_from_bounds = {label for _, _, label in constants.VOLTAGE_CLASS_BOUNDS_V}
    assert labels_from_limits == labels_from_bounds
    # Higher voltage classes tolerate less distortion (monotonically stricter).
    ordered = [limit for _, _, label in constants.VOLTAGE_CLASS_BOUNDS_V
               for limit in [constants.VOLTAGE_DISTORTION_THD_LIMIT_PERCENT[label]]]
    assert ordered == sorted(ordered, reverse=True)


def test_ieee519_tdd_brackets_are_ascending_and_nonoverlapping():
    brackets = constants.CURRENT_TDD_LIMIT_PERCENT_BY_SCR
    for lower, upper, tdd in brackets:
        assert lower < upper
        assert tdd > 0
    for lower, upper in zip(brackets, brackets[1:], strict=False):
        assert upper[0] == lower[1]  # contiguous, non-overlapping


def test_nema_derating_curve_is_monotonic_non_increasing():
    curve = constants.MOTOR_VOLTAGE_UNBALANCE_DERATING
    unbalances = [u for u, _ in curve]
    deratings = [d for _, d in curve]
    assert unbalances == sorted(unbalances)
    assert deratings == sorted(deratings, reverse=True)
    assert curve[0] == (0.0, 1.00)


def test_c57_91_thermal_constants_are_positive():
    assert constants.TRANSFORMER_TOP_OIL_RISE_OVER_AMBIENT_C > 0
    assert constants.TRANSFORMER_HOT_SPOT_RISE_OVER_TOP_OIL_C > 0
    assert constants.TRANSFORMER_OIL_TIME_CONSTANT_MINUTES > 0
    assert constants.TRANSFORMER_WINDING_TIME_CONSTANT_MINUTES > 0
    assert constants.TRANSFORMER_REFERENCE_HOT_SPOT_TEMPERATURE_C == 110.0
    # Oil is a much slower thermal mass than the winding.
    assert (
        constants.TRANSFORMER_OIL_TIME_CONSTANT_MINUTES
        > constants.TRANSFORMER_WINDING_TIME_CONSTANT_MINUTES
    )


def test_itic_envelopes_are_well_formed_tuples():
    for point in constants.ITIC_UPPER:
        assert len(point) == 2
    for point in constants.ITIC_LOWER:
        assert len(point) == 2
    assert len(constants.ITIC_UPPER) > 0
    assert len(constants.ITIC_LOWER) > 0


def test_itic_upper_is_above_lower_at_steady_state():
    upper_steady = constants.ITIC_UPPER[-1]
    lower_steady = constants.ITIC_LOWER[-1]
    assert math.isinf(upper_steady[0])
    assert math.isinf(lower_steady[0])
    assert upper_steady[1] > lower_steady[1]
