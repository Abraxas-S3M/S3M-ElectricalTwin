"""The thirteen seeded scenarios and :func:`all_scenarios`.

Each scenario pins its ``onset_at`` and ``detectable_from`` to exact sample
indices on the shared simulation timebase (see
:mod:`packages.reference_facility.facility`), so the telemetry generator can
inject the fault at precisely the labelled moment. The three differentiating
cases — SC-08 (unmetered load), SC-09 (position inconsistency) and SC-11
(meter drift) — are the ones WP3 scores most exactly, so their node ids and
timing are chosen to be unambiguous.
"""

from __future__ import annotations

from datetime import datetime

from packages.canonical_electrical_model.enums import Severity

from ..facility import sim_timestamp
from .ground_truth import (
    ALL_DETECTORS,
    Detector,
    FaultCategory,
    ScenarioGroundTruth,
    all_detectors_except,
)


def _t(day_index: int) -> datetime:
    return sim_timestamp(day_index)


_SC00 = ScenarioGroundTruth(
    scenario_id="SC-00",
    fault_node_ids=(),
    fault_category=FaultCategory.NONE,
    onset_at=None,
    detectable_from=None,
    expected_detector=None,
    should_not_trigger=ALL_DETECTORS,
    severity=Severity.INFO,
    narrative=(
        "Clean baseline. The facility runs healthy for the full window with no "
        "injected fault. This is the mandatory control: every detector must "
        "stay silent, so any alarm here is by definition a false positive."
    ),
)

_SC01 = ScenarioGroundTruth(
    scenario_id="SC-01",
    fault_node_ids=("TX-001",),
    fault_category=FaultCategory.THERMAL_OVERLOAD,
    onset_at=_t(30),
    detectable_from=_t(33),
    expected_detector=Detector.THERMAL_CAPACITY,
    should_not_trigger=all_detectors_except(Detector.THERMAL_CAPACITY),
    severity=Severity.HIGH,
    narrative=(
        "Transformer TX-001 loading climbs past 100 % of nameplate. Top-oil "
        "temperature rises first, then the hot-spot follows with a thermal lag "
        "of a few days, eventually breaching its limit."
    ),
)

_SC02 = ScenarioGroundTruth(
    scenario_id="SC-02",
    fault_node_ids=("M-003",),
    fault_category=FaultCategory.ROTOR_BAR_DEGRADATION,
    onset_at=_t(20),
    detectable_from=_t(45),
    expected_detector=Detector.MOTOR_CURRENT_SIGNATURE,
    should_not_trigger=all_detectors_except(Detector.MOTOR_CURRENT_SIGNATURE),
    severity=Severity.MEDIUM,
    narrative=(
        "Motor M-003 develops rotor-bar degradation. Current sidebands at "
        "f_s +/- 2*s*f_s grow slowly over weeks; only once the sideband "
        "amplitude clears the noise floor can a signature detector call it."
    ),
)

_SC03 = ScenarioGroundTruth(
    scenario_id="SC-03",
    fault_node_ids=("VFD-002",),
    fault_category=FaultCategory.VFD_DC_LINK_DEGRADATION,
    onset_at=_t(25),
    detectable_from=_t(30),
    expected_detector=Detector.VFD_DC_LINK,
    should_not_trigger=all_detectors_except(Detector.VFD_DC_LINK),
    severity=Severity.MEDIUM,
    narrative=(
        "Drive VFD-002 shows rising DC-link ripple as its bus capacitors age; "
        "heatsink temperature climbs in step. Left alone this ends in a "
        "nuisance trip or capacitor failure."
    ),
)

_SC04 = ScenarioGroundTruth(
    scenario_id="SC-04",
    fault_node_ids=("BATT-001",),
    fault_category=FaultCategory.BATTERY_AGING,
    onset_at=_t(15),
    detectable_from=_t(40),
    expected_detector=Detector.BATTERY_HEALTH,
    should_not_trigger=all_detectors_except(Detector.BATTERY_HEALTH),
    severity=Severity.MEDIUM,
    narrative=(
        "UPS battery string BATT-001 ages: internal resistance rises and "
        "backup autonomy falls. The ride-through the site believes it has is "
        "quietly shrinking."
    ),
)

_SC05 = ScenarioGroundTruth(
    scenario_id="SC-05",
    fault_node_ids=("UTIL-001", "SWGR-LV-001", "SWGR-LV-002"),
    fault_category=FaultCategory.VOLTAGE_SAG,
    onset_at=_t(40),
    detectable_from=_t(40),
    expected_detector=Detector.VOLTAGE_SAG,
    should_not_trigger=all_detectors_except(Detector.VOLTAGE_SAG),
    severity=Severity.HIGH,
    narrative=(
        "A utility-side voltage sag drops to 0.65 pu for three cycles and "
        "propagates to every energized LV bus. It is instantaneous and must be "
        "caught on the sample it occurs."
    ),
)

_SC06 = ScenarioGroundTruth(
    scenario_id="SC-06",
    fault_node_ids=("SWGR-LV-002",),
    fault_category=FaultCategory.HARMONIC_DISTORTION,
    onset_at=_t(20),
    detectable_from=_t(28),
    expected_detector=Detector.HARMONIC_THD,
    should_not_trigger=all_detectors_except(Detector.HARMONIC_THD),
    severity=Severity.MEDIUM,
    narrative=(
        "The variable-frequency-drive group loads SWGR-LV-002 heavily enough "
        "that bus voltage THD creeps past the IEEE 519 limit as duty rises."
    ),
)

