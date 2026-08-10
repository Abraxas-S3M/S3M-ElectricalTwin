"""The packet-to-engine routing table.

Routing is deterministic and declarative: a :class:`PacketClass` maps to exactly
one :class:`RoutingEntry`, which names the validated calculator responsible for
the physics and whether a validated topology is a precondition. The S3M reasoner
consumes the calculator's output and composes the card; it never substitutes for
the calculation.
"""Deterministic engine routing for the S3M ElectricalTwin contract.

S3M is the reasoning brain of the platform. Before any reasoning takes place a
packet must be routed to exactly one engine. Routing here is a PURE,
DETERMINISTIC function of ``(PacketClass, Urgency)``. There are no heuristics,
no randomness and no language-model invocation.

The mapping is expressed as an explicit table (``ROUTING_TABLE``) that is
materialised at import time for every ``(PacketClass, Urgency)`` pair. Routing
is therefore TOTAL: every pair resolves to a :class:`RoutingDecision` and there
is no fallthrough. A module-level self-check asserts completeness on import.

Engine responsibilities
------------------------
* ``TACTICAL``   - seconds; alarm triage, event classification, now-state.
* ``REASONING``  - causal ranking, evidence assembly, explanation.
* ``PLANNING``   - forecasting, optimization, scenarios, capital studies.
* ``BILINGUAL``  - Arabic/English rendering of operator-facing artefacts.

Documented mapping table
------------------------
The base engine is selected by ``PacketClass``. A single, explicit urgency rule
escalates the two *event-driven* packet classes to ``TACTICAL`` when their
urgency is ``IMMEDIATE`` (an immediate power-quality event or anomaly must be
stabilised as now-state before deeper reasoning is attempted).

