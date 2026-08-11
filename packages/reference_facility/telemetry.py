"""Deterministic telemetry generator with per-scenario fault injection.

:func:`generate` builds a fixed synthetic telemetry record for the reference
facility and, when given a scenario id, injects exactly that scenario's fault
at its labelled ``onset_at``. ``generate("SC-00")`` is the untouched baseline:
no injector runs, so the control is healthy by construction.

The generator is pure and deterministic — no randomness, no clock, no I/O — so
that a scenario's ground truth (onset, earliest-detectable point, fault nodes)
maps to exactly reproducible samples that a benchmark can score against.

Real power is built bottom-up through the metered hierarchy: a parent feed
equals the sum of its child meters *plus any injected unmetered load*. That is
the one relationship SC-08 breaks, and the power-balance helpers here expose it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from packages.canonical_electrical_model.provenance import (
    Provenance,
    ProvenanceSource,
)
from packages.canonical_electrical_model.telemetry import ElectricalReading

from .facility import (
    BASE_LOAD_KW,
    POWER_HIERARCHY,
    SIM_START,
    SIM_STEP,
    SIM_STEPS,
    metered_parents,
    sim_index,
)
from .scenarios.catalog import scenario_by_id

_SYNTHETIC = Provenance(
    source=ProvenanceSource.SYNTHETIC,
    method="reference_facility.telemetry.generate",
)

# IEEE 519 voltage THD compliance limit (%) for systems <= 1 kV.
_THD_LIMIT_PCT = 5.0

# Amount of unmetered real power (kW) tapped onto MCC-003 in SC-08.
_UNMETERED_KW = 18.0

# Cooling delivered by CH-001 (refrigeration tons), held constant so a rising
# kW-per-ton in SC-12 is unambiguously an efficiency loss.
_CH001_TONS = 200.0
_CH001_BASE_KW_PER_TON = BASE_LOAD_KW["CH-001"] / _CH001_TONS


@dataclass(frozen=True)
class GeneratedTelemetry:
    """A synthetic telemetry record for one scenario over the sim window."""

    scenario_id: str
    start: datetime
    step: timedelta
    steps: int
    readings: list[ElectricalReading] = field(default_factory=list)

    def channel_series(
        self, node_id: str, channel: str
    ) -> list[tuple[datetime, float]]:
        """Return the ``(timestamp, value)`` series for one node/channel."""

        series = [
            (r.timestamp, r.value)
            for r in self.readings
            if r.node_id == node_id and r.channel == channel
        ]
        series.sort(key=lambda pair: pair[0])
        return series


# --- Load model ----------------------------------------------------------


def _all_power_nodes() -> tuple[str, ...]:
    nodes: list[str] = []
    for parent, children in POWER_HIERARCHY.items():
        if parent not in nodes:
            nodes.append(parent)
        for child in children:
            if child not in nodes and child not in POWER_HIERARCHY:
                nodes.append(child)
    return tuple(nodes)


def _leaf_power_kw(scenario_id: str, onset: int | None, node_id: str, t: int) -> float:
    """Baseline leaf power, with the only leaf-level trend being SC-12."""

    base = BASE_LOAD_KW[node_id]
    if scenario_id == "SC-12" and node_id == "CH-001" and onset is not None and t >= onset:
        # kW-per-ton rises ~0.0035 per day of degradation; cooling held flat.
        kw_per_ton = _CH001_BASE_KW_PER_TON + 0.0035 * (t - onset)
        return kw_per_ton * _CH001_TONS
    return base


def _unmetered_kw(scenario_id: str, onset: int | None, node_id: str, t: int) -> float:
    """Unmetered real power injected at a parent feed (SC-08 only)."""

    if (
        scenario_id == "SC-08"
        and node_id == "MCC-003"
        and onset is not None
        and t >= onset
    ):
        return _UNMETERED_KW
    return 0.0


def _node_power_kw(scenario_id: str, onset: int | None, node_id: str, t: int) -> float:
    children = POWER_HIERARCHY.get(node_id)
    if children is None:
        return _leaf_power_kw(scenario_id, onset, node_id, t)
    total = sum(
        _node_power_kw(scenario_id, onset, child, t) for child in children
    )
    total += _unmetered_kw(scenario_id, onset, node_id, t)
    return total


# --- Injection helpers ---------------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _reading(
    node_id: str, channel: str, value: float, unit: str, timestamp: datetime
) -> ElectricalReading:
    return ElectricalReading(
        node_id=node_id,
        channel=channel,
        value=value,
        unit=unit,
        timestamp=timestamp,
        provenance=_SYNTHETIC,
    )


def _inject_signal_channels(
    scenario_id: str, onset: int | None, t: int, ts: datetime
) -> list[ElectricalReading]:
    """Emit the scenario-specific measurement channels for one timestep."""

    out: list[ElectricalReading] = []
    after = onset is not None and t >= onset
    since = (t - onset) if (onset is not None and t >= onset) else 0

    if scenario_id == "SC-01":
        loading = 85.0 + (1.6 * since if after else 0.0)
        loading = _clamp(loading, 85.0, 118.0)
        top_oil = 60.0 + 0.55 * (loading - 85.0)
        # Hot-spot follows top-oil with a multi-day thermal lag.
        lag_since = max(0, since - 3)
        hot_spot = 78.0 + (1.4 * lag_since if after else 0.0)
        out.append(_reading("TX-001", "loading_percent", loading, "%", ts))
        out.append(_reading("TX-001", "top_oil_temperature_c", top_oil, "degC", ts))
        out.append(_reading("TX-001", "hot_spot_temperature_c", hot_spot, "degC", ts))
    elif scenario_id == "SC-02":
        sideband = -55.0 + (0.9 * since if after else 0.0)
        sideband = _clamp(sideband, -55.0, -18.0)
        out.append(_reading("M-003", "rotor_bar_sideband_db", sideband, "dB", ts))
    elif scenario_id == "SC-03":
        ripple = 4.0 + (0.22 * since if after else 0.0)
        heatsink = 55.0 + (0.5 * since if after else 0.0)
        out.append(_reading("VFD-002", "dc_link_ripple_v", ripple, "V", ts))
        out.append(_reading("VFD-002", "heatsink_temperature_c", heatsink, "degC", ts))
    elif scenario_id == "SC-04":
        resistance = 5.0 + (0.06 * since if after else 0.0)
        autonomy = 12.0 - (0.09 * since if after else 0.0)
        out.append(_reading("BATT-001", "internal_resistance_mohm", resistance, "mOhm", ts))
        out.append(_reading("BATT-001", "backup_autonomy_minutes", max(0.0, autonomy), "min", ts))
    elif scenario_id == "SC-05":
        for bus in ("UTIL-001", "SWGR-LV-001", "SWGR-LV-002"):
            # Instantaneous three-cycle sag on exactly the onset sample.
            v = 0.65 if (onset is not None and t == onset) else 1.0
            out.append(_reading(bus, "voltage_pu", v, "pu", ts))
    elif scenario_id == "SC-06":
        thd = 3.0 + (0.35 * since if after else 0.0)
        thd = _clamp(thd, 3.0, 7.0)
        out.append(_reading("SWGR-LV-002", "voltage_thd_percent", thd, "%", ts))
    elif scenario_id == "SC-07":
        kvar = 100.0 if after else 150.0
        pf = 0.93 if after else 0.98
        out.append(_reading("CAP-001", "delivered_kvar", kvar, "kvar", ts))
        out.append(_reading("SWGR-LV-002", "power_factor", pf, "ratio", ts))
    elif scenario_id == "SC-09":
        # Reports CLOSED throughout; current and downstream collapse at onset.
        out.append(_reading("CB-LV-005", "breaker_reported_closed", 1.0, "bool", ts))
        current = 0.0 if after else 42.0
        downstream_v = 0.0 if after else 1.0
        out.append(_reading("CB-LV-005", "through_current_a", current, "A", ts))
        out.append(_reading("PNL-LV-005", "voltage_pu", downstream_v, "pu", ts))
    elif scenario_id == "SC-10":
        util_v = 0.0 if after else 1.0
        ups_out = 1.0  # UPS bridges the gap throughout the event
        gen_out = _clamp(0.14 * since, 0.0, 1.0) if after else 0.0
        # ATS position: 0 = utility source, 1 = generator source.
        ats_pos = 1.0 if (after and since >= 1) else 0.0
        out.append(_reading("UTIL-001", "voltage_pu", util_v, "pu", ts))
        out.append(_reading("UPS-001", "output_voltage_pu", ups_out, "pu", ts))
        out.append(_reading("GEN-001", "output_voltage_pu", gen_out, "pu", ts))
        out.append(_reading("ATS-001", "source_position", ats_pos, "index", ts))
    elif scenario_id == "SC-11":
        # True feeder power for MCC-002 (unchanged); meter reads it with a slow
        # gain error of ~0.4 % per 30 days once drift begins.
        true_kw = _node_power_kw(scenario_id, onset, "MCC-002", t)
        gain = 1.0 + (0.004 * (since / 30.0) if after else 0.0)
        out.append(_reading("MTR-MCC-002", "meter_indicated_kw", true_kw * gain, "kW", ts))
    elif scenario_id == "SC-12":
        kw_per_ton = _CH001_BASE_KW_PER_TON + (0.0035 * since if after else 0.0)
        out.append(_reading("CH-001", "cooling_output_tons", _CH001_TONS, "ton", ts))
        out.append(_reading("CH-001", "kw_per_ton", kw_per_ton, "kW/ton", ts))

    return out


# --- Public API ----------------------------------------------------------


def generate(
    scenario_id: str = "SC-00",
    *,
    steps: int = SIM_STEPS,
    start: datetime = SIM_START,
    step: timedelta = SIM_STEP,
) -> GeneratedTelemetry:
    """Generate the telemetry record for ``scenario_id``.

    Parameters
    ----------
    scenario_id:
        A seeded scenario id (``"SC-00"`` .. ``"SC-12"``). ``"SC-00"`` is the
        untouched clean baseline; any other id injects that scenario's fault at
        its labelled ``onset_at``.
    steps, start, step:
        Simulation window controls; the defaults are the shared timebase every
        scenario's ground truth is pinned to.

    Raises
    ------
    KeyError
        If ``scenario_id`` is not a known seeded scenario.
    """

    scenario = scenario_by_id(scenario_id)  # raises KeyError on unknown id
    onset = sim_index(scenario.onset_at) if scenario.onset_at is not None else None

    readings: list[ElectricalReading] = []
    power_nodes = _all_power_nodes()

    for t in range(steps):
        ts = start + t * step
        for node_id in power_nodes:
            kw = _node_power_kw(scenario_id, onset, node_id, t)
            readings.append(_reading(node_id, "real_power_kw", kw, "kW", ts))
        readings.extend(_inject_signal_channels(scenario_id, onset, t, ts))

    return GeneratedTelemetry(
        scenario_id=scenario_id,
        start=start,
        step=step,
        steps=steps,
        readings=readings,
    )


def max_power_imbalance_kw(gen: GeneratedTelemetry) -> dict[str, float]:
    """Return, per metered parent, the max absolute parent/child power gap.

    For every parent feed in the hierarchy this walks each timestep, computes
    ``parent_power - sum(child_power)``, and keeps the largest absolute value.
    A healthy, fully-metered branch is ~0; an unmetered tap (SC-08) shows the
    tapped load as a persistent non-zero residual at that parent and nowhere
    else.
    """

    by_node_channel: dict[str, dict[datetime, float]] = {}
    for r in gen.readings:
        if r.channel != "real_power_kw":
            continue
        by_node_channel.setdefault(r.node_id, {})[r.timestamp] = r.value

    imbalance: dict[str, float] = {}
    for parent in metered_parents():
        parent_series = by_node_channel.get(parent, {})
        children = POWER_HIERARCHY[parent]
        worst = 0.0
        for ts, parent_kw in parent_series.items():
            child_sum = sum(
                by_node_channel.get(child, {}).get(ts, 0.0) for child in children
            )
            worst = max(worst, abs(parent_kw - child_sum))
        imbalance[parent] = worst
    return imbalance


def power_balance_breaks_at(
    gen: GeneratedTelemetry, tolerance_kw: float = 1e-6
) -> set[str]:
    """Return the set of parents whose power balance breaks beyond tolerance."""

    return {
        parent
        for parent, gap in max_power_imbalance_kw(gen).items()
        if gap > tolerance_kw
    }


__all__ = [
    "GeneratedTelemetry",
    "generate",
    "max_power_imbalance_kw",
    "power_balance_breaks_at",
]
