"""Deterministic replay engine for the reference facility.

:func:`replay` regenerates a scenario's synthetic telemetry over a time window
for a given seed. The result is fully reproducible: the same inputs always
produce byte-identical output, **in the same process and in any other process**.

Cross-process determinism is the whole point, and it drives one hard design
rule: pseudo-randomness is derived only from :mod:`hashlib`, never from the
:mod:`random` module or the built-in :func:`hash`. Python salts string/bytes
hashing per interpreter (``PYTHONHASHSEED``), so anything built on :func:`hash`
would agree with itself within a run and silently disagree across runs. A
sha256 of a canonical key string has no such hazard.

``result_hash`` is a sha256 over the canonically serialised readings, so a
demonstration can be proven reproducible by comparing hashes without shipping
the underlying telemetry. :func:`replay_manifest` returns the parameters plus
that hash for exactly this purpose.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from packages.canonical_electrical_model import (
    ElectricalReading,
    Provenance,
    ProvenanceSource,
    SwitchState,
    TopologySnapshot,
)

from .scenarios import GroundTruth, Perturbation, Scenario, get_scenario
from .topology import VARIANT_OVERRIDES, build_snapshot

#: Version tag mixed into every derived value and the result hash. Bumping it
#: intentionally changes all hashes (e.g. if the generation scheme changes).
_STREAM_VERSION = "reference_facility.replay.v1"

_UNIT_DENOMINATOR = float(1 << 64)

# Values are rounded to this many decimals so both the stored reading value and
# its serialisation are stable across platforms and processes.
_VALUE_DECIMALS = 6


@dataclass(frozen=True)
class ReplayResult:
    """The full, reproducible output of a replay."""

    scenario_id: str
    seed: int
    start: datetime
    end: datetime
    interval_s: int
    topology_variant: str
    readings: list[ElectricalReading]
    topology_snapshots: list[TopologySnapshot]
    ground_truth: GroundTruth
    result_hash: str


@dataclass(frozen=True)
class ReplayManifest:
    """The parameters of a replay plus its result hash, without the data.

    This is enough to prove a replay reproducible: regenerate with the same
    parameters and confirm the ``result_hash`` matches.
    """

    scenario_id: str
    seed: int
    start: datetime
    end: datetime
    interval_s: int
    topology_variant: str
    interval_count: int
    reading_count: int
    switching_change_count: int
    monitored_points: list[dict[str, str]]
    ground_truth_summary: str
    result_hash: str

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serialisable view of the manifest."""

        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "interval_s": self.interval_s,
            "topology_variant": self.topology_variant,
            "interval_count": self.interval_count,
            "reading_count": self.reading_count,
            "switching_change_count": self.switching_change_count,
            "monitored_points": self.monitored_points,
            "ground_truth_summary": self.ground_truth_summary,
            "result_hash": self.result_hash,
        }


def _unit_float(*parts: str) -> float:
    """A deterministic, process-independent pseudo-random float in ``[0, 1)``.

    Derived from a sha256 of the canonical key. Using a cryptographic hash of a
    fixed string (rather than :func:`hash`) is what makes this identical across
    interpreter processes regardless of ``PYTHONHASHSEED``.
    """

    key = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:8], "big") / _UNIT_DENOMINATOR


def _validate_window(start: datetime, end: datetime, interval_s: int) -> None:
    if interval_s <= 0:
        raise ValueError(f"interval_s must be a positive integer, got {interval_s!r}.")
    if end <= start:
        raise ValueError(f"end ({end.isoformat()}) must be after start ({start.isoformat()}).")


