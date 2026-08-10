"""Deterministic packet routing for the S3M reasoning engine contract.

S3M is the reasoning brain of the platform. Work incoming to it is described by
a :class:`PacketClass` and an :class:`Urgency`, and every such packet must be
directed to exactly one :class:`EngineClass`. This module defines that routing
as a **pure, total, deterministic** function backed by an explicit, documented
rule table. There is no heuristic scoring and no randomness: the same inputs
always yield the same :class:`RoutingDecision`, and every ``(PacketClass,
Urgency)`` pair resolves with no fallthrough.

There is **no language-model invocation anywhere** in this module (or anywhere
in Work Package 0). Routing is a table lookup, nothing more.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class EngineClass(str, Enum):
    """The reasoning engine a packet is routed to."""

    TACTICAL = "TACTICAL"      # Seconds: alarm triage, event classification, now-state.
    REASONING = "REASONING"    # Causal ranking, evidence assembly, explanation.
    PLANNING = "PLANNING"      # Forecasting, optimization, scenarios, capital studies.
    BILINGUAL = "BILINGUAL"    # Arabic/English rendering of operator-facing artefacts.


class PacketClass(str, Enum):
    """The kind of work described by an incoming packet."""

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
    """How time-critical a packet is."""

    ROUTINE = "ROUTINE"
    ELEVATED = "ELEVATED"
    URGENT = "URGENT"
    IMMEDIATE = "IMMEDIATE"


class RoutingDecision(BaseModel):
    """The immutable outcome of routing a single packet.

    Carries the resolved :class:`EngineClass`, the identifier of the rule that
    matched, and a human-readable rationale. It also echoes the inputs so a
    decision is self-describing when logged or attached to an artefact.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    packet_class: PacketClass
    urgency: Urgency
    engine_class: EngineClass
    rule_id: str
    rationale: str


# --- Explicit, documented rule table ------------------------------------------
#
# Urgency escalation policy: at URGENT or IMMEDIATE, packets describing an
# evolving physical situation that would otherwise be handled analytically are
# escalated to the TACTICAL engine so an operator gets a seconds-scale now-state
# read first. All other packets route to their base engine at every urgency.

#: Urgency levels that trigger tactical escalation of time-critical packets.
_ESCALATING_URGENCIES: frozenset[Urgency] = frozenset({Urgency.URGENT, Urgency.IMMEDIATE})

#: Diagnostic packets whose base engine is REASONING but which escalate to
#: TACTICAL under an escalating urgency.
_ESCALATES_TO_TACTICAL: frozenset[PacketClass] = frozenset(
    {
        PacketClass.ANOMALY_INVESTIGATION,
        PacketClass.ASSET_CONDITION,
        PacketClass.ROOT_CAUSE,
    }
)

