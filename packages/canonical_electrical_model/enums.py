"""Enumerations shared across the canonical electrical model.

All enums are string-valued so they serialise to stable, human-readable JSON
and round-trip cleanly back to a member via ``EnumType(value)``. Every member's
value is identical to its name.

All data described by these vocabularies is synthetic.
"""

from __future__ import annotations

from enum import Enum


class AssetType(str, Enum):
    """Kind of electrical asset a node represents."""

    UTILITY_SERVICE = "UTILITY_SERVICE"
    GENERATOR = "GENERATOR"
    UPS = "UPS"
    TRANSFORMER = "TRANSFORMER"
    SWITCHGEAR = "SWITCHGEAR"
    SWITCHBOARD = "SWITCHBOARD"
    PANELBOARD = "PANELBOARD"
    BUSBAR = "BUSBAR"
    BUS = "BUS"
    BREAKER = "BREAKER"
    TIE_BREAKER = "TIE_BREAKER"
    DISCONNECT = "DISCONNECT"
    FEEDER = "FEEDER"
    CAPACITOR_BANK = "CAPACITOR_BANK"
    MOTOR = "MOTOR"
    LOAD = "LOAD"
    METER = "METER"
    JUNCTION = "JUNCTION"
    OTHER = "OTHER"


class EdgeKind(str, Enum):
    """Kind of connection an edge represents."""

    FEEDER = "FEEDER"
    TIE = "TIE"
    TRANSFORMER_WINDING = "TRANSFORMER_WINDING"
    SOURCE_CONNECTION = "SOURCE_CONNECTION"


class SwitchState(str, Enum):
    """Live switching state of an edge.

    This is an *observed/reported* state, never a command. ``UNKNOWN`` is a
    first-class value: topology must validate even when the state of a switch
    cannot be determined.

    Conduction, for the topology solver, is decided by this rule:

    * ``CLOSED`` is the only conducting state.
    * ``OPEN``, ``INTERMEDIATE``, ``TRIPPED`` and ``RACKED_OUT`` are all
      *determinate non-conducting* states -- they are known positions that do
      not carry current, so they never introduce indeterminacy downstream.
    * ``UNKNOWN`` is the only indeterminate state: it *might* conduct, so a node
      reachable only through an ``UNKNOWN`` switch is reported as
      ``INDETERMINATE``.
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    INTERMEDIATE = "INTERMEDIATE"
    TRIPPED = "TRIPPED"
    RACKED_OUT = "RACKED_OUT"
    UNKNOWN = "UNKNOWN"


class Criticality(str, Enum):
    """Operational criticality of an asset."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    LIFE_SAFETY = "LIFE_SAFETY"


class SourceType(str, Enum):
    """Kind of electrical source."""

    UTILITY = "UTILITY"
    GENERATOR = "GENERATOR"
    UPS = "UPS"
    BATTERY = "BATTERY"
    SOLAR_PV = "SOLAR_PV"
    WIND = "WIND"
    COGENERATION = "COGENERATION"
    OTHER = "OTHER"


class EnergizationState(str, Enum):
    """Resolved energization state of a node.

    ``INDETERMINATE`` is a first-class value: it is reported when a node's
    energization cannot be decided (reachable only through an ``UNKNOWN``
    switch) and is never collapsed into energized or de-energized by
    assumption.
    """

    ENERGIZED_PRIMARY = "ENERGIZED_PRIMARY"
    ENERGIZED_BACKUP = "ENERGIZED_BACKUP"
    ENERGIZED_UPS = "ENERGIZED_UPS"
    DE_ENERGIZED = "DE_ENERGIZED"
    ISOLATED_FOR_MAINTENANCE = "ISOLATED_FOR_MAINTENANCE"
    INDETERMINATE = "INDETERMINATE"