def _timestamps(start: datetime, end: datetime, interval_s: int) -> list[datetime]:
    """Sample times ``start + k*interval`` for ``k >= 0`` while strictly before ``end``."""

    total_seconds = (end - start).total_seconds()
    n_steps = int(total_seconds // interval_s)
    step = timedelta(seconds=interval_s)
    return [start + k * step for k in range(n_steps)]


def _apply_perturbations(
    value: float,
    perturbations: list[Perturbation],
    node_id: str,
    channel: str,
    fraction: float,
) -> float:
    for perturbation in perturbations:
        if node_id not in perturbation.node_ids:
            continue
        if channel not in perturbation.channels:
            continue
        if not (perturbation.start_fraction <= fraction < perturbation.end_fraction):
            continue
        if perturbation.mode == "scale":
            value *= perturbation.amount
        else:
            value += perturbation.amount
    return value


def _generate_readings(
    scenario: Scenario,
    seed: int,
    timestamps: list[datetime],
) -> list[ElectricalReading]:
    provenance = Provenance(
        source=ProvenanceSource.SYNTHETIC,
        method="reference_facility.replay",
        reference=scenario.scenario_id,
    )
    seed_str = str(seed)
    n_steps = len(timestamps)
    readings: list[ElectricalReading] = []

    for point in scenario.monitored:
        for k, timestamp in enumerate(timestamps):
            iso = timestamp.isoformat()
            unit_noise = _unit_float(
                _STREAM_VERSION, scenario.scenario_id, seed_str, point.node_id, point.channel, iso
            )
            value = point.base_value + (unit_noise - 0.5) * 2.0 * point.noise_amplitude
            fraction = k / n_steps if n_steps else 0.0
            value = _apply_perturbations(
                value, scenario.perturbations, point.node_id, point.channel, fraction
            )
            readings.append(
                ElectricalReading(
                    node_id=point.node_id,
                    channel=point.channel,
                    value=round(value, _VALUE_DECIMALS),
                    unit=point.unit,
                    timestamp=timestamp,
                    provenance=provenance,
                )
            )
    return readings


def _topology_snapshots(
    scenario: Scenario,
    start: datetime,
    end: datetime,
) -> list[TopologySnapshot]:
    """Initial snapshot plus one at each switching change inside the window."""

    total_seconds = (end - start).total_seconds()
    overrides: dict[str, SwitchState] = dict(VARIANT_OVERRIDES[scenario.topology_variant])

    snapshots: list[TopologySnapshot] = [
        build_snapshot(
            dict(overrides),
            captured_at=start,
            snapshot_id=f"{scenario.scenario_id}-SNAP-000",
        )
    ]

    ordered_events = sorted(
        scenario.switching_events, key=lambda e: (e.at_fraction, e.edge_id)
    )
    index = 1
    for event in ordered_events:
        if not (0.0 <= event.at_fraction < 1.0):
            continue
        overrides[event.edge_id] = event.new_state
        captured_at = start + timedelta(seconds=event.at_fraction * total_seconds)
        snapshots.append(
            build_snapshot(
                dict(overrides),
                captured_at=captured_at,
                snapshot_id=f"{scenario.scenario_id}-SNAP-{index:03d}",
            )
        )
        index += 1
    return snapshots


def _result_hash(readings: list[ElectricalReading]) -> str:
    """A sha256 over the canonical serialisation of the readings.

    The canonical form is a fixed, ordered, line-per-reading encoding of the
    fields that define a reading's identity and value. ``repr`` of the rounded
    float is the shortest round-tripping decimal, which is stable across
    processes and platforms.
    """

    hasher = hashlib.sha256()
    hasher.update(f"{_STREAM_VERSION}\n".encode())
    for reading in readings:
        phase = reading.phase.value if reading.phase is not None else ""
        line = (
            f"{reading.node_id}\x1f{reading.channel}\x1f{phase}\x1f"
            f"{reading.value!r}\x1f{reading.unit}\x1f"
            f"{reading.timestamp.isoformat()}\x1f{reading.quality.value}\n"
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def replay(
    scenario_id: str,
    seed: int,
    start: datetime,
    end: datetime,
    interval_s: int,
) -> ReplayResult:
    """Deterministically replay a scenario over a time window.

    Parameters
    ----------
    scenario_id:
        The scenario to replay (see :func:`reference_facility.all_scenarios`).
    seed:
        Integer seed. The same seed reproduces byte-identical telemetry; a
        different seed re-rolls the noise band while preserving the scenario's
        structure and ground truth.
    start, end:
        Half-open time window ``[start, end)``. ``end`` must be after ``start``.
    interval_s:
        Sample interval in seconds; must be positive.

    Returns
    -------
    ReplayResult
        Readings, topology snapshots at each switching change, the ground truth
        and the ``result_hash`` proving reproducibility.

    Raises:
        UnknownScenarioError: if ``scenario_id`` is unknown.
        ValueError: if the window or interval is invalid.
    """

    _validate_window(start, end, interval_s)
    scenario = get_scenario(scenario_id)

    timestamps = _timestamps(start, end, interval_s)
    readings = _generate_readings(scenario, seed, timestamps)
    snapshots = _topology_snapshots(scenario, start, end)

    return ReplayResult(
        scenario_id=scenario.scenario_id,
        seed=seed,
        start=start,
        end=end,
        interval_s=interval_s,
        topology_variant=scenario.topology_variant,
        readings=readings,
        topology_snapshots=snapshots,
        ground_truth=scenario.ground_truth,
        result_hash=_result_hash(readings),
    )


def replay_manifest(
    scenario_id: str,
    seed: int,
    start: datetime,
    end: datetime,
    interval_s: int,
) -> ReplayManifest:
    """Return the replay parameters plus the result hash, without the data.

    The manifest is computed by running the replay and discarding the bulk
    telemetry, keeping only counts, the monitored-point list and the hash. This
    lets a demonstration prove reproducibility (matching hashes) without
    shipping or persisting the readings themselves.
    """

    result = replay(scenario_id, seed, start, end, interval_s)
    scenario = get_scenario(scenario_id)
    monitored_points = [
        {"node_id": point.node_id, "channel": point.channel}
        for point in scenario.monitored
    ]
    interval_count = len(_timestamps(start, end, interval_s))

    return ReplayManifest(
        scenario_id=result.scenario_id,
        seed=result.seed,
        start=result.start,
        end=result.end,
        interval_s=result.interval_s,
        topology_variant=result.topology_variant,
        interval_count=interval_count,
        reading_count=len(result.readings),
        switching_change_count=len(result.topology_snapshots),
        monitored_points=monitored_points,
        ground_truth_summary=result.ground_truth.summary,
        result_hash=result.result_hash,
    )
