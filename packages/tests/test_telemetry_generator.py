"""Tests for the driver-based deterministic telemetry generator.

These exercise the WP3-style cross-channel consistency properties (S/P/Q/PF,
energy monotonicity, parent-child power balance), byte-for-byte determinism,
emergent power factor from capacitor stepping, and stable STALE/MISSING
proportions.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from functools import cache

import pytest

from packages.canonical_electrical_model import DataProvenance, PhaseTag, Quality
from packages.reference_facility import reference_facility
from packages.reference_facility.channels import Channel
from packages.reference_facility.telemetry import TelemetryReading, generate

_SQRT3 = math.sqrt(3.0)

# A weekday daytime window (Monday) when motors are running.
_START = datetime(2026, 1, 5, 8, 0, 0)
_END = datetime(2026, 1, 5, 11, 0, 0)

# A full day for energy/thermal/PV trend tests.
_DAY_START = datetime(2026, 1, 5, 0, 0, 0)
_DAY_END = datetime(2026, 1, 6, 0, 0, 0)


@cache
def _gen(seed: int, scenario: str, start: datetime, end: datetime, interval: int):
    return tuple(
        generate(
            seed=seed,
            scenario_id=scenario,
            start=start,
            end=end,
            interval_s=interval,
        )
    )


def _window():
    return _gen(42, "SC-00", _START, _END, 60)


def _day():
    return _gen(42, "SC-00", _DAY_START, _DAY_END, 300)


def _good_phase_none_index(
    readings,
) -> dict[tuple[datetime, str], dict[Channel, float]]:
    index: dict[tuple[datetime, str], dict[Channel, float]] = defaultdict(dict)
    for r in readings:
        if r.phase is None and r.quality is Quality.GOOD:
            index[(r.timestamp, r.node_id)][r.channel] = r.value
    return index


# --------------------------------------------------------------------------- #
# Basic shape / labelling                                                     #
# --------------------------------------------------------------------------- #
def test_generator_returns_readings():
    assert len(_window()) > 0
    assert all(isinstance(r, TelemetryReading) for r in _window())


def test_every_reading_is_synthetic():
    assert all(r.provenance is DataProvenance.SYNTHETIC for r in _window())


def test_every_reading_carries_a_quality():
    assert all(isinstance(r.quality, Quality) for r in _window())


def test_expected_channels_present():
    channels = {r.channel for r in _window()}
    for expected in (
        Channel.ACTIVE_POWER_KW,
        Channel.REACTIVE_POWER_KVAR,
        Channel.APPARENT_POWER_KVA,
        Channel.POWER_FACTOR,
        Channel.VOLTAGE_LL_V,
        Channel.CURRENT_A,
        Channel.ENERGY_ACTIVE_KWH,
        Channel.VOLTAGE_THD_PCT,
        Channel.CURRENT_TDD_PCT,
        Channel.WINDING_TEMPERATURE_C,
        Channel.TOP_OIL_TEMPERATURE_C,
        Channel.PANEL_TEMPERATURE_C,
        Channel.BEARING_TEMPERATURE_C,
        Channel.AMBIENT_TEMPERATURE_C,
        Channel.CAPACITOR_STAGES,
        Channel.BREAKER_POSITION,
        Channel.RUNTIME_HOURS,
        Channel.START_COUNT,
    ):
        assert expected in channels


def test_readings_are_time_ordered():
    times = [r.timestamp for r in _window()]
    assert times == sorted(times)


# --------------------------------------------------------------------------- #
# Cross-channel electrical consistency (the WP3 contract)                     #
# --------------------------------------------------------------------------- #
def test_apparent_power_consistent_with_active_and_reactive():
    index = _good_phase_none_index(_window())
    checked = 0
    for channels in index.values():
        if {
            Channel.APPARENT_POWER_KVA,
            Channel.ACTIVE_POWER_KW,
            Channel.REACTIVE_POWER_KVAR,
        } <= channels.keys():
            s = channels[Channel.APPARENT_POWER_KVA]
            p = channels[Channel.ACTIVE_POWER_KW]
            q = channels[Channel.REACTIVE_POWER_KVAR]
            assert abs(s * s - (p * p + q * q)) <= 1e-6 * (1.0 + s * s)
            checked += 1
    assert checked > 100


def test_active_power_equals_apparent_times_power_factor():
    index = _good_phase_none_index(_window())
    for channels in index.values():
        if {
            Channel.APPARENT_POWER_KVA,
            Channel.ACTIVE_POWER_KW,
            Channel.POWER_FACTOR,
        } <= channels.keys():
            s = channels[Channel.APPARENT_POWER_KVA]
            p = channels[Channel.ACTIVE_POWER_KW]
            pf = channels[Channel.POWER_FACTOR]
            assert abs(p - s * pf) <= 1e-6 * (1.0 + abs(p))


def test_apparent_power_equals_sqrt3_v_i():
    index = _good_phase_none_index(_window())
    for channels in index.values():
        if {
            Channel.APPARENT_POWER_KVA,
            Channel.VOLTAGE_LL_V,
            Channel.CURRENT_A,
        } <= channels.keys():
            s = channels[Channel.APPARENT_POWER_KVA]
            v = channels[Channel.VOLTAGE_LL_V]
            i = channels[Channel.CURRENT_A]
            assert abs(s * 1000.0 - _SQRT3 * v * i) <= 1e-3 * (1.0 + s * 1000.0)


def test_power_factor_within_physical_bounds():
    for r in _window():
        if r.channel is Channel.POWER_FACTOR and r.quality is Quality.GOOD:
            assert -1.0 - 1e-9 <= r.value <= 1.0 + 1e-9


def test_frequency_stays_near_nominal():
    for r in _window():
        if r.channel is Channel.FREQUENCY_HZ and r.quality is Quality.GOOD:
            assert 59.9 <= r.value <= 60.1


# --------------------------------------------------------------------------- #
# Energy registers                                                            #
# --------------------------------------------------------------------------- #
def test_energy_registers_monotonically_non_decreasing():
    series: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for r in _day():
        if r.channel is Channel.ENERGY_ACTIVE_KWH and r.quality in (
            Quality.GOOD,
            Quality.STALE,
        ):
            series[r.node_id].append((r.timestamp, r.value))
    assert series
    for samples in series.values():
        samples.sort()
        for (_, earlier), (_, later) in zip(samples, samples[1:], strict=False):
            assert later >= earlier - 1e-9


def test_energy_registers_strictly_increase_for_active_loads():
    motor = [
        r.value
        for r in sorted(_day(), key=lambda r: r.timestamp)
        if r.node_id == "MTR-001"
        and r.channel is Channel.ENERGY_ACTIVE_KWH
        and r.quality is Quality.GOOD
    ]
    assert motor[-1] > motor[0]


# --------------------------------------------------------------------------- #
# Parent-child power balance                                                  #
# --------------------------------------------------------------------------- #
def test_parent_child_active_balance_on_load_buses():
    facility = reference_facility("base")
    active: dict[datetime, dict[str, float]] = defaultdict(dict)
    current: dict[datetime, dict[str, float]] = defaultdict(dict)
    for r in _window():
        if r.phase is None and r.quality is Quality.GOOD:
            if r.channel is Channel.ACTIVE_POWER_KW:
                active[r.timestamp][r.node_id] = r.value
            elif r.channel is Channel.CURRENT_A:
                current[r.timestamp][r.node_id] = r.value

    checked = 0
    for parent_id, child_ids in facility.metered_balance_groups():
        if parent_id == "TX-001":
            continue  # transformer handled separately (adds core/copper loss)
        for moment, p_by_node in active.items():
            if parent_id not in p_by_node:
                continue
            if not all(c in p_by_node for c in child_ids):
                continue
            if not all(c in current[moment] for c in child_ids):
                continue
            child_sum = sum(p_by_node[c] for c in child_ids)
            losses = sum(
                3.0 * current[moment][c] ** 2 * facility.node(c).feeder_r_ohm / 1000.0
                for c in child_ids
            )
            residual = p_by_node[parent_id] - (child_sum + losses)
            assert abs(residual) <= 1e-3 * (1.0 + abs(p_by_node[parent_id]))
            checked += 1
    assert checked > 100


def test_transformer_balance_matches_loss_model():
    facility = reference_facility("base")
    tx = facility.node("TX-001")
    msb_feeder = facility.node("MSB-001")
    index = _good_phase_none_index(_window())
    checked = 0
    for (moment, node_id), channels in index.items():
        if node_id != "MSB-001":
            continue
        tx_channels = index.get((moment, "TX-001"))
        if tx_channels is None:
            continue
        needed = {Channel.ACTIVE_POWER_KW, Channel.APPARENT_POWER_KVA, Channel.CURRENT_A}
        if not (needed <= channels.keys()) or Channel.ACTIVE_POWER_KW not in tx_channels:
            continue
        p_msb = channels[Channel.ACTIVE_POWER_KW]
        s_msb = channels[Channel.APPARENT_POWER_KVA]
        i_msb = channels[Channel.CURRENT_A]
        p_tx = tx_channels[Channel.ACTIVE_POWER_KW]
        loading = s_msb / tx.rated_kva
        expected_tx_loss = tx.no_load_loss_kw + tx.load_loss_kw * loading * loading
        feeder_loss = 3.0 * i_msb**2 * msb_feeder.feeder_r_ohm / 1000.0
        residual = p_tx - (p_msb + feeder_loss + expected_tx_loss)
        assert abs(residual) <= 1e-2 * (1.0 + abs(p_tx))
        checked += 1
    assert checked > 100


def test_parent_power_never_less_than_children():
    facility = reference_facility("base")
    active: dict[datetime, dict[str, float]] = defaultdict(dict)
    for r in _window():
        if (
            r.phase is None
            and r.quality is Quality.GOOD
            and r.channel is Channel.ACTIVE_POWER_KW
        ):
            active[r.timestamp][r.node_id] = r.value
    for parent_id, child_ids in facility.metered_balance_groups():
        for _moment, p_by_node in active.items():
            if parent_id not in p_by_node or not all(c in p_by_node for c in child_ids):
                continue
            # Losses are non-negative, so the parent carries at least the net child load.
            assert p_by_node[parent_id] >= sum(p_by_node[c] for c in child_ids) - 1e-6


# --------------------------------------------------------------------------- #
# Determinism                                                                 #
# --------------------------------------------------------------------------- #
def test_identical_inputs_produce_identical_output():
    a = list(_gen(42, "SC-00", _START, _END, 60))
    b = list(
        generate(
            seed=42,
            scenario_id="SC-00",
            start=_START,
            end=_END,
            interval_s=60,
        )
    )
    assert a == b


def test_output_is_byte_identical_key_tuples():
    a = _gen(42, "SC-00", _START, _END, 60)
    b = _gen(42, "SC-00", _START, _END, 60)
    ka = [(r.node_id, r.channel.value, round(r.value, 9)) for r in a]
    kb = [(r.node_id, r.channel.value, round(r.value, 9)) for r in b]
    assert ka == kb


def test_different_seed_changes_values_not_structure():
    a = _gen(42, "SC-00", _START, _END, 60)
    b = _gen(43, "SC-00", _START, _END, 60)
    assert len(a) == len(b)
    assert [r.channel for r in a] == [r.channel for r in b]
    assert [r.node_id for r in a] == [r.node_id for r in b]
    assert any(ra.value != rb.value for ra, rb in zip(a, b, strict=True))


def test_timezone_aware_input_matches_naive_utc():
    naive = _gen(42, "SC-00", _START, _END, 60)
    aware = generate(
        seed=42,
        scenario_id="SC-00",
        start=_START.replace(tzinfo=UTC),
        end=_END.replace(tzinfo=UTC),
        interval_s=60,
    )
    naive_keys = [(r.node_id, r.channel, round(r.value, 9)) for r in naive]
    aware_keys = [(r.node_id, r.channel, round(r.value, 9)) for r in aware]
    assert naive_keys == aware_keys


# --------------------------------------------------------------------------- #
# Capacitor bank -> emergent power factor                                     #
# --------------------------------------------------------------------------- #
def _msb_stage_and_pf(readings):
    stage: dict[datetime, float] = {}
    pf: dict[datetime, float] = {}
    for r in readings:
        if r.quality is not Quality.GOOD:
            continue
        if r.node_id == "CAP-001" and r.channel is Channel.CAPACITOR_STAGES:
            stage[r.timestamp] = r.value
        elif r.node_id == "MSB-001" and r.channel is Channel.POWER_FACTOR:
            pf[r.timestamp] = r.value
    common = sorted(set(stage) & set(pf))
    return [(stage[t], pf[t]) for t in common]


def test_capacitor_bank_actually_steps():
    stages = {
        r.value
        for r in _day()
        if r.node_id == "CAP-001"
        and r.channel is Channel.CAPACITOR_STAGES
        and r.quality is Quality.GOOD
    }
    assert len(stages) > 1  # the bank steps in and out


def test_power_factor_responds_to_capacitor_stepping():
    pairs = _msb_stage_and_pf(_day())
    assert pairs
    stages = [s for s, _ in pairs]
    lo, hi = min(stages), max(stages)
    assert hi > lo
    pf_low = [pf for s, pf in pairs if s == lo]
    pf_high = [pf for s, pf in pairs if s == hi]
    # More capacitor stages in => higher (better) power factor.
    assert sum(pf_high) / len(pf_high) > sum(pf_low) / len(pf_low)


def test_power_factor_is_not_a_written_constant():
    values = {
        round(r.value, 4)
        for r in _day()
        if r.node_id == "MSB-001"
        and r.channel is Channel.POWER_FACTOR
        and r.quality is Quality.GOOD
    }
    assert len(values) > 5  # emergent, varies over time


def test_capacitor_stages_within_configured_bounds():
    cap = reference_facility("base").node("CAP-001")
    for r in _day():
        if r.channel is Channel.CAPACITOR_STAGES and r.quality is Quality.GOOD:
            assert 0.0 <= r.value <= cap.cap_max_stages


def test_capacitor_operation_count_monotonic():
    ops = [
        r.value
        for r in sorted(_day(), key=lambda r: r.timestamp)
        if r.node_id == "CAP-001"
        and r.channel is Channel.BREAKER_OPERATION_COUNT
        and r.quality in (Quality.GOOD, Quality.STALE)
    ]
    assert ops == sorted(ops)
    assert ops[-1] >= 1  # at least one operation over a day


# --------------------------------------------------------------------------- #
# Harmonics, unbalance, temperatures, counters                               #
# --------------------------------------------------------------------------- #
def test_thd_and_tdd_correlate_with_vfd_loading():
    per_time_loading: dict[datetime, float] = {}
    per_time_tdd: dict[datetime, float] = {}
    for r in _day():
        if r.node_id != "MTR-001" or r.quality is not Quality.GOOD:
            continue
        if r.channel is Channel.APPARENT_POWER_KVA:
            per_time_loading[r.timestamp] = r.value
        elif r.channel is Channel.CURRENT_TDD_PCT:
            per_time_tdd[r.timestamp] = r.value
    common = sorted(set(per_time_loading) & set(per_time_tdd))
    loadings = [per_time_loading[t] for t in common]
    tdds = [per_time_tdd[t] for t in common]
    lo_idx = loadings.index(min(loadings))
    hi_idx = loadings.index(max(loadings))
    assert tdds[hi_idx] > tdds[lo_idx]


def test_voltage_unbalance_present_but_small():
    values = [
        r.value
        for r in _window()
        if r.channel is Channel.VOLTAGE_UNBALANCE_PCT and r.quality is Quality.GOOD
    ]
    assert values
    assert all(0.0 <= v < 3.0 for v in values)
    assert max(values) > 0.0


def test_per_phase_currents_are_unbalanced():
    by_phase: dict[PhaseTag, float] = {}
    for r in _window():
        if (
            r.node_id == "MTR-001"
            and r.channel is Channel.CURRENT_A
            and r.phase in (PhaseTag.A, PhaseTag.B, PhaseTag.C)
            and r.quality is Quality.GOOD
        ):
            by_phase.setdefault(r.phase, r.value)
        if len(by_phase) == 3:
            break
    assert len(by_phase) == 3
    assert len({round(v, 3) for v in by_phase.values()}) > 1


def test_winding_temperature_exceeds_ambient_and_lags():
    winding: list[tuple[datetime, float]] = []
    ambient_max = 0.0
    for r in _day():
        if r.node_id != "MTR-001" or r.quality is not Quality.GOOD:
            continue
        if r.channel is Channel.WINDING_TEMPERATURE_C:
            winding.append((r.timestamp, r.value))
        elif r.channel is Channel.AMBIENT_TEMPERATURE_C:
            ambient_max = max(ambient_max, r.value)
    winding.sort()
    temps = [v for _, v in winding]
    assert max(temps) > ambient_max  # heated by load above ambient
    # First-order lag => no large step between adjacent 5-minute samples.
    assert max(abs(b - a) for a, b in zip(temps, temps[1:], strict=False)) < 8.0


def test_runtime_hours_and_start_count_monotonic():
    runtime = [
        r.value
        for r in sorted(_day(), key=lambda r: r.timestamp)
        if r.node_id == "MTR-001"
        and r.channel is Channel.RUNTIME_HOURS
        and r.quality in (Quality.GOOD, Quality.STALE)
    ]
    starts = [
        r.value
        for r in sorted(_day(), key=lambda r: r.timestamp)
        if r.node_id == "MTR-001"
        and r.channel is Channel.START_COUNT
        and r.quality in (Quality.GOOD, Quality.STALE)
    ]
    assert runtime == sorted(runtime)
    assert starts == sorted(starts)


def test_breaker_positions_closed_on_baseline():
    for r in _window():
        if (
            r.channel is Channel.BREAKER_POSITION
            and r.quality is Quality.GOOD
            and r.node_id != "CAP-001"
        ):
            assert r.value == 1.0


# --------------------------------------------------------------------------- #
# Solar PV                                                                     #
# --------------------------------------------------------------------------- #
def test_pv_injects_negative_power_midday():
    pv_by_hour: dict[int, list[float]] = defaultdict(list)
    for r in _day():
        if (
            r.node_id == "PV-001"
            and r.channel is Channel.ACTIVE_POWER_KW
            and r.quality is Quality.GOOD
        ):
            pv_by_hour[r.timestamp.hour].append(r.value)
    midday = [v for h in (11, 12, 13) for v in pv_by_hour.get(h, [])]
    assert midday
    assert min(midday) < -50.0  # meaningful PV injection reduces net import


def test_pv_is_zero_overnight():
    for r in _day():
        if (
            r.node_id == "PV-001"
            and r.channel is Channel.ACTIVE_POWER_KW
            and r.quality is Quality.GOOD
            and r.timestamp.hour in (0, 1, 2, 3, 4)
        ):
            assert abs(r.value) < 1e-9


# --------------------------------------------------------------------------- #
# STALE / MISSING quality injection                                           #
# --------------------------------------------------------------------------- #
def test_stale_and_missing_present_in_small_proportion():
    counts = Counter(r.quality for r in _day())
    total = sum(counts.values())
    missing = counts[Quality.MISSING] / total
    stale = counts[Quality.STALE] / total
    assert 0.001 < missing < 0.02
    assert 0.004 < stale < 0.03
    assert counts[Quality.GOOD] / total > 0.95


def test_quality_mix_identical_across_runs_with_same_seed():
    a = Counter(r.quality for r in _gen(42, "SC-00", _DAY_START, _DAY_END, 300))
    b = Counter(
        r.quality
        for r in generate(
            seed=42,
            scenario_id="SC-00",
            start=_DAY_START,
            end=_DAY_END,
            interval_s=300,
        )
    )
    assert a == b


def test_stale_and_missing_positions_identical_across_runs():
    a = _gen(42, "SC-00", _START, _END, 60)
    b = tuple(
        generate(seed=42, scenario_id="SC-00", start=_START, end=_END, interval_s=60)
    )
    a_flags = [(r.node_id, r.channel, r.phase, r.quality) for r in a]
    b_flags = [(r.node_id, r.channel, r.phase, r.quality) for r in b]
    assert a_flags == b_flags


# --------------------------------------------------------------------------- #
# Scenario handling                                                           #
# --------------------------------------------------------------------------- #
def test_unknown_scenario_generates_clean_baseline():
    baseline = _gen(42, "SC-00", _START, _END, 60)
    unknown = tuple(
        generate(
            seed=42, scenario_id="SC-UNKNOWN-XYZ", start=_START, end=_END, interval_s=60
        )
    )
    a = [(r.node_id, r.channel, round(r.value, 9)) for r in baseline]
    b = [(r.node_id, r.channel, round(r.value, 9)) for r in unknown]
    assert a == b


# --------------------------------------------------------------------------- #
# Interval / validation                                                       #
# --------------------------------------------------------------------------- #
def test_interval_controls_sample_count():
    coarse = _gen(1, "SC-00", _START, _END, 3600)
    fine = _gen(1, "SC-00", _START, _END, 1800)
    coarse_times = {r.timestamp for r in coarse}
    fine_times = {r.timestamp for r in fine}
    assert len(coarse_times) == 3
    assert len(fine_times) == 6


def test_non_positive_interval_raises():
    with pytest.raises(ValueError):
        generate(seed=1, scenario_id="SC-00", start=_START, end=_END, interval_s=0)
