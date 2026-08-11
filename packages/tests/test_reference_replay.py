"""Tests for the deterministic replay engine.

The headline test is :func:`test_replay_is_deterministic_across_process_boundary`:
it replays the same scenario twice in-process and once in a *separate* Python
process (with a different ``PYTHONHASHSEED``), and requires all three hashes to
be identical. A generator that is deterministic within a process but not across
processes would pass a naive in-process test and fail here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from packages.reference_facility import replay, replay_manifest
from packages.reference_facility.replay import _timestamps

_REPO_ROOT = Path(__file__).resolve().parents[2]

_START = datetime(2026, 1, 5)
_END = datetime(2026, 1, 6)


def _hash_in_subprocess(scenario_id: str, seed: int, hashseed: str) -> str:
    """Run one replay in a fresh interpreter and return its result hash."""

    code = (
        "from datetime import datetime;"
        "from packages.reference_facility.replay import replay;"
        f"print(replay({scenario_id!r}, {seed}, datetime(2026,1,5), "
        "datetime(2026,1,6), 120).result_hash)"
    )
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hashseed
    env["PYTHONPATH"] = str(_REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def test_replay_is_deterministic_in_process() -> None:
    a = replay("SC-08", 42, _START, _END, 120)
    b = replay("SC-08", 42, _START, _END, 120)
    assert a.result_hash == b.result_hash


def test_replay_is_deterministic_across_process_boundary() -> None:
    # Two in-process replays.
    first = replay("SC-08", 42, _START, _END, 120).result_hash
    second = replay("SC-08", 42, _START, _END, 120).result_hash
    # One in a separate process with a hash seed different from this process,
    # and another with a further seed, to defeat any reliance on hash salting.
    sub_random = _hash_in_subprocess("SC-08", 42, "random")
    sub_zero = _hash_in_subprocess("SC-08", 42, "0")
    assert first == second == sub_random == sub_zero


def test_result_hash_is_a_sha256_hex_digest() -> None:
    result = replay("SC-01", 1, _START, _END, 3600)
    assert len(result.result_hash) == 64
    assert all(c in "0123456789abcdef" for c in result.result_hash)


def test_different_seed_changes_the_hash() -> None:
    a = replay("SC-01", 1, _START, _END, 600)
    b = replay("SC-01", 2, _START, _END, 600)
    assert a.result_hash != b.result_hash


def test_different_scenario_changes_the_hash() -> None:
    a = replay("SC-01", 1, _START, _END, 600).result_hash
    b = replay("SC-02", 1, _START, _END, 600).result_hash
    assert a != b


def test_reading_count_matches_points_times_intervals() -> None:
    result = replay("SC-01", 1, _START, _END, 3600)
    scenario_points = len(result.readings) // len(_timestamps(_START, _END, 3600))
    assert len(result.readings) == scenario_points * 24


def test_readings_carry_synthetic_provenance() -> None:
    result = replay("SC-01", 1, _START, _END, 3600)
    assert result.readings
    for reading in result.readings[:20]:
        assert reading.provenance.source.value == "SYNTHETIC"


def test_window_is_half_open() -> None:
    result = replay("SC-01", 1, _START, _END, 3600)
    timestamps = [r.timestamp for r in result.readings]
    assert min(timestamps) == _START
    assert max(timestamps) < _END


def test_invalid_interval_raises() -> None:
    with pytest.raises(ValueError):
        replay("SC-01", 1, _START, _END, 0)


def test_end_before_start_raises() -> None:
    with pytest.raises(ValueError):
        replay("SC-01", 1, _END, _START, 60)


def test_topology_snapshots_capture_each_switching_change() -> None:
    result = replay("SC-08", 42, _START, _END, 120)
    # SC-08 has two switching events -> initial snapshot plus two.
    assert len(result.topology_snapshots) == 3
    captured = [s.captured_at for s in result.topology_snapshots]
    assert captured == sorted(captured)
    assert captured[0] == _START


def test_topology_snapshot_reflects_switch_change() -> None:
    result = replay("SC-08", 42, _START, _END, 120)
    first, second = result.topology_snapshots[0], result.topology_snapshots[1]

    def tie(snapshot) -> str:
        return next(e.switch_state.value for e in snapshot.edges if e.id == "E-TIE-AB")

    assert tie(first) == "OPEN"
    assert tie(second) == "CLOSED"


def test_scenario_without_switching_events_has_single_snapshot() -> None:
    result = replay("SC-01", 1, _START, _END, 3600)
    assert len(result.topology_snapshots) == 1


def test_perturbation_shifts_values_relative_to_baseline() -> None:
    # SC-12 applies a sustained ~1.08 overvoltage across the main buses.
    nominal = replay("SC-01", 5, _START, _END, 600)
    overvoltage = replay("SC-12", 5, _START, _END, 600)

    def mean_bus_a_voltage(result) -> float:
        values = [
            r.value
            for r in result.readings
            if r.node_id == "BUS-A" and r.channel == "VOLTAGE_LINE_TO_NEUTRAL_V"
        ]
        return sum(values) / len(values)

    assert mean_bus_a_voltage(overvoltage) > mean_bus_a_voltage(nominal) * 1.05


def test_manifest_matches_replay_and_omits_data() -> None:
    manifest = replay_manifest("SC-08", 42, _START, _END, 120)
    result = replay("SC-08", 42, _START, _END, 120)
    assert manifest.result_hash == result.result_hash
    assert manifest.reading_count == len(result.readings)
    assert manifest.switching_change_count == len(result.topology_snapshots)
    # The manifest is a dataclass of parameters + hash; it carries no readings.
    assert not hasattr(manifest, "readings")


def test_manifest_to_dict_is_json_friendly() -> None:
    manifest = replay_manifest("SC-08", 42, _START, _END, 120)
    payload = manifest.to_dict()
    assert payload["scenario_id"] == "SC-08"
    assert payload["result_hash"] == manifest.result_hash
    assert isinstance(payload["start"], str)
    assert payload["monitored_points"]


def test_ground_truth_is_carried_through() -> None:
    result = replay("SC-08", 42, _START, _END, 120)
    assert result.ground_truth.summary
    assert "BUS-B" in result.ground_truth.affected_node_ids