PacketClass                  Base engine                 IMMEDIATE override
LIVE_STATE                   TACTICAL                    (unchanged)
ALARM_TRIAGE                 TACTICAL                    (unchanged)
POWER_QUALITY_EVENT          REASONING                   TACTICAL
ANOMALY_INVESTIGATION        REASONING                   TACTICAL
ASSET_CONDITION              REASONING                   (unchanged)
ROOT_CAUSE                   REASONING                   (unchanged)
MAINTENANCE_PLANNING         PLANNING                    (unchanged)
ENERGY_ANALYSIS              PLANNING                    (unchanged)
RESILIENCE_SCENARIO          PLANNING                    (unchanged)
EXECUTIVE_SUMMARY            BILINGUAL                   (unchanged)
OPERATOR_QUERY               BILINGUAL                   (unchanged)
"""

from __future__ import annotations

from pydantic import BaseModel

from packages.s3m_engine_contract.packets import EngineClass, EnginePacket, PacketClass


class RoutingEntry(BaseModel):
    """One row of the routing table."""

    model_config = {"frozen": True}

    packet_class: PacketClass
    engine_class: EngineClass
    requires_validated_topology: bool
    rationale: str


ROUTING_TABLE: dict[PacketClass, RoutingEntry] = {
    PacketClass.STEADY_STATE_LOADING: RoutingEntry(
        packet_class=PacketClass.STEADY_STATE_LOADING,
        engine_class=EngineClass.LOAD_FLOW_BALANCED,
        requires_validated_topology=True,
        rationale=(
            "Balanced steady-state loading is a load-flow problem solved by the "
            "pandapower engine; it is only meaningful over a validated topology."
        ),
    ),
    PacketClass.FAULT_LEVEL: RoutingEntry(
        packet_class=PacketClass.FAULT_LEVEL,
        engine_class=EngineClass.SHORT_CIRCUIT_IEC60909,
        requires_validated_topology=True,
        rationale=(
            "Fault-level assessment uses the IEC 60909 short-circuit calculation "
            "provided by pandapower. Protection settings are treated as data only."
        ),
    ),
    PacketClass.CONTINGENCY_N1: RoutingEntry(
        packet_class=PacketClass.CONTINGENCY_N1,
        engine_class=EngineClass.CONTINGENCY_N1,
        requires_validated_topology=True,
        rationale=(
            "N-1 contingency screening iterates load flow over single-element "
            "outages using pandapower."
        ),
    ),
    PacketClass.POWER_QUALITY: RoutingEntry(
        packet_class=PacketClass.POWER_QUALITY,
        engine_class=EngineClass.UNBALANCED_HARMONICS,
        requires_validated_topology=True,
        rationale=(
            "Unbalance and harmonics require a phase-explicit solver; OpenDSS via "
            "dss-python is used."
        ),
    ),
    PacketClass.DISPATCH_ECONOMICS: RoutingEntry(
        packet_class=PacketClass.DISPATCH_ECONOMICS,
        engine_class=EngineClass.DISPATCH_STORAGE,
        requires_validated_topology=False,
        rationale=(
            "Dispatch and storage economics are an optimisation problem handled "
            "by PyPSA."
        ),
    ),
    PacketClass.ASSET_HEALTH: RoutingEntry(
        packet_class=PacketClass.ASSET_HEALTH,
        engine_class=EngineClass.S3M_REASONER,
        requires_validated_topology=False,
        rationale=(
            "Asset-health triage weighs heterogeneous evidence; the S3M reasoner "
            "frames the question and cites evidence but calculates nothing."
        ),
    ),
    PacketClass.ANOMALY_TRIAGE: RoutingEntry(
        packet_class=PacketClass.ANOMALY_TRIAGE,
        engine_class=EngineClass.S3M_REASONER,
        requires_validated_topology=False,
        rationale=(
            "Anomaly triage is a reasoning task: the S3M reasoner correlates "
            "signals and proposes ranked hypotheses for a human to adjudicate."
        ),
    ),
}


def route(packet: EnginePacket) -> RoutingEntry:
    """Return the routing entry for ``packet`` based on its packet class."""

    try:
        return ROUTING_TABLE[packet.packet_class]
    except KeyError as exc:  # pragma: no cover - guarded by the enum
        raise KeyError(f"no routing entry for packet class {packet.packet_class}") from exc


def routing_table_as_dicts() -> list[dict[str, object]]:
    """Return the routing table as plain dictionaries for API serialisation."""

    return [
        {
            "packet_class": entry.packet_class.value,
            "engine_class": entry.engine_class.value,
            "requires_validated_topology": entry.requires_validated_topology,
            "rationale": entry.rationale,
        }
        for entry in ROUTING_TABLE.values()
    ]
from enum import Enum

from pydantic import BaseModel, ConfigDict

__all__ = [
    "EngineClass",
    "PacketClass",
    "Urgency",
    "RoutingDecision",
    "route",
    "ROUTING_TABLE",
]


class EngineClass(str, Enum):
    """The four engines S3M can route a packet to."""

    TACTICAL = "TACTICAL"
    REASONING = "REASONING"
    PLANNING = "PLANNING"
    BILINGUAL = "BILINGUAL"


class PacketClass(str, Enum):
    """The kind of analytical work a packet represents."""

    LIVE_STATE = "LIVE_STATE"
    ALARM_TRIAGE = "ALARM_TRIAGE"
    ANOMALY_INVESTIGATION = "ANOMALY_INVESTIGATION"
    POWER_QUALITY_EVENT = "POWER_QUALITY_EVENT"
    ASSET_CONDITION = "ASSET_CONDITION"
    MAINTENANCE_PLANNING = "MAINTENANCE_PLANNING"
    ENERGY_ANALYSIS = "ENERGY_ANALYSIS"
    RESILIENCE_SCENARIO = "RESILIENCE_SCENARIO"
    ROOT_CAUSE = "ROOT_CAUSE"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    OPERATOR_QUERY = "OPERATOR_QUERY"


class Urgency(str, Enum):
    """How quickly a packet must be answered."""

    ROUTINE = "ROUTINE"
    ELEVATED = "ELEVATED"
    URGENT = "URGENT"
    IMMEDIATE = "IMMEDIATE"


class RoutingDecision(BaseModel):
    """The immutable outcome of routing a single packet.

    Carries the chosen engine, the id of the mapping rule that matched, and a
    human-readable rationale. ``packet_class`` and ``urgency`` are retained for
    traceability so a decision can be audited in isolation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    packet_class: PacketClass
    urgency: Urgency
    engine: EngineClass
    rule_id: str
    rationale: str


