"""Deterministic, driver-based synthetic telemetry for the reference facility.

Design contract
---------------
Given ``(seed, scenario_id, start, end, interval_s)`` the output of
:func:`generate` is **byte-identical every time, on every machine**. There are
no wall-clock reads, no unseeded randomness, and no reliance on ``set`` / ``dict``
iteration order: every source of pseudo-randomness is a pure hash of
``(seed, node, channel, timestamp, ...)`` via :func:`hashlib.blake2b`, and every
loop iterates ordered lists.

Driver model
------------
Load is generated from **explicit physical drivers**, not as noise around a
target mean::

    P_node(t) = base_node
              + shift_factor(t)            * production_coefficient_node
              + ambient_response(T_amb(t)) * thermal_coefficient_node
              + occupancy_factor(t)        * occupancy_coefficient_node
              + noise(seed, node, t)

* ``shift_factor``    -- weekday two-shift schedule with ramp up/down; reduced
  at the weekend.
* ``T_amb``           -- deterministic diurnal sinusoid plus a seasonal term, a
  generic hot-climate profile (no city or country is named).
* ``occupancy_factor``-- office/occupancy diurnal profile, reduced at weekends.
* solar irradiance    -- a clear-sky curve with deterministic cloud events that
  drive ``PV-001`` and reduce the facility's net import.
* the capacitor bank  -- steps in/out on the *measured* power factor with
  hysteresis, so the emitted power factor is an **emergent result**, never a
  written value.

Physical consistency
--------------------
Only leaf loads carry driver noise. Bus, transformer and source powers are
**aggregated** from their children plus modelled losses, so the following hold
by construction (checked by the WP3-style tests):

* ``S = sqrt(3) * V_LL * I``  (with the same V and I that are emitted),
* ``P = S * PF`` and ``Q = sign * sqrt(S**2 - P**2)``,
* energy registers accumulate ``E += |P| * dt`` and are monotonically
  non-decreasing,
* ``P_parent == sum(P_children) + modelled_losses`` at every bus/transformer
  with complete child metering, where transformer loss is
  ``no_load_loss_kw + load_loss_kw * loading**2`` and cable loss is ``3*I**2*R``.

Scenarios
---------
``scenario_id='SC-00'`` is the clean baseline with no injected fault. Additional
scenario ids are introduced by a later work package; an **unknown scenario_id is
accepted and generates the clean baseline** (documented behaviour), so callers
never fail on a scenario this generator does not yet model.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from packages.canonical_electrical_model import DataProvenance, PhaseTag, Quality

from .channels import CHANNEL_UNITS, Channel
from .facility import (
    FacilityNode,
    NodeRole,
    ReferenceFacility,
    reference_facility,
)

_SQRT3 = math.sqrt(3.0)
_EPOCH = datetime(1970, 1, 1)

#: Scenario ids this generator models explicitly. Everything else is treated as
#: the clean baseline (see the module docstring).
CLEAN_BASELINE_SCENARIOS: frozenset[str] = frozenset({"SC-00"})

_PHASES: tuple[PhaseTag, ...] = (PhaseTag.A, PhaseTag.B, PhaseTag.C)
_PHASE_V_BIAS: dict[PhaseTag, float] = {
    PhaseTag.A: 0.0030,
    PhaseTag.B: -0.0012,
    PhaseTag.C: -0.0018,
}
_PHASE_I_BIAS: dict[PhaseTag, float] = {
    PhaseTag.A: 0.016,
    PhaseTag.B: -0.009,
    PhaseTag.C: -0.007,
}

_PROVENANCE = DataProvenance.SYNTHETIC

# Quality-injection proportions (deterministic, stable across runs at a seed).
_P_MISSING = 0.006
_P_STALE = 0.012


@dataclass(frozen=True, slots=True)
class TelemetryReading:
    """A single synthetic telemetry sample.

    Every reading is labelled :data:`DataProvenance.SYNTHETIC` and carries a
    :class:`~packages.canonical_electrical_model.Quality` flag.
    """

    node_id: str
    channel: Channel
    phase: PhaseTag | None
    value: float
    unit: str
    timestamp: datetime
    provenance: DataProvenance
    quality: Quality


# --------------------------------------------------------------------------- #
# Determinism helpers                                                         #
# --------------------------------------------------------------------------- #
def _u01(*parts: object) -> float:
    """A deterministic pseudo-random float in ``[0, 1)`` from the parts.

    Uses :func:`hashlib.blake2b` (not the salted built-in ``hash``) so the value
    is identical across processes and machines.
    """

    key = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2.0**64


def _signed(*parts: object) -> float:
    """A deterministic pseudo-random float in ``[-1, 1)`` from the parts."""

    return _u01(*parts) * 2.0 - 1.0


def _to_naive_utc(moment: datetime) -> datetime:
    """Normalise to a naive UTC datetime (tz-aware inputs are converted)."""

    if moment.tzinfo is not None:
        return moment.astimezone(UTC).replace(tzinfo=None)
    return moment


def _epoch_seconds(moment: datetime) -> int:
    """Whole seconds since the fixed epoch; tz-independent and deterministic."""

    return int((moment - _EPOCH).total_seconds())


def _timestamps(start: datetime, end: datetime, interval_s: int) -> list[datetime]:
    if interval_s <= 0:
        raise ValueError("interval_s must be positive")
    start = _to_naive_utc(start)
    end = _to_naive_utc(end)
    step = timedelta(seconds=interval_s)
    out: list[datetime] = []
    current = start
    while current < end:
        out.append(current)
        current += step
    return out


def _pwl(x: float, points: Sequence[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation over sorted ``(x, y)`` break-points."""

    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            frac = (x - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0)
    return points[-1][1]


