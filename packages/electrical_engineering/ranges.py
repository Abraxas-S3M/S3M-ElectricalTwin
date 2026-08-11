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


#: Advisory data-quality bounds per channel. NOT engineering limits. There is
#: exactly one entry per :class:`TelemetryChannel` member: a value outside a
#: channel's range is flagged as a likely sensor/unit/transport fault, never as
#: an electrical event.
PLAUSIBILITY_RANGES: dict[TelemetryChannel, PlausibilityRange] = {
    TelemetryChannel.VOLTAGE_LN: PlausibilityRange(0.0, 900_000.0, "V"),
    TelemetryChannel.VOLTAGE_LL: PlausibilityRange(0.0, 1_600_000.0, "V"),
    TelemetryChannel.CURRENT: PlausibilityRange(0.0, 100_000.0, "A"),
    TelemetryChannel.ACTIVE_POWER_KW: PlausibilityRange(-2.0e6, 2.0e6, "kW"),
    TelemetryChannel.REACTIVE_POWER_KVAR: PlausibilityRange(-2.0e6, 2.0e6, "kvar"),
    TelemetryChannel.APPARENT_POWER_KVA: PlausibilityRange(0.0, 2.0e6, "kVA"),
    TelemetryChannel.POWER_FACTOR: PlausibilityRange(-1.0, 1.0, "unitless"),
    TelemetryChannel.FREQUENCY_HZ: PlausibilityRange(0.0, 100.0, "Hz"),
    TelemetryChannel.ENERGY_KWH: PlausibilityRange(0.0, 1.0e12, "kWh"),
    TelemetryChannel.DEMAND_KVA: PlausibilityRange(0.0, 2.0e6, "kVA"),
    TelemetryChannel.VOLTAGE_THD_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.CURRENT_TDD_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.HARMONIC_MAGNITUDE: PlausibilityRange(0.0, 1.0e6, "magnitude"),
    TelemetryChannel.VOLTAGE_UNBALANCE_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.CURRENT_UNBALANCE_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.WINDING_TEMPERATURE_C: PlausibilityRange(-60.0, 300.0, "degC"),
    TelemetryChannel.TOP_OIL_TEMPERATURE_C: PlausibilityRange(-60.0, 250.0, "degC"),
    TelemetryChannel.AMBIENT_TEMPERATURE_C: PlausibilityRange(-60.0, 80.0, "degC"),
    TelemetryChannel.PANEL_TEMPERATURE_C: PlausibilityRange(-60.0, 200.0, "degC"),
    TelemetryChannel.MOTOR_TEMPERATURE_C: PlausibilityRange(-60.0, 300.0, "degC"),
    TelemetryChannel.BEARING_TEMPERATURE_C: PlausibilityRange(-60.0, 300.0, "degC"),
    TelemetryChannel.VIBRATION_MM_S_RMS: PlausibilityRange(0.0, 1_000.0, "mm/s"),
    TelemetryChannel.BREAKER_POSITION: PlausibilityRange(0.0, 1.0, "unitless"),
    TelemetryChannel.OPERATION_COUNT: PlausibilityRange(0.0, 1.0e9, "count"),
    TelemetryChannel.RUNTIME_HOURS: PlausibilityRange(0.0, 1.0e7, "h"),
    TelemetryChannel.STARTS_COUNT: PlausibilityRange(0.0, 1.0e9, "count"),
    TelemetryChannel.TRIP_COUNT: PlausibilityRange(0.0, 1.0e9, "count"),
    TelemetryChannel.BATTERY_VOLTAGE: PlausibilityRange(0.0, 10_000.0, "V"),
    TelemetryChannel.BATTERY_INTERNAL_RESISTANCE_MOHM: PlausibilityRange(0.0, 1.0e6, "mOhm"),
    TelemetryChannel.BATTERY_TEMPERATURE_C: PlausibilityRange(-60.0, 150.0, "degC"),
    TelemetryChannel.STATE_OF_CHARGE_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.FUEL_LEVEL_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.IRRADIANCE_W_M2: PlausibilityRange(0.0, 2_000.0, "W/m2"),
    TelemetryChannel.DC_VOLTAGE: PlausibilityRange(0.0, 5_000.0, "V"),
    TelemetryChannel.DC_CURRENT: PlausibilityRange(0.0, 100_000.0, "A"),
    TelemetryChannel.VOLTAGE_PER_UNIT: PlausibilityRange(0.0, 2.0, "pu"),
    TelemetryChannel.CURRENT_THD_PCT: PlausibilityRange(0.0, 100.0, "%"),
    TelemetryChannel.HOT_SPOT_TEMPERATURE_C: PlausibilityRange(-60.0, 300.0, "degC"),
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
