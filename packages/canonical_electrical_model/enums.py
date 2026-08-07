"""Canonical enumerations for the S3M ElectricalTwin domain model.

This module defines the controlled vocabularies shared across the electrical
digital-twin packages. Every enumeration is a ``str``-backed :class:`enum.Enum`
so that members serialise transparently to their canonical string token and
round-trip losslessly back to the member via ``EnumType(value)``.

Design rules enforced here:

* Every member's ``value`` is identical to its ``name``. This keeps wire
  formats, database columns and JSON payloads human-readable and stable.
* ``ValidationState.CALIBRATED`` is a *reserved* terminal state. It documents
  the existence of a calibrated model but **must never be assigned by any code
  path in this repository** -- calibration is an out-of-band, operator-governed
  act. A guard test enforces that no assignment statement anywhere in the code
  base references ``ValidationState.CALIBRATED``.
* ``EnergizationState.INDETERMINATE`` is the mandatory, non-negotiable result
  whenever switch state is ``SwitchState.UNKNOWN`` anywhere on the supply path.
  Energisation is never guessed.

All data described by these vocabularies is synthetic.
"""

from __future__ import annotations

from enum import Enum, unique


class _CanonicalStrEnum(str, Enum):
    """Base class for canonical string enumerations.

    Members declared with :func:`enum.auto` receive a ``value`` equal to their
    ``name``. Because the class also derives from ``str``, each member *is* its
    canonical string token, which makes serialisation and comparison against
    raw strings both natural and unambiguous.
    """

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):  # noqa: D401,N805
        """Return the member name so that ``value == name`` for every member."""
        return name

    def __str__(self) -> str:  # pragma: no cover - trivial
        """Render as the bare canonical token (e.g. ``"TRANSFORMER"``)."""
        return str(self.value)


# Local alias so member declarations read as ``= auto()`` while keeping the
# value-equals-name contract centralised in ``_CanonicalStrEnum``.
from enum import auto  # noqa: E402


@unique
class AssetType(_CanonicalStrEnum):
    """Physical or logical class of a modelled electrical asset."""

    UTILITY_INTAKE = auto()        # Point of common coupling with the supply network.
    MAIN_SWITCHGEAR = auto()       # Primary metal-enclosed switchgear assembly.
    TRANSFORMER = auto()           # Power/distribution transformer (any winding config).
    DISTRIBUTION_BOARD = auto()    # Panelboard distributing final circuits.
    MCC = auto()                   # Motor control centre.
    CIRCUIT_BREAKER = auto()       # Protective switching device with interruption rating.
    SWITCH_DISCONNECTOR = auto()   # Load-break / isolation switch (no interruption duty).
    BUSBAR = auto()                # Conductive bus tying feeders and loads together.
    CABLE = auto()                 # Power cable segment between two nodes.
    CAPACITOR_BANK = auto()        # Power-factor-correction capacitor bank.
    HARMONIC_FILTER = auto()       # Passive or active harmonic mitigation unit.
    GENERATOR = auto()             # Standby or prime engine/turbine generator set.
    ATS = auto()                   # Automatic transfer switch.
    UPS = auto()                   # Uninterruptible power supply.
    BATTERY_STRING = auto()        # Series/parallel battery string (UPS or storage).
    MOTOR = auto()                 # Rotating electrical machine acting as a load.
    VFD = auto()                   # Variable-frequency drive.
    PUMP = auto()                  # Pump driven by an electrical motor.
    CHILLER = auto()               # Refrigeration chiller unit.
    HVAC_UNIT = auto()             # Heating, ventilation and air-conditioning unit.
    SOLAR_ARRAY = auto()           # Photovoltaic array (DC generation source).
    INVERTER = auto()              # DC-to-AC power-conversion inverter.
    ENERGY_STORAGE = auto()        # Battery/other energy-storage system (AC coupled).
    PRODUCTION_LINE = auto()       # Aggregated process/production load.
    LIGHTING_PANEL = auto()        # Lighting distribution panel.
    GENERIC_LOAD = auto()          # Unclassified electrical load.
    METER = auto()                 # Revenue or sub-metering measurement point.


@unique
class SwitchState(_CanonicalStrEnum):
    """Discrete position/state of a switching device."""

    CLOSED = auto()      # Contacts closed; circuit made.
    OPEN = auto()        # Contacts open; circuit broken deliberately.
    TRIPPED = auto()     # Opened by protection following a fault or overload.
    RACKED_OUT = auto()  # Withdrawn from service position (isolated for work).
    UNKNOWN = auto()     # Position not observable; forces INDETERMINATE energisation.


@unique
class EnergizationState(_CanonicalStrEnum):
    """Whether and how a node is currently energised.

    ``INDETERMINATE`` is the mandatory result whenever any switch on the supply
    path reports :attr:`SwitchState.UNKNOWN`. Energisation is never guessed.
    """

    ENERGIZED_PRIMARY = auto()          # Supplied from the normal/primary source.
    ENERGIZED_BACKUP = auto()           # Supplied from a backup source (e.g. generator).
    ENERGIZED_UPS = auto()              # Supplied through a UPS (battery-backed) path.
    DE_ENERGIZED = auto()               # Confirmed no live source on the path.
    ISOLATED_FOR_MAINTENANCE = auto()   # Deliberately isolated and secured for work.
    INDETERMINATE = auto()              # Cannot be determined (unknown switch on path).