class TelemetryChannel(str, Enum):
    """Measured or derived telemetry channel for a monitored point.

    Controlled vocabulary naming the physical quantity a reading carries. It is
    a label only; it never encodes an engineering limit or a plausibility
    bound.
    """

    VOLTAGE_LN = "VOLTAGE_LN"
    VOLTAGE_LL = "VOLTAGE_LL"
    CURRENT = "CURRENT"
    ACTIVE_POWER_KW = "ACTIVE_POWER_KW"
    REACTIVE_POWER_KVAR = "REACTIVE_POWER_KVAR"
    APPARENT_POWER_KVA = "APPARENT_POWER_KVA"
    POWER_FACTOR = "POWER_FACTOR"
    FREQUENCY_HZ = "FREQUENCY_HZ"
    ENERGY_KWH = "ENERGY_KWH"
    DEMAND_KVA = "DEMAND_KVA"
    VOLTAGE_THD_PCT = "VOLTAGE_THD_PCT"
    CURRENT_TDD_PCT = "CURRENT_TDD_PCT"
    HARMONIC_MAGNITUDE = "HARMONIC_MAGNITUDE"
    VOLTAGE_UNBALANCE_PCT = "VOLTAGE_UNBALANCE_PCT"
    CURRENT_UNBALANCE_PCT = "CURRENT_UNBALANCE_PCT"
    WINDING_TEMPERATURE_C = "WINDING_TEMPERATURE_C"
    TOP_OIL_TEMPERATURE_C = "TOP_OIL_TEMPERATURE_C"
    AMBIENT_TEMPERATURE_C = "AMBIENT_TEMPERATURE_C"
    PANEL_TEMPERATURE_C = "PANEL_TEMPERATURE_C"
    MOTOR_TEMPERATURE_C = "MOTOR_TEMPERATURE_C"
    BEARING_TEMPERATURE_C = "BEARING_TEMPERATURE_C"
    VIBRATION_MM_S_RMS = "VIBRATION_MM_S_RMS"
    BREAKER_POSITION = "BREAKER_POSITION"
    OPERATION_COUNT = "OPERATION_COUNT"
    RUNTIME_HOURS = "RUNTIME_HOURS"
    STARTS_COUNT = "STARTS_COUNT"
    TRIP_COUNT = "TRIP_COUNT"
    BATTERY_VOLTAGE = "BATTERY_VOLTAGE"
    BATTERY_INTERNAL_RESISTANCE_MOHM = "BATTERY_INTERNAL_RESISTANCE_MOHM"
    BATTERY_TEMPERATURE_C = "BATTERY_TEMPERATURE_C"
    STATE_OF_CHARGE_PCT = "STATE_OF_CHARGE_PCT"
    FUEL_LEVEL_PCT = "FUEL_LEVEL_PCT"
    IRRADIANCE_W_M2 = "IRRADIANCE_W_M2"
    DC_VOLTAGE = "DC_VOLTAGE"
    DC_CURRENT = "DC_CURRENT"
    # Members carried over from the engineering package's TelemetryChannel that
    # have no equivalent in the list above, preserved so no vocabulary is lost:
    #   * VOLTAGE_PER_UNIT     -- per-unit voltage (distinct from VOLTAGE_LN/LL)
    #   * CURRENT_THD_PCT      -- current THD (distinct from CURRENT_TDD_PCT)
    #   * HOT_SPOT_TEMPERATURE_C -- transformer hot-spot (distinct from winding)
    VOLTAGE_PER_UNIT = "VOLTAGE_PER_UNIT"
    CURRENT_THD_PCT = "CURRENT_THD_PCT"
    HOT_SPOT_TEMPERATURE_C = "HOT_SPOT_TEMPERATURE_C"


class SectorProfile(str, Enum):
    """Market/sector profile of a facility."""

    DATA_CENTER = "DATA_CENTER"
    HEALTHCARE = "HEALTHCARE"
    MANUFACTURING = "MANUFACTURING"
    COMMERCIAL_REAL_ESTATE = "COMMERCIAL_REAL_ESTATE"
    WATER_TREATMENT = "WATER_TREATMENT"
    LOGISTICS = "LOGISTICS"
    EDUCATION = "EDUCATION"
    MIXED_USE = "MIXED_USE"
    OTHER = "OTHER"