def _hour_of_day(moment: datetime) -> float:
    return moment.hour + moment.minute / 60.0 + moment.second / 3600.0


# --------------------------------------------------------------------------- #
# Physical drivers (pure functions of the timestamp)                          #
# --------------------------------------------------------------------------- #
_SHIFT_WEEKDAY: tuple[tuple[float, float], ...] = (
    (0.0, 0.15),
    (5.0, 0.15),
    (7.0, 1.00),
    (13.5, 0.95),
    (14.0, 0.68),
    (14.5, 0.95),
    (21.0, 0.95),
    (23.0, 0.15),
    (24.0, 0.15),
)
_SHIFT_WEEKEND: tuple[tuple[float, float], ...] = (
    (0.0, 0.10),
    (7.0, 0.10),
    (9.0, 0.40),
    (17.0, 0.40),
    (20.0, 0.10),
    (24.0, 0.10),
)
_OCC_WEEKDAY: tuple[tuple[float, float], ...] = (
    (0.0, 0.05),
    (6.0, 0.05),
    (8.0, 0.90),
    (12.0, 0.90),
    (12.5, 0.60),
    (13.0, 0.90),
    (17.0, 0.90),
    (19.0, 0.20),
    (24.0, 0.05),
)
_OCC_WEEKEND: tuple[tuple[float, float], ...] = (
    (0.0, 0.02),
    (9.0, 0.05),
    (10.0, 0.20),
    (16.0, 0.20),
    (18.0, 0.05),
    (24.0, 0.02),
)


def shift_factor(moment: datetime) -> float:
    """Production shift intensity in ``[0, 1]`` for ``moment``.

    Weekdays run two shifts with a ramp up in the morning, a brief dip at the
    shift change, and a ramp down late evening. Weekends run a single reduced
    profile.
    """

    hour = _hour_of_day(moment)
    if moment.weekday() >= 5:
        return _pwl(hour, _SHIFT_WEEKEND)
    return _pwl(hour, _SHIFT_WEEKDAY)


def occupancy_factor(moment: datetime) -> float:
    """Occupancy intensity in ``[0, 1]`` for ``moment`` (lower at weekends)."""

    hour = _hour_of_day(moment)
    if moment.weekday() >= 5:
        return _pwl(hour, _OCC_WEEKEND)
    return _pwl(hour, _OCC_WEEKDAY)