@unique
class SourceType(_CanonicalStrEnum):
    """Origin classification for a supply source."""

    UTILITY = auto()    # External utility/grid supply.
    GENERATOR = auto()  # On-site engine/turbine generation.
    UPS = auto()        # Uninterruptible power supply / battery-backed source.
    SOLAR = auto()      # Photovoltaic generation.
    STORAGE = auto()    # Energy-storage discharge.


@unique
class Criticality(_CanonicalStrEnum):
    """Business/operational criticality tier of a load or asset."""

    LIFE_SAFETY = auto()     # Loss endangers life (egress, fire, medical).
    CRITICAL = auto()        # Loss halts core operation with major impact.
    ESSENTIAL = auto()       # Important but tolerant of short interruption.
    NON_ESSENTIAL = auto()   # Deferrable / sheddable load.


@unique
class PowerQualityEventType(_CanonicalStrEnum):
    """Power-quality disturbance classes.

    Definitions align with the measurement methods of IEC 61000-4-30 and the
    disturbance categories of IEEE 1159.
    """

    SAG = auto()                    # rms voltage 0.1-0.9 pu for 0.5 cycle-1 min (IEEE 1159 dip).
    SWELL = auto()                  # rms voltage 1.1-1.8 pu for 0.5 cycle-1 min.
    INTERRUPTION_SHORT = auto()     # Supply < 0.1 pu, from 0.5 cycle up to 1 min.
    INTERRUPTION_LONG = auto()      # Supply < 0.1 pu sustained beyond 1 min.
    TRANSIENT_IMPULSIVE = auto()    # Unidirectional sub-cycle impulse (e.g. lightning/switching).
    TRANSIENT_OSCILLATORY = auto()  # Bidirectional decaying oscillatory transient.
    HARMONIC_DISTORTION = auto()    # Steady-state harmonic content (THD/individual harmonics).
    VOLTAGE_UNBALANCE = auto()      # Negative-sequence voltage unbalance between phases.
    FREQUENCY_DEVIATION = auto()    # Power-frequency excursion from nominal.
    FLICKER = auto()                # Perceptible luminance variation (P_st / P_lt).
    NOTCHING = auto()               # Periodic converter-commutation voltage notches.
    DC_OFFSET = auto()              # Direct-current component superimposed on the ac waveform.


@unique
class DataProvenance(_CanonicalStrEnum):
    """Origin/lineage classification for a data value."""

    SYNTHETIC = auto()           # Generated by this project's synthetic data tooling.
    SIMULATED = auto()           # Produced by a physics/behavioural simulation.
    OPERATOR_ENTERED = auto()    # Manually entered by an operator.
    NAMEPLATE = auto()           # Transcribed from equipment nameplate/datasheet.
    CUSTOMER_HISTORIAN = auto()  # Sourced from the customer's process historian.
    CUSTOMER_METER = auto()      # Sourced from the customer's metering infrastructure.
    CUSTOMER_LIMS = auto()       # Sourced from the customer's laboratory information system.
    THIRD_PARTY = auto()         # Supplied by an external third party (not the customer).


#: Provenance members that represent data originating from the customer.
_CUSTOMER_SOURCED: frozenset[DataProvenance] = frozenset(
    {
        DataProvenance.CUSTOMER_HISTORIAN,
        DataProvenance.CUSTOMER_METER,
        DataProvenance.CUSTOMER_LIMS,
    }
)


def is_customer_sourced(p: DataProvenance) -> bool:
    """Return ``True`` when *p* denotes data originating from the customer.

    Only the ``CUSTOMER_*`` provenances are customer-sourced. ``THIRD_PARTY``
    data comes from an external party rather than the customer, and the
    remaining provenances are produced or entered inside the project.
    """
    return DataProvenance(p) in _CUSTOMER_SOURCED


@unique
class ValidationState(_CanonicalStrEnum):
    """Maturity/trust level of a modelled quantity.

    ``CALIBRATED`` is a reserved terminal state describing a model that has been
    formally calibrated against measurements. It **must never be assigned by any
    code path in this repository**; only an out-of-band, operator-governed
    calibration process may set it. A guard test enforces this invariant.
    """

    PRELIMINARY = auto()  # Initial estimate; not yet cross-checked.
    ESTIMATED = auto()    # Derived from models/heuristics.
    BENCHMARKED = auto()  # Compared against reference data or peer assets.
    CALIBRATED = auto()   # Reserved: never assigned by repository code paths.


@unique
class HealthBand(_CanonicalStrEnum):
    """Coarse asset-health classification band."""

    HEALTHY = auto()            # No adverse indicators.
    WATCH = auto()              # Minor indicators; monitor.
    DEGRADED = auto()           # Clear degradation; plan intervention.
    CRITICAL = auto()           # Imminent failure risk; act now.
    INSUFFICIENT_DATA = auto()  # Not enough data to classify.