class PhaseTag(str, Enum):
    """Phase designation for a telemetry channel or event."""

    A = "A"
    B = "B"
    C = "C"
    N = "N"
    AB = "AB"
    BC = "BC"
    CA = "CA"
    ABC = "ABC"
    GROUND = "GROUND"


class Quality(str, Enum):
    """Quality flag for a telemetry reading."""

    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    ESTIMATED = "ESTIMATED"
    STALE = "STALE"
    BAD = "BAD"
    MISSING = "MISSING"


class HealthBand(str, Enum):
    """Qualitative band for a health score."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ContributionDirection(str, Enum):
    """Whether a factor raises or lowers a health score."""

    IMPROVES = "IMPROVES"
    DEGRADES = "DEGRADES"
    NEUTRAL = "NEUTRAL"


class ValidationState(str, Enum):
    """Validation lifecycle state of an analytic result or modelled quantity.

    ``CALIBRATED`` is a reserved terminal state describing a model formally
    calibrated against measurements. It is an out-of-band, operator-governed act
    and is never assigned by ordinary repository code paths.
    """

    PENDING = "PENDING"
    PROVISIONAL = "PROVISIONAL"
    PRELIMINARY = "PRELIMINARY"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CALIBRATED = "CALIBRATED"


class DataProvenance(str, Enum):
    """Origin/lineage classification for a data value."""

    SYNTHETIC = "SYNTHETIC"
    SIMULATED = "SIMULATED"
    OPERATOR_ENTERED = "OPERATOR_ENTERED"
    NAMEPLATE = "NAMEPLATE"
    CUSTOMER_HISTORIAN = "CUSTOMER_HISTORIAN"
    CUSTOMER_METER = "CUSTOMER_METER"
    CUSTOMER_LIMS = "CUSTOMER_LIMS"
    THIRD_PARTY = "THIRD_PARTY"


class Severity(str, Enum):
    """Severity level for anomalies and events."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyDomain(str, Enum):
    """Analytic domain that produced an anomaly."""

    THERMAL = "THERMAL"
    ELECTRICAL = "ELECTRICAL"
    HARMONIC = "HARMONIC"
    LOAD = "LOAD"
    INSULATION = "INSULATION"
    MECHANICAL = "MECHANICAL"
    POWER_QUALITY = "POWER_QUALITY"
    TOPOLOGY = "TOPOLOGY"
    OTHER = "OTHER"


class PowerQualityEventType(str, Enum):
    """Classification of a power-quality event."""

    SAG = "SAG"
    SWELL = "SWELL"
    INTERRUPTION = "INTERRUPTION"
    TRANSIENT = "TRANSIENT"
    HARMONIC_DISTORTION = "HARMONIC_DISTORTION"
    FLICKER = "FLICKER"
    UNBALANCE = "UNBALANCE"
    OVERVOLTAGE = "OVERVOLTAGE"
    UNDERVOLTAGE = "UNDERVOLTAGE"
    FREQUENCY_DEVIATION = "FREQUENCY_DEVIATION"


class ITICRegion(str, Enum):
    """Region of the ITIC (CBEMA) susceptibility curve."""

    NO_INTERRUPTION = "NO_INTERRUPTION"
    NO_DAMAGE = "NO_DAMAGE"
    PROHIBITED = "PROHIBITED"
    UNKNOWN = "UNKNOWN"


class ApprovalStatus(str, Enum):
    """Review/approval lifecycle state of an operator-facing artefact.

    Advisory artefacts default to ``PENDING_OPERATOR_REVIEW``: nothing this
    system produces is acted upon without a human operator's review.
    """

    DRAFT = "DRAFT"
    PENDING_OPERATOR_REVIEW = "PENDING_OPERATOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


__all__ = [
    "AssetType",
    "EdgeKind",
    "SwitchState",
    "Criticality",
    "SourceType",
    "EnergizationState",
    "TelemetryChannel",
    "SectorProfile",
    "PhaseTag",
    "Quality",
    "HealthBand",
    "ContributionDirection",
    "ValidationState",
    "DataProvenance",
    "Severity",
    "AnomalyDomain",
    "PowerQualityEventType",
    "ITICRegion",
    "ApprovalStatus",
]
