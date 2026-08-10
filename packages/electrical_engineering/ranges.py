"""Advisory plausibility ranges per telemetry channel.

These ranges exist for ONE purpose: tagging incoming telemetry samples as
``OUT_OF_RANGE`` for data-quality screening. A value outside the range is far
more likely to be a sensor fault, a mislabelled unit or a transport error than
a real measurement.

THESE ARE ADVISORY DATA-QUALITY BOUNDS. THEY ARE NEVER ENGINEERING LIMITS.
    Do not use them as protection thresholds, ratings, alarm setpoints, or any
    kind of operational or safety limit. A value comfortably inside its
    plausibility range can still be a serious engineering problem, and a value
    flagged OUT_OF_RANGE is a data-quality signal, not an electrical event.
"""

from __future__ import annotations

from dataclasses import dataclass

from packages.canonical_electrical_model import TelemetryChannel


@dataclass(frozen=True)
class PlausibilityRange:
    """Inclusive advisory bounds for a telemetry channel (data quality only)."""

    low: float
    high: float
    unit: str

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


#: Advisory data-quality bounds per channel. NOT engineering limits.
PLAUSIBILITY_RANGES: dict[TelemetryChannel, PlausibilityRange] = {
    TelemetryChannel.VOLTAGE_LINE_TO_NEUTRAL_V: PlausibilityRange(0.0, 900_000.0, "V"),
    TelemetryChannel.VOLTAGE_LINE_TO_LINE_V: PlausibilityRange(0.0, 1_600_000.0, "V"),
    TelemetryChannel.VOLTAGE_PER_UNIT: PlausibilityRange(0.0, 2.0, "pu"),
    TelemetryChannel.CURRENT_A: PlausibilityRange(0.0, 100_000.0, "A"),
    TelemetryChannel.FREQUENCY_HZ: PlausibilityRange(0.0, 100.0, "Hz"),
    TelemetryChannel.ACTIVE_POWER_W: PlausibilityRange(-2.0e9, 2.0e9, "W"),
    TelemetryChannel.REACTIVE_POWER_VAR: PlausibilityRange(-2.0e9, 2.0e9, "var"),
    TelemetryChannel.APPARENT_POWER_VA: PlausibilityRange(0.0, 2.0e9, "VA"),
    TelemetryChannel.POWER_FACTOR: PlausibilityRange(-1.0, 1.0, "unitless"),
    TelemetryChannel.VOLTAGE_THD_PERCENT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.CURRENT_THD_PERCENT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.VOLTAGE_UNBALANCE_PERCENT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.TOP_OIL_TEMPERATURE_C: PlausibilityRange(-60.0, 250.0, "degC"),
    TelemetryChannel.HOT_SPOT_TEMPERATURE_C: PlausibilityRange(-60.0, 300.0, "degC"),
    TelemetryChannel.AMBIENT_TEMPERATURE_C: PlausibilityRange(-60.0, 80.0, "degC"),
}


def is_out_of_range(channel: TelemetryChannel, value: float) -> bool:
    """Return ``True`` when ``value`` falls outside the advisory range.

    Channels without a defined range are never flagged (there is no advisory
    bound to test against). This is a data-quality screen only.
    """

    plausibility = PLAUSIBILITY_RANGES.get(channel)
    if plausibility is None:
        return False
    return not plausibility.contains(value)