def ambient_temperature_c(moment: datetime) -> float:
    """Deterministic ambient temperature (deg C): diurnal + seasonal terms.

    A generic hot-climate profile: mean ~29 C, a diurnal swing peaking mid
    afternoon, and a seasonal swing peaking around mid-year. No location is
    named; the numbers are synthetic.
    """

    hour = _hour_of_day(moment)
    day_of_year = moment.timetuple().tm_yday
    diurnal = 6.5 * math.cos(2.0 * math.pi * (hour - 15.0) / 24.0)
    seasonal = 7.0 * math.cos(2.0 * math.pi * (day_of_year - 200.0) / 365.0)
    return 29.0 + diurnal + seasonal


def ambient_response(temperature_c: float) -> float:
    """Cooling-demand response to ambient temperature, ``0`` below 22 C."""

    return max(0.0, temperature_c - 22.0) / 10.0


def clear_sky_irradiance(moment: datetime) -> float:
    """Clear-sky irradiance fraction in ``[0, 1]`` (0 at night)."""

    hour = _hour_of_day(moment)
    if hour <= 6.0 or hour >= 18.0:
        return 0.0
    day_of_year = moment.timetuple().tm_yday
    seasonal = 0.85 + 0.15 * math.cos(2.0 * math.pi * (day_of_year - 200.0) / 365.0)
    shape = math.sin(math.pi * (hour - 6.0) / 12.0)
    return max(0.0, shape**1.3 * seasonal)


def cloud_attenuation(moment: datetime, seed: int) -> float:
    """Deterministic cloud-cover attenuation in ``[0, 1]`` reducing PV output.

    Each day draws up to two cloud windows from a hash of ``(seed, day)``; a
    timestamp inside a window is attenuated by that window's depth.
    """

    hour = _hour_of_day(moment)
    day_of_year = moment.timetuple().tm_yday
    attenuation = 0.0
    for window in range(2):
        present = _u01(seed, "cloud_present", day_of_year, window)
        if present > 0.55:
            continue
        centre = 8.0 + 8.0 * _u01(seed, "cloud_centre", day_of_year, window)
        width = 0.75 + 1.75 * _u01(seed, "cloud_width", day_of_year, window)
        depth = 0.30 + 0.55 * _u01(seed, "cloud_depth", day_of_year, window)
        if abs(hour - centre) <= width:
            local = 1.0 - abs(hour - centre) / width
            attenuation = max(attenuation, depth * local)
    return min(1.0, attenuation)


# --------------------------------------------------------------------------- #
# Per-node electrical state for one timestep                                  #
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class _Electrical:
    p_kw: float
    q_kvar: float
    s_kva: float
    power_factor: float
    v_ll: float
    i_a: float
    loading_frac: float


def _capacity_kva(node: FacilityNode) -> float:
    if node.rated_kva > 0.0:
        return node.rated_kva
    if node.rated_kw > 0.0:
        return node.rated_kw / max(node.load_power_factor, 0.5)
    defaults = {
        "MSB-001": 2500.0,
        "MCC-001": 1100.0,
        "PP-001": 500.0,
        "UTIL-001": 4000.0,
        "PV-001": 320.0,
        "CAP-001": 250.0,
    }
    return defaults.get(node.node_id, 1000.0)


def _voltage(node: FacilityNode, loading_frac: float, seed: int, epoch: int) -> float:
    """Line-to-line voltage with mild load droop plus deterministic noise."""

    droop = 0.015 * min(loading_frac, 1.5)
    noise = 0.0009 * _signed(seed, node.node_id, "vll", epoch)
    return node.nominal_v_ll * (1.0 - droop + noise)


