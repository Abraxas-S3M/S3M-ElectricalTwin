"""Tests for the packet-to-engine routing table."""

from __future__ import annotations

from conftest import make_packet

from packages.s3m_engine_contract.packets import EngineClass, PacketClass
from packages.s3m_engine_contract.routing import (
    ROUTING_TABLE,
    route,
    routing_table_as_dicts,
)


def test_every_packet_class_has_a_route():
    for packet_class in PacketClass:
        assert packet_class in ROUTING_TABLE


def test_routing_entry_packet_class_matches_key():
    for packet_class, entry in ROUTING_TABLE.items():
        assert entry.packet_class is packet_class


def test_route_returns_entry_for_packet():
    packet = make_packet(packet_class=PacketClass.STEADY_STATE_LOADING)
    entry = route(packet)
    assert entry.engine_class is EngineClass.LOAD_FLOW_BALANCED


def test_fault_level_routes_to_short_circuit_engine():
    packet = make_packet(packet_class=PacketClass.FAULT_LEVEL)
    assert route(packet).engine_class is EngineClass.SHORT_CIRCUIT_IEC60909


def test_reasoning_packet_classes_route_to_s3m():
    for packet_class in (PacketClass.ASSET_HEALTH, PacketClass.ANOMALY_TRIAGE):
        packet = make_packet(packet_class=packet_class)
        assert route(packet).engine_class is EngineClass.S3M_REASONER


def test_load_flow_requires_validated_topology():
    assert ROUTING_TABLE[PacketClass.STEADY_STATE_LOADING].requires_validated_topology is True


def test_dispatch_does_not_require_validated_topology():
    assert ROUTING_TABLE[PacketClass.DISPATCH_ECONOMICS].requires_validated_topology is False


def test_routing_table_as_dicts_is_serialisable():
    rows = routing_table_as_dicts()
    assert len(rows) == len(ROUTING_TABLE)
    for row in rows:
        assert set(row.keys()) == {
            "packet_class",
            "engine_class",
            "requires_validated_topology",
            "rationale",
        }


def test_every_route_has_a_rationale():
    for entry in ROUTING_TABLE.values():
        assert entry.rationale.strip()
