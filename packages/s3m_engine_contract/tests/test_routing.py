"""Routing is pure, deterministic and TOTAL across every pair."""

from __future__ import annotations

import itertools

from packages.s3m_engine_contract.routing import (
    EngineClass,
    PacketClass,
    RoutingDecision,
    Urgency,
    route,
)


def test_routing_is_total_across_every_pair() -> None:
    resolved = 0
    for packet_class, urgency in itertools.product(PacketClass, Urgency):
        decision = route(packet_class, urgency)
        assert isinstance(decision, RoutingDecision)
        assert decision.engine in EngineClass
        assert decision.rule_id  # non-empty
        assert decision.rationale  # non-empty
        assert decision.packet_class is packet_class
        assert decision.urgency is urgency
        resolved += 1

    assert resolved == len(list(PacketClass)) * len(list(Urgency)) == 44


def test_routing_is_deterministic() -> None:
    for packet_class, urgency in itertools.product(PacketClass, Urgency):
        assert route(packet_class, urgency) == route(packet_class, urgency)


def test_no_pair_falls_through_to_none() -> None:
    assert all(
        route(packet_class, urgency) is not None
        for packet_class in PacketClass
        for urgency in Urgency
    )


def test_known_base_mappings() -> None:
    assert route(PacketClass.ALARM_TRIAGE, Urgency.ROUTINE).engine is EngineClass.TACTICAL
    assert route(PacketClass.LIVE_STATE, Urgency.URGENT).engine is EngineClass.TACTICAL
    assert route(PacketClass.ASSET_CONDITION, Urgency.ROUTINE).engine is EngineClass.REASONING
    assert route(PacketClass.ROOT_CAUSE, Urgency.URGENT).engine is EngineClass.REASONING
    assert route(PacketClass.ENERGY_ANALYSIS, Urgency.ROUTINE).engine is EngineClass.PLANNING
    assert route(PacketClass.MAINTENANCE_PLANNING, Urgency.URGENT).engine is EngineClass.PLANNING
    assert route(PacketClass.EXECUTIVE_SUMMARY, Urgency.ROUTINE).engine is EngineClass.BILINGUAL
    assert route(PacketClass.OPERATOR_QUERY, Urgency.ELEVATED).engine is EngineClass.BILINGUAL


def test_immediate_escalation_of_event_classes() -> None:
    # Event-driven classes escalate to TACTICAL at IMMEDIATE urgency...
    for packet_class in (
        PacketClass.POWER_QUALITY_EVENT,
        PacketClass.ANOMALY_INVESTIGATION,
    ):
        immediate = route(packet_class, Urgency.IMMEDIATE)
        assert immediate.engine is EngineClass.TACTICAL
        assert immediate.rule_id.endswith("IMMEDIATE-ESCALATION")
        # ...but remain on their base REASONING engine below IMMEDIATE.
        for urgency in (Urgency.ROUTINE, Urgency.ELEVATED, Urgency.URGENT):
            assert route(packet_class, urgency).engine is EngineClass.REASONING


def test_planning_class_not_escalated_by_immediate() -> None:
    assert route(PacketClass.RESILIENCE_SCENARIO, Urgency.IMMEDIATE).engine is EngineClass.PLANNING
