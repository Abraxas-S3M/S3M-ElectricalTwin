"""Tests for the engine packet model and vocabularies."""

from __future__ import annotations

from conftest import make_packet

from packages.s3m_engine_contract.packets import (
    EngineClass,
    PacketClass,
    UrgencyLevel,
)


def test_packet_evidence_lookup():
    packet = make_packet()
    assert packet.evidence("ev-load-pct") is not None
    assert packet.evidence("nope") is None


def test_packet_evidence_ids_set():
    packet = make_packet()
    assert "ev-top-oil-temp" in packet.evidence_ids
    assert isinstance(packet.evidence_ids, frozenset)


def test_urgency_levels_are_advisory():
    values = {level.value for level in UrgencyLevel}
    assert "immediate_review" in values
    assert "routine" in values


def test_engine_classes_include_all_physics_and_reasoner():
    values = {engine.value for engine in EngineClass}
    for expected in (
        "load_flow_balanced",
        "short_circuit_iec60909",
        "contingency_n1",
        "unbalanced_harmonics",
        "dispatch_storage",
        "s3m_reasoner",
    ):
        assert expected in values


def test_packet_classes_cover_expected_analyses():
    values = {p.value for p in PacketClass}
    for expected in ("steady_state_loading", "fault_level", "power_quality", "asset_health"):
        assert expected in values


def test_packet_defaults_topology_unvalidated():
    packet = make_packet()
    assert packet.topology_validated is False