_SC07 = ScenarioGroundTruth(
    scenario_id="SC-07",
    fault_node_ids=("CAP-001",),
    fault_category=FaultCategory.CAPACITOR_STEP_FAILURE,
    onset_at=_t(35),
    detectable_from=_t(36),
    expected_detector=Detector.CAPACITOR_BANK,
    should_not_trigger=all_detectors_except(Detector.CAPACITOR_BANK),
    severity=Severity.MEDIUM,
    narrative=(
        "One step of capacitor bank CAP-001 fails. Delivered kvar drops in a "
        "discrete step and the site power factor declines and stops recovering."
    ),
)

_SC08 = ScenarioGroundTruth(
    scenario_id="SC-08",
    fault_node_ids=("MCC-003",),
    fault_category=FaultCategory.UNMETERED_LOAD,
    onset_at=_t(30),
    detectable_from=_t(32),
    expected_detector=Detector.UNMETERED_LOAD,
    should_not_trigger=all_detectors_except(Detector.UNMETERED_LOAD),
    severity=Severity.MEDIUM,
    narrative=(
        "A new load is tapped onto the MCC-003 branch with no sub-meter of its "
        "own. The MCC-003 feed meter reads more than the sum of its child "
        "meters — a parent/child power-balance gap that only exists at "
        "MCC-003. Generic monitoring, which trusts each meter in isolation, "
        "cannot see it."
    ),
)

_SC09 = ScenarioGroundTruth(
    scenario_id="SC-09",
    fault_node_ids=("CB-LV-005",),
    fault_category=FaultCategory.POSITION_INCONSISTENCY,
    onset_at=_t(25),
    detectable_from=_t(25),
    expected_detector=Detector.POSITION_CONSISTENCY,
    should_not_trigger=all_detectors_except(Detector.POSITION_CONSISTENCY),
    severity=Severity.HIGH,
    narrative=(
        "Breaker CB-LV-005 reports CLOSED, yet the current through it is zero "
        "and everything downstream is dead. The reported position contradicts "
        "the physics; a consistency check catches it the instant it appears."
    ),
)

_SC10 = ScenarioGroundTruth(
    scenario_id="SC-10",
    fault_node_ids=("UTIL-001", "UPS-001", "GEN-001", "ATS-001"),
    fault_category=FaultCategory.SOURCE_TRANSFER,
    onset_at=_t(50),
    detectable_from=_t(50),
    expected_detector=Detector.SOURCE_TRANSFER,
    should_not_trigger=all_detectors_except(Detector.SOURCE_TRANSFER),
    severity=Severity.LOW,
    narrative=(
        "The utility is lost. UPS-001 bridges the gap, GEN-001 starts, ATS-001 "
        "transfers to the generator and load is restored. This is a correct, "
        "coordinated ride-through — the transfer detector should recognize it "
        "as an orchestrated event and the sag detector must NOT flag the "
        "momentary interruption as a fault."
    ),
)

_SC11 = ScenarioGroundTruth(
    scenario_id="SC-11",
    fault_node_ids=("MTR-MCC-002",),
    fault_category=FaultCategory.METER_DRIFT,
    onset_at=_t(10),
    detectable_from=_t(55),
    expected_detector=Detector.METER_DRIFT,
    should_not_trigger=all_detectors_except(Detector.METER_DRIFT),
    severity=Severity.LOW,
    narrative=(
        "Meter MTR-MCC-002 develops a slow gain error of about 0.4 % per "
        "month. Each reading is plausible on its own; only the accumulating "
        "divergence from the true feeder power over many weeks reveals the "
        "drift. No single sample looks wrong."
    ),
)

_SC12 = ScenarioGroundTruth(
    scenario_id="SC-12",
    fault_node_ids=("CH-001",),
    fault_category=FaultCategory.EFFICIENCY_DEGRADATION,
    onset_at=_t(20),
    detectable_from=_t(40),
    expected_detector=Detector.EFFICIENCY_TREND,
    should_not_trigger=all_detectors_except(Detector.EFFICIENCY_TREND),
    severity=Severity.MEDIUM,
    narrative=(
        "Chiller CH-001 uses steadily more kW per unit of cooling delivered as "
        "fouling and refrigerant issues accumulate. The trend is gradual and "
        "only an efficiency baseline over time exposes it."
    ),
)


_SCENARIOS: tuple[ScenarioGroundTruth, ...] = (
    _SC00,
    _SC01,
    _SC02,
    _SC03,
    _SC04,
    _SC05,
    _SC06,
    _SC07,
    _SC08,
    _SC09,
    _SC10,
    _SC11,
    _SC12,
)


def all_scenarios() -> list[ScenarioGroundTruth]:
    """Return the full ordered list of seeded scenarios (SC-00 .. SC-12)."""

    return list(_SCENARIOS)


def scenario_by_id(scenario_id: str) -> ScenarioGroundTruth:
    """Return the scenario with ``scenario_id`` or raise :class:`KeyError`."""

    for scenario in _SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise KeyError(f"unknown scenario id: {scenario_id!r}")


def scenario_ids() -> tuple[str, ...]:
    """Return the ordered tuple of scenario ids."""

    return tuple(s.scenario_id for s in _SCENARIOS)


__all__ = [
    "all_scenarios",
    "scenario_by_id",
    "scenario_ids",
]
