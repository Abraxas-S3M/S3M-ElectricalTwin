"""Telemetry generation and fault-injection tests.

The generator is the mechanism that turns a scenario's ground truth into data.
These tests verify that ``generate`` is deterministic, that SC-00 is genuinely
untouched, that the power-balance guard sees the unmetered load in SC-08 (and
only there), and that each scenario's fault actually appears at its labelled
onset.
"""

from __future__ import annotations

import pytest

from packages.canonical_electrical_model.provenance import ProvenanceSource
from packages.reference_facility import (
    generate,
    max_power_imbalance_kw,
    metered_parents,
    power_balance_breaks_at,
    sim_index,
    sim_timestamp,
)
from packages.reference_facility.scenarios import all_scenarios, scenario_by_id
from packages.reference_facility.telemetry import _UNMETERED_KW

_SCENARIOS = all_scenarios()
_IDS = [s.scenario_id for s in _SCENARIOS]


def test_generate_default_is_baseline() -> None:
    default = generate()
    assert default.scenario_id == "SC-00"


def test_generate_unknown_scenario_raises() -> None:
    with pytest.raises(KeyError):
        generate("SC-99")


@pytest.mark.parametrize("scenario_id", _IDS)
def test_generate_produces_readings(scenario_id: str) -> None:
    gen = generate(scenario_id)
    assert len(gen.readings) > 0


@pytest.mark.parametrize("scenario_id", _IDS)
def test_generate_is_deterministic(scenario_id: str) -> None:
    first = generate(scenario_id)
    second = generate(scenario_id)
    assert first.readings == second.readings


@pytest.mark.parametrize("scenario_id", _IDS)
def test_all_readings_are_synthetic(scenario_id: str) -> None:
    gen = generate(scenario_id)
    assert all(
        r.provenance.source is ProvenanceSource.SYNTHETIC for r in gen.readings
    )


@pytest.mark.parametrize("scenario_id", _IDS)
def test_all_reading_timestamps_within_window(scenario_id: str) -> None:
    gen = generate(scenario_id)
    lo = gen.start
    hi = gen.start + (gen.steps - 1) * gen.step
    assert all(lo <= r.timestamp <= hi for r in gen.readings)


def test_baseline_emits_only_power_channels() -> None:
    gen = generate("SC-00")
    channels = {r.channel for r in gen.readings}
    assert channels == {"real_power_kw"}


def test_baseline_power_balance_holds_everywhere() -> None:
    gen = generate("SC-00")
    assert power_balance_breaks_at(gen) == set()
    assert all(gap < 1e-6 for gap in max_power_imbalance_kw(gen).values())


def test_sc08_breaks_balance_only_at_mcc003() -> None:
    gen = generate("SC-08")
    assert power_balance_breaks_at(gen) == {"MCC-003"}


def test_sc08_imbalance_equals_unmetered_load() -> None:
    gen = generate("SC-08")
    imbalance = max_power_imbalance_kw(gen)
    assert imbalance["MCC-003"] == pytest.approx(_UNMETERED_KW)
    for parent in metered_parents():
        if parent != "MCC-003":
            assert imbalance[parent] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("scenario_id", _IDS)
def test_only_sc08_breaks_power_balance(scenario_id: str) -> None:
    breaks = power_balance_breaks_at(generate(scenario_id))
    if scenario_id == "SC-08":
        assert breaks == {"MCC-003"}
    else:
        assert breaks == set()


def test_sc08_unmetered_load_appears_at_onset() -> None:
    sc08 = scenario_by_id("SC-08")
    assert sc08.onset_at is not None
    onset = sim_index(sc08.onset_at)
    gen = generate("SC-08")
    series = dict(gen.channel_series("MCC-003", "real_power_kw"))
    before = series[sim_timestamp(onset - 1)]
    at_onset = series[sim_timestamp(onset)]
    # The tapped load raises the MCC-003 feed by exactly the unmetered amount.
    assert at_onset - before == pytest.approx(_UNMETERED_KW)


def test_sc01_thermal_rises_after_onset() -> None:
    gen = generate("SC-01")
    loading = gen.channel_series("TX-001", "loading_percent")
    hot_spot = gen.channel_series("TX-001", "hot_spot_temperature_c")
    assert loading[0][1] == pytest.approx(85.0)
    assert loading[-1][1] > 100.0
    assert hot_spot[-1][1] > hot_spot[0][1]


