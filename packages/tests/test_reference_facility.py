"""Tests for the reference facility metadata and asset inventory."""

from __future__ import annotations

from packages.canonical_electrical_model import AssetType, SourceType
from packages.reference_facility import (
    FACILITY_ID,
    base_edges,
    base_nodes,
    base_sources,
    facility,
)


def test_facility_metadata_is_synthetic_and_stable() -> None:
    fac = facility()
    assert fac.id == FACILITY_ID
    assert "synthetic" in fac.name.lower()
    assert fac.nominal_frequency_hz == 60.0
    assert 480.0 in fac.nominal_voltage_levels


def test_asset_inventory_is_non_empty_and_belongs_to_facility() -> None:
    nodes = base_nodes()
    assert len(nodes) >= 15
    assert all(node.parent_facility_id == FACILITY_ID for node in nodes)


def test_node_ids_are_unique() -> None:
    ids = [node.id for node in base_nodes()]
    assert len(ids) == len(set(ids))


def test_edge_ids_are_unique_and_reference_known_nodes() -> None:
    node_ids = {node.id for node in base_nodes()}
    edges = base_edges()
    edge_ids = [edge.id for edge in edges]
    assert len(edge_ids) == len(set(edge_ids))
    for edge in edges:
        assert edge.from_node_id in node_ids
        assert edge.to_node_id in node_ids


def test_sources_reference_known_nodes_and_expected_types() -> None:
    node_ids = {node.id for node in base_nodes()}
    sources = base_sources()
    types = {source.source_type for source in sources}
    assert types == {SourceType.UTILITY, SourceType.GENERATOR, SourceType.UPS}
    for source in sources:
        assert source.node_id in node_ids


def test_inventory_contains_expected_asset_types() -> None:
    asset_types = {node.asset_type for node in base_nodes()}
    assert AssetType.UTILITY_SERVICE in asset_types
    assert AssetType.GENERATOR in asset_types
    assert AssetType.UPS in asset_types
    assert AssetType.TRANSFORMER in asset_types


def test_accessors_return_fresh_copies() -> None:
    first = base_nodes()
    first[0].name = "MUTATED"
    second = base_nodes()
    assert second[0].name != "MUTATED"
