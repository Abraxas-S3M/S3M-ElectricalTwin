"""Tests for the S3M engine-contract routing table."""

from __future__ import annotations

from packages.s3m_engine_contract.routing import (
    ROUTING_TABLE,
    EngineClass,
    PacketClass,
    RoutingDecision,
    Urgency,
    route,
)


def test_routing_is_total_across_every_pair():
    pairs = [(pc, u) for pc in PacketClass for u in Urgency]
    for packet_class, urgency in pairs:
        decision = route(packet_class, urgency)
        assert isinstance(decision, RoutingDecision)
        assert decision.engine_class in EngineClass
        assert decision.rule_id
        assert decision.rationale
        assert decision.packet_class is packet_class
        assert decision.urgency is urgency
    # Every pair resolved and the precomputed table has no gaps.
    assert len(ROUTING_TABLE) == len(pairs) == len(PacketClass) * len(Urgency)


def test_routing_is_deterministic():
    first = route(PacketClass.ROOT_CAUSE, Urgency.ROUTINE)
    second = route(PacketClass.ROOT_CAUSE, Urgency.ROUTINE)
    assert first == second


def test_urgency_escalates_diagnostic_packets_to_tactical():
    routine = route(PacketClass.ROOT_CAUSE, Urgency.ROUTINE)
    immediate = route(PacketClass.ROOT_CAUSE, Urgency.IMMEDIATE)
    assert routine.engine_class is EngineClass.REASONING
    assert immediate.engine_class is EngineClass.TACTICAL
    assert immediate.rule_id == "R5-URGENT-ESCALATION-TACTICAL"


def test_planning_and_bilingual_are_stable_across_urgency():
    for urgency in Urgency:
        assert route(PacketClass.ENERGY_ANALYSIS, urgency).engine_class is EngineClass.PLANNING
        assert route(PacketClass.OPERATOR_QUERY, urgency).engine_class is EngineClass.BILINGUAL