def test_sc06_thd_crosses_ieee519_limit() -> None:
    gen = generate("SC-06")
    thd = gen.channel_series("SWGR-LV-002", "voltage_thd_percent")
    assert thd[0][1] == pytest.approx(3.0)
    assert thd[-1][1] > 5.0


def test_sc05_sag_is_a_single_sample_on_onset() -> None:
    sc05 = scenario_by_id("SC-05")
    assert sc05.onset_at is not None
    onset = sim_index(sc05.onset_at)
    gen = generate("SC-05")
    for bus in ("UTIL-001", "SWGR-LV-001", "SWGR-LV-002"):
        series = dict(gen.channel_series(bus, "voltage_pu"))
        assert series[sim_timestamp(onset)] == pytest.approx(0.65)
        assert series[sim_timestamp(onset - 1)] == pytest.approx(1.0)
        assert series[sim_timestamp(onset + 1)] == pytest.approx(1.0)


def test_sc09_position_inconsistency_at_onset() -> None:
    sc09 = scenario_by_id("SC-09")
    assert sc09.onset_at is not None
    onset = sim_index(sc09.onset_at)
    gen = generate("SC-09")
    reported = dict(gen.channel_series("CB-LV-005", "breaker_reported_closed"))
    current = dict(gen.channel_series("CB-LV-005", "through_current_a"))
    downstream = dict(gen.channel_series("PNL-LV-005", "voltage_pu"))
    # Reports CLOSED both before and after; physics collapses at onset.
    assert reported[sim_timestamp(onset - 1)] == pytest.approx(1.0)
    assert reported[sim_timestamp(onset)] == pytest.approx(1.0)
    assert current[sim_timestamp(onset - 1)] > 0.0
    assert current[sim_timestamp(onset)] == pytest.approx(0.0)
    assert downstream[sim_timestamp(onset)] == pytest.approx(0.0)


def test_sc10_transfer_sequence() -> None:
    sc10 = scenario_by_id("SC-10")
    assert sc10.onset_at is not None
    onset = sim_index(sc10.onset_at)
    gen = generate("SC-10")
    util = dict(gen.channel_series("UTIL-001", "voltage_pu"))
    ups = dict(gen.channel_series("UPS-001", "output_voltage_pu"))
    gen_out = dict(gen.channel_series("GEN-001", "output_voltage_pu"))
    ats = dict(gen.channel_series("ATS-001", "source_position"))
    assert util[sim_timestamp(onset - 1)] == pytest.approx(1.0)
    assert util[sim_timestamp(onset)] == pytest.approx(0.0)
    # UPS bridges throughout; generator ramps up; ATS ends on the generator.
    assert ups[sim_timestamp(onset)] == pytest.approx(1.0)
    assert gen_out[sim_timestamp(onset - 1)] == pytest.approx(0.0)
    assert gen_out[max(ats)] == pytest.approx(1.0)
    assert ats[max(ats)] == pytest.approx(1.0)


def test_sc11_meter_drift_grows_over_time() -> None:
    gen = generate("SC-11")
    indicated = gen.channel_series("MTR-MCC-002", "meter_indicated_kw")
    true_power = dict(gen.channel_series("MCC-002", "real_power_kw"))
    first_ts, first_val = indicated[0]
    last_ts, last_val = indicated[-1]
    # Early on the meter matches truth; by the end it reads high and the gap
    # has grown monotonically in the wrong direction.
    assert first_val == pytest.approx(true_power[first_ts])
    assert last_val > true_power[last_ts]
    assert (last_val - true_power[last_ts]) > (first_val - true_power[first_ts])


def test_sc12_efficiency_degrades() -> None:
    gen = generate("SC-12")
    kw_per_ton = gen.channel_series("CH-001", "kw_per_ton")
    power = gen.channel_series("CH-001", "real_power_kw")
    assert kw_per_ton[-1][1] > kw_per_ton[0][1]
    # Rising kW-per-ton shows up as rising real power, but stays fully metered.
    assert power[-1][1] > power[0][1]
    assert power_balance_breaks_at(gen) == set()