def _electrical_from_pq(
    node: FacilityNode, p_kw: float, q_kvar: float, seed: int, epoch: int
) -> _Electrical:
    """Derive the physically-consistent electrical quantities from P and Q."""

    s_kva = math.sqrt(p_kw * p_kw + q_kvar * q_kvar)
    loading_frac = s_kva / _capacity_kva(node) if _capacity_kva(node) > 0 else 0.0
    v_ll = _voltage(node, loading_frac, seed, epoch)
    i_a = (s_kva * 1000.0) / (_SQRT3 * v_ll) if v_ll > 0 else 0.0
    power_factor = (p_kw / s_kva) if s_kva > 1e-9 else 1.0
    return _Electrical(
        p_kw=p_kw,
        q_kvar=q_kvar,
        s_kva=s_kva,
        power_factor=power_factor,
        v_ll=v_ll,
        i_a=i_a,
        loading_frac=loading_frac,
    )


def _feeder_loss_kw(child: FacilityNode, elec: _Electrical) -> float:
    return 3.0 * elec.i_a * elec.i_a * child.feeder_r_ohm / 1000.0


def _feeder_loss_kvar(child: FacilityNode, elec: _Electrical) -> float:
    return 3.0 * elec.i_a * elec.i_a * child.feeder_x_ohm / 1000.0


def _leaf_power(node: FacilityNode, moment: datetime, seed: int) -> tuple[float, float]:
    """Active/reactive power of a leaf load from the explicit driver model."""

    epoch = _epoch_seconds(moment)
    t_amb = ambient_temperature_c(moment)
    p = (
        node.base_kw
        + shift_factor(moment) * node.production_coefficient_kw
        + ambient_response(t_amb) * node.thermal_coefficient_kw
        + occupancy_factor(moment) * node.occupancy_coefficient_kw
    )
    noise = 0.03 * node.base_kw * _signed(seed, node.node_id, "load", epoch)
    p = max(0.0, p + noise)
    pf = min(max(node.load_power_factor, 0.5), 0.999)
    q = p * math.tan(math.acos(pf))
    return p, q


# --------------------------------------------------------------------------- #
# Mutable state carried across timesteps                                      #
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class _RunState:
    temps: dict[tuple[str, Channel], float]
    energy_kwh: dict[str, float]
    runtime_h: dict[str, float]
    start_count: dict[str, int]
    running: dict[str, bool]
    cap_stage: int
    cap_ops: int
    last_good: dict[tuple[str, Channel, PhaseTag | None], float]


def _thermal_step(
    state: _RunState,
    key: tuple[str, Channel],
    target: float,
    tau_s: float,
    dt_s: float,
) -> float:
    prev = state.temps.get(key)
    if prev is None:
        state.temps[key] = target
        return target
    alpha = 1.0 - math.exp(-dt_s / tau_s)
    updated = prev + (target - prev) * alpha
    state.temps[key] = updated
    return updated


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #
def generate(
    *,
    seed: int,
    scenario_id: str,
    start: datetime,
    end: datetime,
    interval_s: int,
    variant: str = "base",
) -> list[TelemetryReading]:
    """Generate deterministic synthetic telemetry for the reference facility.

    Parameters
    ----------
    seed:
        Integer seed for the deterministic noise / cloud / quality streams.
    scenario_id:
        ``'SC-00'`` is the clean baseline. Any other (unknown) scenario id is
        accepted and also produces the clean baseline (see module docstring).
    start, end:
        Half-open ``[start, end)`` window. Naive datetimes are treated as UTC;
        tz-aware datetimes are converted to UTC. No wall-clock is ever read.
    interval_s:
        Sampling interval in seconds (must be positive).
    variant:
        Topology variant (``base``/``gen_backup``/``tie_alt``); unknown values
        fall back to ``base``.

    Returns
    -------
    list[TelemetryReading]
        Readings in a fully deterministic order (timestamp, then node, then
        channel, then phase).
    """

    # ``scenario_id`` is accepted for forward-compatibility; clean baseline is
    # produced for SC-00 and for every not-yet-modelled scenario id alike.
    _ = scenario_id in CLEAN_BASELINE_SCENARIOS

    facility: ReferenceFacility = reference_facility(variant)
    timestamps = _timestamps(start, end, interval_s)
    dt_s = float(interval_s)
    dt_h = interval_s / 3600.0

    state = _RunState(
        temps={},
        energy_kwh={},
        runtime_h={},
        start_count={},
        running={},
        cap_stage=0,
        cap_ops=0,
        last_good={},
    )

    readings: list[TelemetryReading] = []

    for moment in timestamps:
        elec = _solve_timestep(facility, moment, seed, state)
        _emit_timestep(facility, moment, seed, state, elec, dt_s, dt_h, readings)

    return readings