# --- Explicit, documented mapping -------------------------------------------

_BASE_ENGINE: dict[PacketClass, EngineClass] = {
    PacketClass.LIVE_STATE: EngineClass.TACTICAL,
    PacketClass.ALARM_TRIAGE: EngineClass.TACTICAL,
    PacketClass.POWER_QUALITY_EVENT: EngineClass.REASONING,
    PacketClass.ANOMALY_INVESTIGATION: EngineClass.REASONING,
    PacketClass.ASSET_CONDITION: EngineClass.REASONING,
    PacketClass.ROOT_CAUSE: EngineClass.REASONING,
    PacketClass.MAINTENANCE_PLANNING: EngineClass.PLANNING,
    PacketClass.ENERGY_ANALYSIS: EngineClass.PLANNING,
    PacketClass.RESILIENCE_SCENARIO: EngineClass.PLANNING,
    PacketClass.EXECUTIVE_SUMMARY: EngineClass.BILINGUAL,
    PacketClass.OPERATOR_QUERY: EngineClass.BILINGUAL,
}

# Event-driven classes that, at IMMEDIATE urgency, are stabilised as now-state
# by the TACTICAL engine before any deeper reasoning is attempted.
_IMMEDIATE_TACTICAL_ESCALATION: frozenset[PacketClass] = frozenset(
    {
        PacketClass.POWER_QUALITY_EVENT,
        PacketClass.ANOMALY_INVESTIGATION,
    }
)


def _build_decision(packet_class: PacketClass, urgency: Urgency) -> RoutingDecision:
    """Resolve one pair into a fully-formed decision (used to seed the table)."""

    base_engine = _BASE_ENGINE[packet_class]

    if urgency is Urgency.IMMEDIATE and packet_class in _IMMEDIATE_TACTICAL_ESCALATION:
        engine = EngineClass.TACTICAL
        rule_id = f"R-{packet_class.name}-IMMEDIATE-ESCALATION"
        rationale = (
            f"{packet_class.name} at IMMEDIATE urgency is escalated from the "
            f"{base_engine.name} engine to the TACTICAL engine so the event is "
            "stabilised as now-state before deeper reasoning proceeds."
        )
    else:
        engine = base_engine
        rule_id = f"R-{packet_class.name}-BASE"
        rationale = (
            f"{packet_class.name} at {urgency.name} urgency is routed to the "
            f"{engine.name} engine by its base mapping."
        )

    return RoutingDecision(
        packet_class=packet_class,
        urgency=urgency,
        engine=engine,
        rule_id=rule_id,
        rationale=rationale,
    )


# Materialise every (PacketClass, Urgency) pair exactly once. The routing
# function is a pure table lookup over this structure.
ROUTING_TABLE: dict[tuple[PacketClass, Urgency], RoutingDecision] = {
    (packet_class, urgency): _build_decision(packet_class, urgency)
    for packet_class in PacketClass
    for urgency in Urgency
}


# Import-time totality guarantee: the table must cover the full cross product
# with no missing or duplicated cells.
_EXPECTED_PAIRS = len(list(PacketClass)) * len(list(Urgency))
assert len(ROUTING_TABLE) == _EXPECTED_PAIRS, (
    "ROUTING_TABLE is not total: "
    f"{len(ROUTING_TABLE)} entries, expected {_EXPECTED_PAIRS}"
)


def route(packet_class: PacketClass, urgency: Urgency) -> RoutingDecision:
    """Route a packet to exactly one engine.

    Pure and deterministic: the same ``(packet_class, urgency)`` always yields
    an identical :class:`RoutingDecision`. The lookup is TOTAL — every pair is
    present in :data:`ROUTING_TABLE`, so a resolution is always returned and
    there is no fallthrough. A :class:`KeyError` can only arise if the callers
    pass a value that is not a member of the declared enums.
    """

    return ROUTING_TABLE[(packet_class, urgency)]
