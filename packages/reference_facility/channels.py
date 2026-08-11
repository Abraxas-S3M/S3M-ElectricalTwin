"""Telemetry channel vocabulary for the reference-facility generator.

Channels are string-valued so they serialise to stable JSON and round-trip via
``Channel(value)``. Every member's value equals its name. The unit map records
the engineering unit each channel is expressed in.
"""

from __future__ import annotations

from enum import Enum


class Channel(str, Enum):
    """A measured or derived telemetry channel."""

    VOLTAGE_LL_V = "VOLTAGE_LL_V"
    CURRENT_A = "CURRENT_A"
    ACTIVE_POWER_KW = "ACTIVE_POWER_KW"
    REACTIVE_POWER_KVAR = "REACTIVE_POWER_KVAR"
    APPARENT_POWER_KVA = "APPARENT_POWER_KVA"
    POWER_FACTOR = "POWER_FACTOR"
    FREQUENCY_HZ = "FREQUENCY_HZ"
    ENERGY_ACTIVE_KWH = "ENERGY_ACTIVE_KWH"
    VOLTAGE_THD_PCT = "VOLTAGE_THD_PCT"
    CURRENT_TDD_PCT = "CURRENT_TDD_PCT"
    VOLTAGE_UNBALANCE_PCT = "VOLTAGE_UNBALANCE_PCT"
    WINDING_TEMPERATURE_C = "WINDING_TEMPERATURE_C"
    TOP_OIL_TEMPERATURE_C = "TOP_OIL_TEMPERATURE_C"
    PANEL_TEMPERATURE_C = "PANEL_TEMPERATURE_C"
    BEARING_TEMPERATURE_C = "BEARING_TEMPERATURE_C"
    AMBIENT_TEMPERATURE_C = "AMBIENT_TEMPERATURE_C"
    BREAKER_POSITION = "BREAKER_POSITION"
    BREAKER_OPERATION_COUNT = "BREAKER_OPERATION_COUNT"
    CAPACITOR_STAGES = "CAPACITOR_STAGES"
    RUNTIME_HOURS = "RUNTIME_HOURS"
    START_COUNT = "START_COUNT"


CHANNEL_UNITS: dict[Channel, str] = {
    Channel.VOLTAGE_LL_V: "V",
    Channel.CURRENT_A: "A",
    Channel.ACTIVE_POWER_KW: "kW",
    Channel.REACTIVE_POWER_KVAR: "kvar",
    Channel.APPARENT_POWER_KVA: "kVA",
    Channel.POWER_FACTOR: "ratio",
    Channel.FREQUENCY_HZ: "Hz",
    Channel.ENERGY_ACTIVE_KWH: "kWh",
    Channel.VOLTAGE_THD_PCT: "%",
    Channel.CURRENT_TDD_PCT: "%",
    Channel.VOLTAGE_UNBALANCE_PCT: "%",
    Channel.WINDING_TEMPERATURE_C: "degC",
    Channel.TOP_OIL_TEMPERATURE_C: "degC",
    Channel.PANEL_TEMPERATURE_C: "degC",
    Channel.BEARING_TEMPERATURE_C: "degC",
    Channel.AMBIENT_TEMPERATURE_C: "degC",
    Channel.BREAKER_POSITION: "position",
    Channel.BREAKER_OPERATION_COUNT: "count",
    Channel.CAPACITOR_STAGES: "count",
    Channel.RUNTIME_HOURS: "h",
    Channel.START_COUNT: "count",
}