def _solve_timestep(
    facility: ReferenceFacility,
    moment: datetime,
    seed: int,
    state: _RunState,
) -> dict[str, _Electrical]:
    """Solve every node's P/Q/S/PF/V/I for one timestep, bottom-up."""

    epoch = _epoch_seconds(moment)
    elec: dict[str, _Electrical] = {}

    # 1. Leaf loads from the driver model.
    for node in facility.nodes:
        if node.role in (NodeRole.VFD_LOAD, NodeRole.LOAD):
            p, q = _leaf_power(node, moment, seed)
            elec[node.node_id] = _electrical_from_pq(node, p, q, seed, epoch)

    # 2. PV injection (negative active power, ~unity power factor).
    pv = _pv_node(facility)
    if pv is not None:
        irradiance = clear_sky_irradiance(moment) * (1.0 - cloud_attenuation(moment, seed))
        p_pv = -pv.pv_capacity_kw * irradiance
        elec[pv.node_id] = _electrical_from_pq(pv, p_pv, 0.0, seed, epoch)

    # 3. Load buses (MCC, PP): aggregate their leaf children + feeder losses.
    for node in facility.nodes:
        if node.role is NodeRole.BUS and node.node_id not in ("MSB-001",):
            p, q = _aggregate_children(facility, node.node_id, elec)
            elec[node.node_id] = _electrical_from_pq(node, p, q, seed, epoch)

    # 4. Main bus (MSB): aggregate MCC/PP/PV, run capacitor hysteresis, add cap.
    p_pre, q_pre = _aggregate_children(
        facility, "MSB-001", elec, exclude=("CAP-001",)
    )
    cap = facility.node("CAP-001")
    _step_capacitor(state, p_pre, q_pre, cap)
    q_cap = -state.cap_stage * cap.cap_stage_kvar
    elec[cap.node_id] = _electrical_from_pq(cap, 0.0, q_cap, seed, epoch)

    p_msb, q_msb = _aggregate_children(facility, "MSB-001", elec)
    msb = facility.node("MSB-001")
    elec[msb.node_id] = _electrical_from_pq(msb, p_msb, q_msb, seed, epoch)

    # 5. Transformer: child (MSB) + feeder loss + transformer core/copper loss.
    tx = facility.node("TX-001")
    p_child, q_child = _aggregate_children(facility, "TX-001", elec)
    s_msb = elec["MSB-001"].s_kva
    loading = s_msb / tx.rated_kva if tx.rated_kva > 0 else 0.0
    tx_loss = tx.no_load_loss_kw + tx.load_loss_kw * loading * loading
    q_mag = 0.06 * tx.rated_kva * (0.1 + 0.9 * loading * loading)
    elec[tx.node_id] = _electrical_from_pq(
        tx, p_child + tx_loss, q_child + q_mag, seed, epoch
    )

    # 6. Utility service: net import equals the transformer primary power.
    util = facility.node("UTIL-001")
    p_util, q_util = _aggregate_children(facility, "UTIL-001", elec)
    elec[util.node_id] = _electrical_from_pq(util, p_util, q_util, seed, epoch)

    return elec


def _pv_node(facility: ReferenceFacility) -> FacilityNode | None:
    for node in facility.nodes:
        if node.role is NodeRole.SOLAR_PV:
            return node
    return None