@unique
class ApprovalStatus(_CanonicalStrEnum):
    """Review/approval lifecycle state of an artefact."""

    DRAFT = auto()                    # Author-editable; not submitted.
    PENDING_OPERATOR_REVIEW = auto()  # Submitted; awaiting operator review.
    APPROVED = auto()                 # Accepted by the reviewer.
    REJECTED = auto()                 # Declined by the reviewer.
    EXPIRED = auto()                  # Approval window lapsed.


@unique
class DataQuality(_CanonicalStrEnum):
    """Per-sample data-quality flag."""

    GOOD = auto()          # Passed all quality checks.
    UNCERTAIN = auto()     # Plausible but with reduced confidence.
    STALE = auto()         # Older than the acceptable freshness window.
    MISSING = auto()       # Expected value absent.
    OUT_OF_RANGE = auto()  # Outside physically/technically valid range.
    SUSPECT = auto()       # Fails a consistency/plausibility rule.


@unique
class PhaseTag(_CanonicalStrEnum):
    """Electrical-phase association for a measurement or quantity."""

    A = auto()          # Phase A (L1).
    B = auto()          # Phase B (L2).
    C = auto()          # Phase C (L3).
    N = auto()          # Neutral.
    AGGREGATE = auto()  # Three-phase aggregate / not phase-specific.


@unique
class TelemetryChannel(_CanonicalStrEnum):
    """Canonical measurement channel identifiers with implied units.

    The unit is encoded in the token suffix where applicable (e.g. ``_KW``,
    ``_C``, ``_PCT``) so that a channel and its unit stay inseparable.
    """

    VOLTAGE_LN = auto()                      # Line-to-neutral voltage (V).
    VOLTAGE_LL = auto()                      # Line-to-line voltage (V).
    CURRENT = auto()                         # Line current (A).
    ACTIVE_POWER_KW = auto()                 # Active power (kW).
    REACTIVE_POWER_KVAR = auto()             # Reactive power (kvar).
    APPARENT_POWER_KVA = auto()              # Apparent power (kVA).
    POWER_FACTOR = auto()                    # Displacement/true power factor (ratio).
    FREQUENCY_HZ = auto()                    # Power-system frequency (Hz).
    ENERGY_KWH = auto()                      # Cumulative active energy (kWh).
    DEMAND_KVA = auto()                      # Demand interval apparent power (kVA).
    VOLTAGE_THD_PCT = auto()                 # Voltage total harmonic distortion (%).
    CURRENT_TDD_PCT = auto()                 # Current total demand distortion (%).
    HARMONIC_MAGNITUDE = auto()              # Individual harmonic magnitude (per-order).
    VOLTAGE_UNBALANCE_PCT = auto()           # Voltage unbalance (%).
    CURRENT_UNBALANCE_PCT = auto()           # Current unbalance (%).
    WINDING_TEMPERATURE_C = auto()           # Transformer/machine winding temperature (deg C).
    TOP_OIL_TEMPERATURE_C = auto()           # Transformer top-oil temperature (deg C).
    AMBIENT_TEMPERATURE_C = auto()           # Ambient air temperature (deg C).
    PANEL_TEMPERATURE_C = auto()             # Enclosure/panel internal temperature (deg C).
    MOTOR_TEMPERATURE_C = auto()             # Motor body/winding temperature (deg C).
    BEARING_TEMPERATURE_C = auto()           # Bearing temperature (deg C).
    VIBRATION_MM_S_RMS = auto()              # Vibration velocity, rms (mm/s).
    BREAKER_POSITION = auto()                # Breaker position status (open/closed).
    OPERATION_COUNT = auto()                 # Cumulative operating-cycle count.
    RUNTIME_HOURS = auto()                   # Cumulative running hours (h).
    STARTS_COUNT = auto()                    # Cumulative start count.
    TRIP_COUNT = auto()                      # Cumulative protective-trip count.
    BATTERY_VOLTAGE = auto()                 # Battery terminal/string voltage (V).
    BATTERY_INTERNAL_RESISTANCE_MOHM = auto()  # Battery internal resistance (milliohm).
    BATTERY_TEMPERATURE_C = auto()           # Battery temperature (deg C).
    STATE_OF_CHARGE_PCT = auto()             # Battery/storage state of charge (%).
    FUEL_LEVEL_PCT = auto()                  # Generator fuel level (%).
    IRRADIANCE_W_M2 = auto()                 # Plane-of-array solar irradiance (W/m^2).
    DC_VOLTAGE = auto()                      # DC-side voltage (V).
    DC_CURRENT = auto()                      # DC-side current (A).


__all__ = [
    "AssetType",
    "SwitchState",
    "EnergizationState",
    "SourceType",
    "Criticality",
    "PowerQualityEventType",
    "DataProvenance",
    "is_customer_sourced",
    "ValidationState",
    "HealthBand",
    "ApprovalStatus",
    "DataQuality",
    "PhaseTag",
    "TelemetryChannel",
]
