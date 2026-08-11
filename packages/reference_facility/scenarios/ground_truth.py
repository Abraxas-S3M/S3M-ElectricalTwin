"""Machine-readable ground truth for a seeded scenario.

Every scenario injects (at most) one fault into the reference telemetry and
carries the exact label a benchmark needs to score a detector: where the fault
is, when it starts, the earliest point a correct detector could fire, which
detector *should* fire, and — critically — which detectors must stay silent.

That last field, :attr:`ScenarioGroundTruth.should_not_trigger`, is the
false-positive guard. Without it a detector that fires on everything would
score perfectly on recall; with it, firing on the wrong scenario is a
measurable error. It is what turns "it looked right" into a falsifiable claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from packages.canonical_electrical_model.enums import Severity


class FaultCategory(str, Enum):
    """Kind of fault a scenario injects. ``NONE`` is the clean control."""

    NONE = "NONE"
    THERMAL_OVERLOAD = "THERMAL_OVERLOAD"
    ROTOR_BAR_DEGRADATION = "ROTOR_BAR_DEGRADATION"
    VFD_DC_LINK_DEGRADATION = "VFD_DC_LINK_DEGRADATION"
    BATTERY_AGING = "BATTERY_AGING"
    VOLTAGE_SAG = "VOLTAGE_SAG"
    HARMONIC_DISTORTION = "HARMONIC_DISTORTION"
    CAPACITOR_STEP_FAILURE = "CAPACITOR_STEP_FAILURE"
    UNMETERED_LOAD = "UNMETERED_LOAD"
    POSITION_INCONSISTENCY = "POSITION_INCONSISTENCY"
    SOURCE_TRANSFER = "SOURCE_TRANSFER"
    METER_DRIFT = "METER_DRIFT"
    EFFICIENCY_DEGRADATION = "EFFICIENCY_DEGRADATION"


class Detector(str, Enum):
    """The named detectors a scenario can expect (or must not) fire.

    These are the analytic algorithms later work packages implement. The
    scenario ground truth references them by name so the WP3 benchmark can be
    scored automatically rather than by eye.
    """

    THERMAL_CAPACITY = "thermal_capacity_detector"
    MOTOR_CURRENT_SIGNATURE = "motor_current_signature_detector"
    VFD_DC_LINK = "vfd_dc_link_detector"
    BATTERY_HEALTH = "battery_health_detector"
    VOLTAGE_SAG = "voltage_sag_detector"
    HARMONIC_THD = "harmonic_thd_detector"
    CAPACITOR_BANK = "capacitor_bank_detector"
    UNMETERED_LOAD = "unmetered_load_detector"
    POSITION_CONSISTENCY = "position_consistency_detector"
    SOURCE_TRANSFER = "source_transfer_detector"
    METER_DRIFT = "meter_drift_detector"
    EFFICIENCY_TREND = "efficiency_trend_detector"


ALL_DETECTORS: tuple[Detector, ...] = tuple(Detector)


def all_detectors_except(*expected: Detector) -> tuple[Detector, ...]:
    """Return every detector except those in ``expected``.

    This builds the ``should_not_trigger`` guard for a single-fault scenario:
    exactly one detector should fire, so every *other* detector is expected to
    stay silent.
    """

    excluded = set(expected)
    return tuple(d for d in ALL_DETECTORS if d not in excluded)


@dataclass(frozen=True)
class ScenarioGroundTruth:
    """The label a benchmark scores a scenario against.

    Attributes
    ----------
    scenario_id:
        Stable id, e.g. ``"SC-08"``.
    fault_node_ids:
        Facility node ids carrying the injected fault. Empty for the control.
    fault_category:
        The kind of fault injected (:class:`FaultCategory`).
    onset_at:
        When the fault begins in the telemetry. ``None`` for the clean control.
    detectable_from:
        Earliest timestamp at which a correct detector could legitimately fire.
        Always at or after ``onset_at`` — a detector cannot see a fault before
        it exists. ``None`` for the clean control.
    expected_detector:
        The detector that *should* catch this fault. ``None`` for the control,
        where every detector must stay silent.
    should_not_trigger:
        Detectors that must stay silent — the false-positive guard. Never
        empty: even the expected fault must not trip unrelated detectors.
    severity:
        Operator-facing severity of the (correctly detected) condition.
    narrative:
        Plain-language description usable directly in a demonstration.
    """

    scenario_id: str
    fault_node_ids: tuple[str, ...]
    fault_category: FaultCategory
    onset_at: datetime | None
    detectable_from: datetime | None
    expected_detector: Detector | None
    should_not_trigger: tuple[Detector, ...]
    severity: Severity
    narrative: str

    def is_control(self) -> bool:
        """Return ``True`` for the clean baseline (no injected fault)."""

        return self.fault_category is FaultCategory.NONE


__all__ = [
    "FaultCategory",
    "Detector",
    "ALL_DETECTORS",
    "all_detectors_except",
    "ScenarioGroundTruth",
]