def _aggregate_children(
    facility: ReferenceFacility,
    parent_id: str,
    elec: dict[str, _Electrical],
    exclude: tuple[str, ...] = (),
) -> tuple[float, float]:
    """Sum child powers plus each child's feeder loss (active, reactive)."""

    p_total = 0.0
    q_total = 0.0
    for child in facility.children_of(parent_id):
        if child.node_id in exclude:
            continue
        child_elec = elec[child.node_id]
        p_total += child_elec.p_kw + _feeder_loss_kw(child, child_elec)
        q_total += child_elec.q_kvar + _feeder_loss_kvar(child, child_elec)
    return p_total, q_total


def _step_capacitor(
    state: _RunState, p_pre: float, q_pre: float, cap: FacilityNode
) -> None:
    """Step the capacitor bank in/out on measured PF with hysteresis.

    The stage decision uses the power factor *measured with the current stage*
    and only changes by one stage per timestep, so the emitted power factor is
    an emergent result of the stepping rather than a written value.
    """

    q_now = q_pre - state.cap_stage * cap.cap_stage_kvar
    s_now = math.sqrt(p_pre * p_pre + q_now * q_now)
    pf_now = (p_pre / s_now) if s_now > 1e-9 else 1.0

    if pf_now < 0.90 and state.cap_stage < cap.cap_max_stages:
        state.cap_stage += 1
        state.cap_ops += 1
    elif pf_now > 0.985 and state.cap_stage > 0:
        state.cap_stage -= 1
        state.cap_ops += 1


# --------------------------------------------------------------------------- #
# Emission                                                                    #
# --------------------------------------------------------------------------- #
def _quality_and_value(
    state: _RunState,
    node_id: str,
    channel: Channel,
    phase: PhaseTag | None,
    value: float,
    moment: datetime,
    seed: int,
) -> tuple[float, Quality]:
    """Apply deterministic STALE/MISSING injection and value carry-over."""

    key = (node_id, channel, phase)
    roll = _u01(seed, "quality", node_id, channel.value, str(phase), _epoch_seconds(moment))
    if roll < _P_MISSING:
        carried = state.last_good.get(key, value)
        return carried, Quality.MISSING
    if roll < _P_MISSING + _P_STALE:
        carried = state.last_good.get(key, value)
        return carried, Quality.STALE
    state.last_good[key] = value
    return value, Quality.GOOD


def _add(
    readings: list[TelemetryReading],
    state: _RunState,
    node_id: str,
    channel: Channel,
    phase: PhaseTag | None,
    value: float,
    moment: datetime,
    seed: int,
) -> None:
    out_value, quality = _quality_and_value(
        state, node_id, channel, phase, value, moment, seed
    )
    readings.append(
        TelemetryReading(
            node_id=node_id,
            channel=channel,
            phase=phase,
            value=out_value,
            unit=CHANNEL_UNITS[channel],
            timestamp=moment,
            provenance=_PROVENANCE,
            quality=quality,
        )
    )


