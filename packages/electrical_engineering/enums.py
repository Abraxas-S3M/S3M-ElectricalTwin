"""Enumerations for the electrical engineering domain model.

These enumerations are pure value types with no behaviour. They are shared by
the topology solver, the plausibility ranges and the standards constants.

Nothing in this module encodes an engineering limit or a standard's normative
text. It only names the discrete states and categories used elsewhere.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class SwitchState(Enum):
    """Declared state of a switching device on an edge.

    ``UNKNOWN`` is a first-class state, not a synonym for open or closed. The
    topology solver must never resolve an ``UNKNOWN`` into a definite state by
    assumption.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    UNKNOWN = "UNKNOWN"


@unique
class SourceType(Enum):
    """Type of an energization source.

    The type determines the energized state a downstream node is reported in
    (see :class:`EnergizationState`).
    """

    UTILITY = "UTILITY"
    GENERATOR = "GENERATOR"
    STORAGE = "STORAGE"
    UPS = "UPS"


@unique
class EnergizationState(Enum):
    """Resolved energization state of a node."""

    ENERGIZED_PRIMARY = "ENERGIZED_PRIMARY"
    ENERGIZED_BACKUP = "ENERGIZED_BACKUP"
    ENERGIZED_UPS = "ENERGIZED_UPS"
    DE_ENERGIZED = "DE_ENERGIZED"
    INDETERMINATE = "INDETERMINATE"


#: States that represent a node that is definitely energized (from some source
#: over a path of exclusively CLOSED switches).
ENERGIZED_STATES = frozenset(
    {
        EnergizationState.ENERGIZED_PRIMARY,
        EnergizationState.ENERGIZED_BACKUP,
        EnergizationState.ENERGIZED_UPS,
    }
)


@unique
class Criticality(Enum):
    """Load criticality classification.

    Ordered from most to least critical. The integer ``rank`` is provided for
    deterministic sorting and partitioning; a lower rank is more critical.
    """

    LIFE_SAFETY = 0
    CRITICAL = 1
    ESSENTIAL = 2
    NON_ESSENTIAL = 3

    @property
    def rank(self) -> int:
        return self.value


@unique
class TelemetryChannel(Enum):
    """Measured or derived telemetry channels for a monitored point.

    Used as the key for advisory plausibility ranges in :mod:`ranges`.
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