#: Base engine and governing rule for each packet class, independent of urgency.
_BASE_RULES: dict[PacketClass, tuple[EngineClass, str, str]] = {
    PacketClass.LIVE_STATE: (
        EngineClass.TACTICAL,
        "R1-TACTICAL-NOWSTATE",
        "Live now-state assessment is a seconds-scale tactical task.",
    ),
    PacketClass.ALARM_TRIAGE: (
        EngineClass.TACTICAL,
        "R1-TACTICAL-NOWSTATE",
        "Alarm triage is a seconds-scale tactical classification task.",
    ),
    PacketClass.POWER_QUALITY_EVENT: (
        EngineClass.TACTICAL,
        "R1-TACTICAL-NOWSTATE",
        "Power-quality event classification is a tactical, now-state task.",
    ),
    PacketClass.ANOMALY_INVESTIGATION: (
        EngineClass.REASONING,
        "R2-REASONING-DIAGNOSTIC",
        "Anomaly investigation requires causal reasoning and evidence assembly.",
    ),
    PacketClass.ASSET_CONDITION: (
        EngineClass.REASONING,
        "R2-REASONING-DIAGNOSTIC",
        "Asset-condition assessment requires evidence assembly and explanation.",
    ),
    PacketClass.ROOT_CAUSE: (
        EngineClass.REASONING,
        "R2-REASONING-DIAGNOSTIC",
        "Root-cause ranking is a causal reasoning task.",
    ),
    PacketClass.MAINTENANCE_PLANNING: (
        EngineClass.PLANNING,
        "R3-PLANNING-STUDY",
        "Maintenance planning is a forward-looking planning study.",
    ),
    PacketClass.ENERGY_ANALYSIS: (
        EngineClass.PLANNING,
        "R3-PLANNING-STUDY",
        "Energy analysis and optimization are planning-scale studies.",
    ),
    PacketClass.RESILIENCE_SCENARIO: (
        EngineClass.PLANNING,
        "R3-PLANNING-STUDY",
        "Resilience scenarios are planning-scale what-if studies.",
    ),
    PacketClass.EXECUTIVE_SUMMARY: (
        EngineClass.BILINGUAL,
        "R4-BILINGUAL-ARTEFACT",
        "Executive summaries are operator-facing bilingual artefacts.",
    ),
    PacketClass.OPERATOR_QUERY: (
        EngineClass.BILINGUAL,
        "R4-BILINGUAL-ARTEFACT",
        "Operator queries are answered as bilingual operator-facing artefacts.",
    ),
}


def _build_decision_table() -> dict[tuple[PacketClass, Urgency], RoutingDecision]:
    """Materialise the complete decision table over every packet/urgency pair.

    Building the whole product up front makes routing a total function by
    construction: the completeness assertion below fails at import time if any
    pair is missing, so :func:`route` never needs a fallthrough branch.
    """
    table: dict[tuple[PacketClass, Urgency], RoutingDecision] = {}
    for packet_class in PacketClass:
        base_engine, base_rule_id, base_rationale = _BASE_RULES[packet_class]
        for urgency in Urgency:
            if packet_class in _ESCALATES_TO_TACTICAL and urgency in _ESCALATING_URGENCIES:
                engine_class = EngineClass.TACTICAL
                rule_id = "R5-URGENT-ESCALATION-TACTICAL"
                rationale = (
                    f"{urgency.value} urgency escalates {packet_class.value} to the "
                    "tactical engine for an immediate now-state read."
                )
            else:
                engine_class = base_engine
                rule_id = base_rule_id
                rationale = base_rationale
            table[(packet_class, urgency)] = RoutingDecision(
                packet_class=packet_class,
                urgency=urgency,
                engine_class=engine_class,
                rule_id=rule_id,
                rationale=rationale,
            )
    return table


#: The complete, precomputed routing table. Every (PacketClass, Urgency) pair is
#: present, so routing is total.
ROUTING_TABLE: dict[tuple[PacketClass, Urgency], RoutingDecision] = _build_decision_table()

# Completeness guard: assert totality at import so a missing pair can never
# silently fall through at call time.
_EXPECTED_PAIRS = len(PacketClass) * len(Urgency)
assert len(ROUTING_TABLE) == _EXPECTED_PAIRS, (
    f"routing table is not total: {len(ROUTING_TABLE)} of {_EXPECTED_PAIRS} pairs"
)


def route(packet_class: PacketClass, urgency: Urgency) -> RoutingDecision:
    """Route a packet to its engine.

    A pure, deterministic, total function: it performs a single lookup into the
    precomputed :data:`ROUTING_TABLE`. Every ``(PacketClass, Urgency)`` pair
    resolves to exactly one :class:`RoutingDecision`; there is no fallthrough,
    no heuristic and no randomness.
    """
    return ROUTING_TABLE[(packet_class, urgency)]


__all__ = [
    "EngineClass",
    "PacketClass",
    "Urgency",
    "RoutingDecision",
    "ROUTING_TABLE",
    "route",
]
