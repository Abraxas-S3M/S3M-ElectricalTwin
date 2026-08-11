"""Demonstration scenarios for the reference facility.

A scenario ties together three things:

* a **topology variant** (the switching configuration the scenario runs on);
* a **telemetry signature** -- the monitored points, their nominal values, the
  noise band, and any deterministic perturbation that shapes an injected
  condition over the replay window; and
* a **ground truth** -- a plain-language statement of what is actually going on,
  the root cause, the affected assets and the diagnosis a correct analysis
  should reach.

The ground truth exists so a demonstration can be scored: the replay produces
telemetry, an analysis produces a conclusion, and the conclusion can be checked
against what the scenario *knows* to be true. Everything here is synthetic.
"""

from __future__ import annotations

from typing import Literal

from packages.canonical_electrical_model import (
    AnomalyDomain,
    CanonicalModel,
    Severity,
    SwitchState,
)
from packages.electrical_engineering import TelemetryChannel
from packages.electrical_engineering.ranges import PLAUSIBILITY_RANGES

from .facility import SYNTHETIC_NOTICE


def _unit_for(channel: TelemetryChannel) -> str:
    plausibility = PLAUSIBILITY_RANGES.get(channel)
    return plausibility.unit if plausibility is not None else "unitless"


class GroundTruth(CanonicalModel):
    """What is actually true in a scenario, for scoring an analysis against."""

    summary: str
    root_cause: str
    anomaly_domain: AnomalyDomain
    severity: Severity
    affected_node_ids: list[str] = []
    expected_diagnosis: str
    notes: str = SYNTHETIC_NOTICE


class MonitoredPoint(CanonicalModel):
    """A single (node, channel) point that produces telemetry during replay."""

    node_id: str
    channel: str
    unit: str
    base_value: float
    noise_amplitude: float = 0.0


class Perturbation(CanonicalModel):
    """A deterministic shaping applied to matching points over a sub-window.

    ``start_fraction``/``end_fraction`` are positions within the replay window
    in ``[0, 1]``. Where a point matches (both ``node_ids`` and ``channels``)
    and the sample falls inside the window, the base+noise value is either
    scaled or offset by ``amount``.
    """

    node_ids: list[str]
    channels: list[str]
    start_fraction: float
    end_fraction: float
    mode: Literal["scale", "offset"]
    amount: float
    label: str


class SwitchingEvent(CanonicalModel):
    """A switch-state change that occurs partway through the replay window."""

    at_fraction: float
    edge_id: str
    new_state: SwitchState
    label: str


class Scenario(CanonicalModel):
    """A named, reproducible demonstration scenario."""

    scenario_id: str
    title: str
    narrative: str
    topology_variant: str
    monitored: list[MonitoredPoint]
    perturbations: list[Perturbation] = []
    switching_events: list[SwitchingEvent] = []
    ground_truth: GroundTruth


# --- Telemetry signature helpers -------------------------------------------

# Nominal line-to-neutral voltage by node voltage class.
_VLN_480 = 277.0
_VLN_208 = 120.0


def _point(
    node_id: str,
    channel: TelemetryChannel,
    base_value: float,
    noise_amplitude: float,
) -> MonitoredPoint:
    return MonitoredPoint(
        node_id=node_id,
        channel=channel.value,
        unit=_unit_for(channel),
        base_value=base_value,
        noise_amplitude=noise_amplitude,
    )


def _bus_points(node_id: str, vln: float, current: float) -> list[MonitoredPoint]:
    """A standard instrument cluster for a bus or panel."""

    return [
        _point(node_id, TelemetryChannel.VOLTAGE_LINE_TO_NEUTRAL_V, vln, vln * 0.004),
        _point(node_id, TelemetryChannel.CURRENT_A, current, current * 0.02),
        _point(node_id, TelemetryChannel.FREQUENCY_HZ, 60.0, 0.01),
        _point(node_id, TelemetryChannel.POWER_FACTOR, 0.96, 0.005),
        _point(node_id, TelemetryChannel.VOLTAGE_THD_PERCENT, 2.0, 0.15),
    ]


def _baseline_monitored() -> list[MonitoredPoint]:
    points: list[MonitoredPoint] = []
    points += _bus_points("MSB", _VLN_480, 1400.0)
    points += _bus_points("BUS-A", _VLN_480, 720.0)
    points += _bus_points("BUS-B", _VLN_480, 680.0)
    points += _bus_points("PANEL-A", _VLN_208, 210.0)
    points += _bus_points("PANEL-CRIT", _VLN_208, 90.0)
    points.append(
        _point("MV-XFMR", TelemetryChannel.TOP_OIL_TEMPERATURE_C, 55.0, 0.4)
    )
    points.append(
        _point("MV-XFMR", TelemetryChannel.HOT_SPOT_TEMPERATURE_C, 78.0, 0.6)
    )
    return points