def _emit_timestep(
    facility: ReferenceFacility,
    moment: datetime,
    seed: int,
    state: _RunState,
    elec: dict[str, _Electrical],
    dt_s: float,
    dt_h: float,
    readings: list[TelemetryReading],
) -> None:
    epoch = _epoch_seconds(moment)
    t_amb = ambient_temperature_c(moment)
    freq = 60.0 + 0.02 * math.sin(2.0 * math.pi * _hour_of_day(moment) / 24.0)

    for node in facility.nodes:
        e = elec[node.node_id]

        # Energy register: monotonically non-decreasing.
        state.energy_kwh[node.node_id] = (
            state.energy_kwh.get(node.node_id, 0.0) + abs(e.p_kw) * dt_h
        )

        # Core three-phase electrical channels.
        _add(readings, state, node.node_id, Channel.ACTIVE_POWER_KW, None, e.p_kw, moment, seed)
        _add(
            readings, state, node.node_id, Channel.REACTIVE_POWER_KVAR, None, e.q_kvar,
            moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.APPARENT_POWER_KVA, None, e.s_kva,
            moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.POWER_FACTOR, None, e.power_factor,
            moment, seed,
        )
        _add(readings, state, node.node_id, Channel.FREQUENCY_HZ, None, freq, moment, seed)
        _add(
            readings, state, node.node_id, Channel.ENERGY_ACTIVE_KWH, None,
            state.energy_kwh[node.node_id], moment, seed,
        )

        # Per-phase voltage and current with a small deterministic unbalance.
        v_phase: list[float] = []
        for phase in _PHASES:
            vph = e.v_ll * (
                1.0 + _PHASE_V_BIAS[phase]
                + 0.0008 * _signed(seed, node.node_id, "vph", phase.value, epoch)
            )
            v_phase.append(vph)
            _add(readings, state, node.node_id, Channel.VOLTAGE_LL_V, phase, vph, moment, seed)
        _add(readings, state, node.node_id, Channel.VOLTAGE_LL_V, None, e.v_ll, moment, seed)

        for phase in _PHASES:
            iph = e.i_a * (
                1.0 + _PHASE_I_BIAS[phase]
                + 0.006 * _signed(seed, node.node_id, "iph", phase.value, epoch)
            )
            _add(readings, state, node.node_id, Channel.CURRENT_A, phase, iph, moment, seed)
        _add(readings, state, node.node_id, Channel.CURRENT_A, None, e.i_a, moment, seed)

        v_mean = sum(v_phase) / 3.0
        unbalance = (max(v_phase) - min(v_phase)) / v_mean * 100.0 if v_mean > 0 else 0.0
        _add(
            readings, state, node.node_id, Channel.VOLTAGE_UNBALANCE_PCT, None, unbalance,
            moment, seed,
        )

        _emit_role_channels(node, moment, seed, state, elec, e, t_amb, dt_s, dt_h, readings)


