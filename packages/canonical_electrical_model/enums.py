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
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    INTERMEDIATE = "INTERMEDIATE"
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


class EnergizationState(str, Enum):
    """Resolved energization state of a node.

    This is a *conservative computation* over the topology graph, not a reported
    field on an asset. ``INDETERMINATE`` is a first-class value: when a node can
    only be reached by traversing a switch whose state is not definitively known
    (``UNKNOWN`` / ``INTERMEDIATE``), the state is reported as indeterminate and
    is never guessed in either direction.
    """

    ENERGIZED_PRIMARY = "ENERGIZED_PRIMARY"
    ENERGIZED_BACKUP = "ENERGIZED_BACKUP"
    ENERGIZED_UPS = "ENERGIZED_UPS"
    DE_ENERGIZED = "DE_ENERGIZED"
    INDETERMINATE = "INDETERMINATE"


class TelemetryChannel(str, Enum):
    """Measured or derived telemetry channels for a monitored point.

    A controlled vocabulary for the free-form ``ElectricalReading.channel``
    field. It is also the key used for advisory data-quality plausibility
    ranges in the electrical-engineering calculations package.
    """

    VOLTAGE_LINE_TO_NEUTRAL_V = "VOLTAGE_LINE_TO_NEUTRAL_V"
    VOLTAGE_LINE_TO_LINE_V = "VOLTAGE_LINE_TO_LINE_V"
    VOLTAGE_PER_UNIT = "VOLTAGE_PER_UNIT"
    CURRENT_A = "CURRENT_A"
    FREQUENCY_HZ = "FREQUENCY_HZ"
    ACTIVE_POWER_W = "ACTIVE_POWER_W"
    REACTIVE_POWER_VAR = "REACTIVE_POWER_VAR"
    APPARENT_POWER_VA = "APPARENT_POWER_VA"
    POWER_FACTOR = "POWER_FACTOR"
    VOLTAGE_THD_PERCENT = "VOLTAGE_THD_PERCENT"
    CURRENT_THD_PERCENT = "CURRENT_THD_PERCENT"
    VOLTAGE_UNBALANCE_PERCENT = "VOLTAGE_UNBALANCE_PERCENT"
    TOP_OIL_TEMPERATURE_C = "TOP_OIL_TEMPERATURE_C"
    HOT_SPOT_TEMPERATURE_C = "HOT_SPOT_TEMPERATURE_C"
    AMBIENT_TEMPERATURE_C = "AMBIENT_TEMPERATURE_C"


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
    "EnergizationState",
    "TelemetryChannel",
    "ApprovalStatus",
]