_VOLTAGE_CHANNELS = [
    TelemetryChannel.VOLTAGE_LINE_TO_NEUTRAL_V.value,
]


def _scenarios() -> list[Scenario]:
    scenarios: list[Scenario] = []

    scenarios.append(
        Scenario(
            scenario_id="SC-01",
            title="Nominal steady state",
            narrative=(
                "The facility runs on utility power in its normal configuration. "
                "All monitored points sit near nominal within a tight noise band."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            ground_truth=GroundTruth(
                summary="Healthy nominal operation; no event.",
                root_cause="None; steady-state baseline.",
                anomaly_domain=AnomalyDomain.OTHER,
                severity=Severity.INFO,
                expected_diagnosis="No anomaly should be reported.",
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-02",
            title="Voltage sag on bus A",
            narrative=(
                "A brief voltage sag depresses bus A line-to-neutral voltage to "
                "roughly 0.8 pu partway through the window, then recovers."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["BUS-A", "PANEL-A"],
                    channels=_VOLTAGE_CHANNELS,
                    start_fraction=0.30,
                    end_fraction=0.34,
                    mode="scale",
                    amount=0.80,
                    label="Voltage sag to ~0.8 pu",
                )
            ],
            ground_truth=GroundTruth(
                summary="Voltage sag on bus A.",
                root_cause="Upstream fault ride-through / large motor start (synthetic).",
                anomaly_domain=AnomalyDomain.POWER_QUALITY,
                severity=Severity.MEDIUM,
                affected_node_ids=["BUS-A", "PANEL-A"],
                expected_diagnosis="A SAG power-quality event on bus A near 30-34% of the window.",
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-03",
            title="Voltage swell on bus B",
            narrative=(
                "Bus B line-to-neutral voltage rises to about 1.15 pu for a short "
                "interval, consistent with a swell."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["BUS-B"],
                    channels=_VOLTAGE_CHANNELS,
                    start_fraction=0.55,
                    end_fraction=0.58,
                    mode="scale",
                    amount=1.15,
                    label="Voltage swell to ~1.15 pu",
                )
            ],
            ground_truth=GroundTruth(
                summary="Voltage swell on bus B.",
                root_cause="Load rejection / capacitor switching (synthetic).",
                anomaly_domain=AnomalyDomain.POWER_QUALITY,
                severity=Severity.MEDIUM,
                affected_node_ids=["BUS-B"],
                expected_diagnosis=(
                    "A SWELL power-quality event on bus B near 55-58% of the window."
                ),
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-04",
            title="Utility interruption and generator transfer",
            narrative=(
                "The utility feed is lost midway through the window. The standby "
                "generator starts and closes onto the main board, restoring the "
                "loads on backup power."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["MSB", "BUS-A", "BUS-B", "PANEL-A", "PANEL-CRIT"],
                    channels=_VOLTAGE_CHANNELS,
                    start_fraction=0.50,
                    end_fraction=0.505,
                    mode="scale",
                    amount=0.02,
                    label="Momentary interruption during transfer",
                )
            ],
            switching_events=[
                SwitchingEvent(
                    at_fraction=0.50,
                    edge_id="E-UTIL-XFMR",
                    new_state=SwitchState.OPEN,
                    label="Utility breaker opens (utility lost)",
                ),
                SwitchingEvent(
                    at_fraction=0.505,
                    edge_id="E-GEN-MSB",
                    new_state=SwitchState.CLOSED,
                    label="Generator breaker closes (transfer to backup)",
                ),
            ],
            ground_truth=GroundTruth(
                summary="Utility interruption followed by generator transfer.",
                root_cause="Loss of utility source; standby generator picks up load.",
                anomaly_domain=AnomalyDomain.TOPOLOGY,
                severity=Severity.HIGH,
                affected_node_ids=["UTIL-1", "GEN-1", "MSB"],
                expected_diagnosis=(
                    "An INTERRUPTION at ~50% of the window with a source transfer "
                    "from utility (primary) to generator (backup)."
                ),
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-05",
            title="Transformer thermal excursion",
            narrative=(
                "The main transformer top-oil and hot-spot temperatures climb well "
                "above their nominal band in the second half of the window."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["MV-XFMR"],
                    channels=[
                        TelemetryChannel.TOP_OIL_TEMPERATURE_C.value,
                        TelemetryChannel.HOT_SPOT_TEMPERATURE_C.value,
                    ],
                    start_fraction=0.55,
                    end_fraction=1.0,
                    mode="offset",
                    amount=35.0,
                    label="Rising oil and hot-spot temperature",
                )
            ],
            ground_truth=GroundTruth(
                summary="Thermal excursion on the main transformer.",
                root_cause="Sustained overload or cooling degradation (synthetic).",
                anomaly_domain=AnomalyDomain.THERMAL,
                severity=Severity.HIGH,
                affected_node_ids=["MV-XFMR"],
                expected_diagnosis=(
                    "A thermal anomaly on MV-XFMR in the second half of the window."
                ),
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-06",
            title="Harmonic distortion rise",
            narrative=(
                "Voltage total harmonic distortion at panel A rises from ~2% to "
                "well above 8% as a non-linear load ramps up."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["PANEL-A"],
                    channels=[TelemetryChannel.VOLTAGE_THD_PERCENT.value],
                    start_fraction=0.40,
                    end_fraction=0.90,
                    mode="offset",
                    amount=8.0,
                    label="Elevated voltage THD",
                )
            ],
            ground_truth=GroundTruth(
                summary="Elevated harmonic distortion at panel A.",
                root_cause="Non-linear load / VFD operation (synthetic).",
                anomaly_domain=AnomalyDomain.HARMONIC,
                severity=Severity.MEDIUM,
                affected_node_ids=["PANEL-A"],
                expected_diagnosis="Voltage THD at PANEL-A exceeding a typical 8% screening level.",
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-07",
            title="Load imbalance",
            narrative=(
                "Panel A current rises steadily while its power factor droops, "
                "consistent with a growing, poorly-compensated load."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["PANEL-A"],
                    channels=[TelemetryChannel.CURRENT_A.value],
                    start_fraction=0.30,
                    end_fraction=1.0,
                    mode="scale",
                    amount=1.4,
                    label="Rising load current",
                ),
                Perturbation(
                    node_ids=["PANEL-A"],
                    channels=[TelemetryChannel.POWER_FACTOR.value],
                    start_fraction=0.30,
                    end_fraction=1.0,
                    mode="offset",
                    amount=-0.12,
                    label="Drooping power factor",
                ),
            ],
            ground_truth=GroundTruth(
                summary="Growing, poorly-compensated load at panel A.",
                root_cause="Added inductive load without compensation (synthetic).",
                anomaly_domain=AnomalyDomain.LOAD,
                severity=Severity.LOW,
                affected_node_ids=["PANEL-A"],
                expected_diagnosis="Rising current with falling power factor at PANEL-A.",
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-08",
            title="Planned bus-tie maintenance transfer",
            narrative=(
                "The bus B main feeder is taken out for maintenance. The bus tie "
                "is closed first so bus B is carried by backfeed from bus A across "
                "the tie, keeping its loads energized throughout."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["BUS-A"],
                    channels=[TelemetryChannel.CURRENT_A.value],
                    start_fraction=0.40,
                    end_fraction=1.0,
                    mode="scale",
                    amount=1.6,
                    label="Bus A picks up bus B load across the tie",
                )
            ],
            switching_events=[
                SwitchingEvent(
                    at_fraction=0.40,
                    edge_id="E-TIE-AB",
                    new_state=SwitchState.CLOSED,
                    label="Bus tie closed ahead of the transfer",
                ),
                SwitchingEvent(
                    at_fraction=0.42,
                    edge_id="E-MSB-BUSB",
                    new_state=SwitchState.OPEN,
                    label="Bus B main feeder opened for maintenance",
                ),
            ],
            ground_truth=GroundTruth(
                summary="Planned maintenance transfer of bus B onto the tie.",
                root_cause="Deliberate switching for maintenance; bus B backfed from bus A.",
                anomaly_domain=AnomalyDomain.TOPOLOGY,
                severity=Severity.LOW,
                affected_node_ids=["BUS-A", "BUS-B", "XFMR-B", "PANEL-B"],
                expected_diagnosis=(
                    "A planned switching transfer; bus B remains energized via "
                    "backfeed across the closed tie, no loss of load."
                ),
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-09",
            title="Frequency deviation",
            narrative=(
                "System frequency dips below nominal for a sustained interval, "
                "consistent with a generation/load mismatch while on backup."
            ),
            topology_variant="utility_outage",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["MSB", "BUS-A", "BUS-B", "PANEL-A", "PANEL-CRIT"],
                    channels=[TelemetryChannel.FREQUENCY_HZ.value],
                    start_fraction=0.25,
                    end_fraction=0.60,
                    mode="offset",
                    amount=-0.8,
                    label="Frequency dip while on generator",
                )
            ],
            ground_truth=GroundTruth(
                summary="Sustained under-frequency while on generator.",
                root_cause="Generation/load mismatch on the standby source (synthetic).",
                anomaly_domain=AnomalyDomain.ELECTRICAL,
                severity=Severity.HIGH,
                affected_node_ids=["GEN-1", "MSB"],
                expected_diagnosis="A frequency deviation below ~59.5 Hz on the backup source.",
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-10",
            title="Power-factor degradation",
            narrative=(
                "Facility-wide power factor drifts downward over the window as "
                "reactive demand grows."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["MSB", "BUS-A", "BUS-B"],
                    channels=[TelemetryChannel.POWER_FACTOR.value],
                    start_fraction=0.10,
                    end_fraction=1.0,
                    mode="offset",
                    amount=-0.18,
                    label="Declining power factor",
                )
            ],
            ground_truth=GroundTruth(
                summary="Facility-wide power-factor degradation.",
                root_cause="Rising uncompensated reactive load (synthetic).",
                anomaly_domain=AnomalyDomain.LOAD,
                severity=Severity.LOW,
                affected_node_ids=["MSB", "BUS-A", "BUS-B"],
                expected_diagnosis="A downward power-factor trend across the main buses.",
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-11",
            title="Sensor dropout with indeterminate topology",
            narrative=(
                "The position of the bus A distribution feeder cannot be "
                "determined. Nodes reachable only through it are indeterminate; "
                "the analysis must not guess the switch state either way."
            ),
            topology_variant="sensor_dropout",
            monitored=_baseline_monitored(),
            ground_truth=GroundTruth(
                summary="Unknown feeder position downstream of bus A.",
                root_cause="Lost switch-position telemetry on E-BUSA-XFMRA (synthetic).",
                anomaly_domain=AnomalyDomain.TOPOLOGY,
                severity=Severity.MEDIUM,
                affected_node_ids=["XFMR-A", "PANEL-A", "LOAD-A1", "LOAD-A2"],
                expected_diagnosis=(
                    "XFMR-A and everything below it must be reported INDETERMINATE, "
                    "never assumed energized or de-energized."
                ),
            ),
        )
    )

    scenarios.append(
        Scenario(
            scenario_id="SC-12",
            title="Sustained overvoltage",
            narrative=(
                "Line-to-neutral voltage across the main buses sits about 8% high "
                "for the whole window."
            ),
            topology_variant="normal",
            monitored=_baseline_monitored(),
            perturbations=[
                Perturbation(
                    node_ids=["MSB", "BUS-A", "BUS-B"],
                    channels=_VOLTAGE_CHANNELS,
                    start_fraction=0.0,
                    end_fraction=1.0,
                    mode="scale",
                    amount=1.08,
                    label="Sustained overvoltage ~1.08 pu",
                )
            ],
            ground_truth=GroundTruth(
                summary="Sustained overvoltage on the main buses.",
                root_cause="Tap setting / regulation issue (synthetic).",
                anomaly_domain=AnomalyDomain.POWER_QUALITY,
                severity=Severity.MEDIUM,
                affected_node_ids=["MSB", "BUS-A", "BUS-B"],
                expected_diagnosis="Steady overvoltage near 1.08 pu across the main buses.",
            ),
        )
    )

    return scenarios


_SCENARIOS: dict[str, Scenario] = {s.scenario_id: s for s in _scenarios()}


def all_scenarios() -> list[Scenario]:
    """Return every scenario, ordered by scenario id (fresh copies)."""

    return [s.model_copy(deep=True) for s in _SCENARIOS.values()]


def scenario_ids() -> list[str]:
    """Return the ordered list of scenario ids."""

    return list(_SCENARIOS.keys())


class UnknownScenarioError(KeyError):
    """Raised when a scenario id is not known."""


def get_scenario(scenario_id: str) -> Scenario:
    """Return a single scenario by id (a fresh copy).

    Raises:
        UnknownScenarioError: if ``scenario_id`` is not a known scenario.
    """

    scenario = _SCENARIOS.get(scenario_id)
    if scenario is None:
        raise UnknownScenarioError(
            f"Unknown scenario id {scenario_id!r}; known ids are: "
            f"{', '.join(_SCENARIOS)}."
        )
    return scenario.model_copy(deep=True)