def _emit_role_channels(
    node: FacilityNode,
    moment: datetime,
    seed: int,
    state: _RunState,
    elec: dict[str, _Electrical],
    e: _Electrical,
    t_amb: float,
    dt_s: float,
    dt_h: float,
    readings: list[TelemetryReading],
) -> None:
    epoch = _epoch_seconds(moment)

    if node.role is NodeRole.VFD_LOAD:
        vfd_loading = min(e.loading_frac, 1.2)
        v_thd = 2.0 + 4.0 * vfd_loading + 0.3 * _u01(seed, node.node_id, "vthd", epoch)
        i_tdd = 3.0 + 12.0 * vfd_loading + 0.5 * _u01(seed, node.node_id, "itdd", epoch)
        _add(readings, state, node.node_id, Channel.VOLTAGE_THD_PCT, None, v_thd, moment, seed)
        _add(readings, state, node.node_id, Channel.CURRENT_TDD_PCT, None, i_tdd, moment, seed)

        winding_target = t_amb + 65.0 * vfd_loading * vfd_loading
        bearing_target = t_amb + 25.0 * vfd_loading
        winding = _thermal_step(
            state, (node.node_id, Channel.WINDING_TEMPERATURE_C), winding_target, 900.0, dt_s
        )
        bearing = _thermal_step(
            state, (node.node_id, Channel.BEARING_TEMPERATURE_C), bearing_target, 1800.0, dt_s
        )
        _add(
            readings, state, node.node_id, Channel.WINDING_TEMPERATURE_C, None, winding,
            moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.BEARING_TEMPERATURE_C, None, bearing,
            moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.AMBIENT_TEMPERATURE_C, None,
            t_amb, moment, seed,
        )

        running_now = vfd_loading > 0.05
        was_running = state.running.get(node.node_id, running_now)
        if running_now and not was_running:
            state.start_count[node.node_id] = state.start_count.get(node.node_id, 0) + 1
        state.running[node.node_id] = running_now
        if running_now:
            state.runtime_h[node.node_id] = state.runtime_h.get(node.node_id, 0.0) + dt_h
        _add(
            readings, state, node.node_id, Channel.RUNTIME_HOURS, None,
            state.runtime_h.get(node.node_id, 0.0), moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.START_COUNT, None,
            float(state.start_count.get(node.node_id, 0)), moment, seed,
        )
        _add(readings, state, node.node_id, Channel.BREAKER_POSITION, None, 1.0, moment, seed)

    elif node.role is NodeRole.TRANSFORMER:
        loading = min(e.loading_frac, 1.2)
        top_oil_target = t_amb + 45.0 * loading * loading
        winding_target = t_amb + 60.0 * loading * loading
        top_oil = _thermal_step(
            state, (node.node_id, Channel.TOP_OIL_TEMPERATURE_C), top_oil_target, 7200.0, dt_s
        )
        winding = _thermal_step(
            state, (node.node_id, Channel.WINDING_TEMPERATURE_C), winding_target, 1200.0, dt_s
        )
        _add(
            readings, state, node.node_id, Channel.TOP_OIL_TEMPERATURE_C, None, top_oil,
            moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.WINDING_TEMPERATURE_C, None, winding,
            moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.AMBIENT_TEMPERATURE_C, None,
            t_amb, moment, seed,
        )

    elif node.role is NodeRole.BUS:
        loading = min(e.loading_frac, 1.2)
        panel_target = t_amb + 15.0 * loading
        panel = _thermal_step(
            state, (node.node_id, Channel.PANEL_TEMPERATURE_C), panel_target, 1200.0, dt_s
        )
        _add(readings, state, node.node_id, Channel.PANEL_TEMPERATURE_C, None, panel, moment, seed)
        v_thd = 1.5 + 2.5 * _bus_vfd_loading(node, elec) + 0.2 * _u01(
            seed, node.node_id, "busvthd", epoch
        )
        _add(readings, state, node.node_id, Channel.VOLTAGE_THD_PCT, None, v_thd, moment, seed)
        _add(readings, state, node.node_id, Channel.BREAKER_POSITION, None, 1.0, moment, seed)
        _add(
            readings, state, node.node_id, Channel.BREAKER_OPERATION_COUNT, None, 0.0,
            moment, seed,
        )

    elif node.role is NodeRole.CAPACITOR_BANK:
        _add(
            readings, state, node.node_id, Channel.CAPACITOR_STAGES, None,
            float(state.cap_stage), moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.BREAKER_OPERATION_COUNT, None,
            float(state.cap_ops), moment, seed,
        )
        _add(
            readings, state, node.node_id, Channel.BREAKER_POSITION, None,
            1.0 if state.cap_stage > 0 else 0.0, moment, seed,
        )
        panel_target = t_amb + 6.0
        panel = _thermal_step(
            state, (node.node_id, Channel.PANEL_TEMPERATURE_C), panel_target, 1500.0, dt_s
        )
        _add(readings, state, node.node_id, Channel.PANEL_TEMPERATURE_C, None, panel, moment, seed)

    elif node.role is NodeRole.SOLAR_PV:
        panel_target = t_amb + 12.0 * min(e.loading_frac, 1.2)
        panel = _thermal_step(
            state, (node.node_id, Channel.PANEL_TEMPERATURE_C), panel_target, 900.0, dt_s
        )
        _add(readings, state, node.node_id, Channel.PANEL_TEMPERATURE_C, None, panel, moment, seed)
        _add(
            readings, state, node.node_id, Channel.AMBIENT_TEMPERATURE_C, None,
            t_amb, moment, seed,
        )

    elif node.role is NodeRole.SOURCE:
        _add(
            readings, state, node.node_id, Channel.AMBIENT_TEMPERATURE_C, None,
            t_amb, moment, seed,
        )


def _bus_vfd_loading(node: FacilityNode, elec: dict[str, _Electrical]) -> float:
    """Mean VFD loading feeding a bus, for harmonic correlation."""

    child_id = node.node_id
    loadings = [
        elec[nid].loading_frac
        for nid in elec
        if nid.startswith("MTR-")
    ]
    if child_id == "MCC-001" and loadings:
        return sum(loadings) / len(loadings)
    return 0.2
