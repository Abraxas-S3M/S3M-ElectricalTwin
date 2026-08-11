"""Tests for reference facility topology variants."""

from __future__ import annotations

import pytest

from packages.canonical_electrical_model import SwitchState
from packages.reference_facility import (
    TOPOLOGY_VARIANTS,
    UnknownVariantError,
    build_snapshot,
    topology,
)


def _switch_state(snapshot, edge_id: str) -> SwitchState:
    for edge in snapshot.edges:
        if edge.id == edge_id:
            return edge.switch_state
    raise AssertionError(f"edge {edge_id} not found")


def test_all_variants_resolve() -> None:
    for variant in TOPOLOGY_VARIANTS:
        snapshot = topology(variant)
        assert snapshot.facility_id
        assert snapshot.nodes
        assert snapshot.edges


def test_normal_variant_matches_base_configuration() -> None:
    snapshot = topology("normal")
    assert _switch_state(snapshot, "E-UTIL-XFMR") is SwitchState.CLOSED
    assert _switch_state(snapshot, "E-GEN-MSB") is SwitchState.OPEN
    assert _switch_state(snapshot, "E-TIE-AB") is SwitchState.OPEN


def test_utility_outage_variant_swaps_source() -> None:
    snapshot = topology("utility_outage")
    assert _switch_state(snapshot, "E-UTIL-XFMR") is SwitchState.OPEN
    assert _switch_state(snapshot, "E-GEN-MSB") is SwitchState.CLOSED


def test_tie_closed_variant_closes_tie() -> None:
    assert _switch_state(topology("tie_closed"), "E-TIE-AB") is SwitchState.CLOSED


def test_partial_maintenance_variant_opens_feeder_and_closes_tie() -> None:
    snapshot = topology("partial_maintenance")
    assert _switch_state(snapshot, "E-MSB-BUSB") is SwitchState.OPEN
    assert _switch_state(snapshot, "E-TIE-AB") is SwitchState.CLOSED


def test_sensor_dropout_variant_marks_feeder_unknown() -> None:
    assert _switch_state(topology("sensor_dropout"), "E-BUSA-XFMRA") is SwitchState.UNKNOWN


def test_unknown_variant_raises() -> None:
    with pytest.raises(UnknownVariantError):
        topology("does-not-exist")


def test_variants_share_identical_node_and_edge_inventory() -> None:
    normal = topology("normal")
    outage = topology("utility_outage")
    assert {n.id for n in normal.nodes} == {n.id for n in outage.nodes}
    assert {e.id for e in normal.edges} == {e.id for e in outage.edges}


def test_build_snapshot_rejects_unknown_edge_override() -> None:
    with pytest.raises(KeyError):
        build_snapshot({"E-DOES-NOT-EXIST": SwitchState.OPEN})


def test_build_snapshot_applies_override() -> None:
    snapshot = build_snapshot({"E-TIE-AB": SwitchState.CLOSED})
    assert _switch_state(snapshot, "E-TIE-AB") is SwitchState.CLOSED
