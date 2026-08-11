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
"""Tests for the synthetic reference facility FAC-001 (WP1.1 asset inventory).

Every value exercised here is synthetic (``DataProvenance.SYNTHETIC``); FAC-001
is not based on any real facility.
"""

from __future__ import annotations

import pytest

from packages.canonical_electrical_model import (
    Criticality,
    ElectricalNode,
    Facility,
    ProvenanceSource,
    RatedData,
    SourceNode,
    SourceType,
)
from packages.reference_facility import (
    ReferenceFacility,
    load_reference_facility,
)

# Loaded once; the facility is immutable in practice for these read-only checks.
FAC = load_reference_facility()


def test_load_returns_reference_facility() -> None:
    assert isinstance(FAC, ReferenceFacility)
    assert isinstance(FAC.facility, Facility)
    assert FAC.facility.id == "FAC-001"
    assert FAC.facility.sector_profile is not None
    assert FAC.facility.sector_profile.value == "MANUFACTURING"


def test_node_count_is_in_required_range() -> None:
    # WP1.1 requires "~48 nodes", node count between 45 and 52 inclusive.
    assert 45 <= len(FAC.nodes) <= 52


def test_every_node_is_a_canonical_electrical_node() -> None:
    assert FAC.nodes, "facility must define nodes"
    assert all(isinstance(node, ElectricalNode) for node in FAC.nodes)


def test_every_node_has_rated_data() -> None:
    for node in FAC.nodes:
        assert isinstance(node.rated, RatedData), f"{node.id} has no RatedData"


def test_every_node_has_criticality() -> None:
    for node in FAC.nodes:
        assert isinstance(node.criticality, Criticality), f"{node.id} has no Criticality"


def test_node_ids_are_unique() -> None:
    ids = [node.id for node in FAC.nodes]
    assert len(ids) == len(set(ids))


def test_both_transformers_have_non_null_losses() -> None:
    transformers = [n for n in FAC.nodes if n.id in {"TX-001", "TX-002"}]
    assert len(transformers) == 2
    for tx in transformers:
        assert tx.rated is not None
        assert tx.rated.no_load_loss_kw is not None, f"{tx.id} missing no_load_loss_kw"
        assert tx.rated.load_loss_kw is not None, f"{tx.id} missing load_loss_kw"
        assert tx.rated.no_load_loss_kw.value > 0.0
        assert tx.rated.load_loss_kw.value > 0.0


def test_intentional_metering_gap_is_present_and_documented() -> None:
    gap_id = FAC.metering.intentional_unmetered_branch_id
    assert gap_id == "MCC-003"
    # the gap references a real node that carries no dedicated sub-meter
    assert gap_id in FAC.node_ids
    assert FAC.unmetered_branch.id == gap_id
    assert not FAC.metering.is_metered(gap_id)
    # ... and it is explicitly documented as an untouchable test fixture
    assert FAC.metering.intentional_gap_is_test_fixture is True
    note = FAC.metering.note.lower()
    assert "test fixture" in note
    assert "must not" in note
    assert "unmetered" in note


def test_other_mccs_and_critical_board_are_metered() -> None:
    for metered in ("MCC-001", "MCC-002", "DB-003"):
        assert FAC.metering.is_metered(metered), f"{metered} should be sub-metered"


def test_meter_nodes_exist_for_every_submeter() -> None:
    for submeter in FAC.metering.submeters:
        assert submeter.meter_node_id in FAC.node_ids
        assert submeter.measures_node_id in FAC.node_ids
        assert FAC.node(submeter.meter_node_id).asset_type.value == "METER"


def test_sources_cover_the_backup_and_generation_chain() -> None:
    assert all(isinstance(s, SourceNode) for s in FAC.sources)
    source_types = {s.source_type for s in FAC.sources}
    assert {
        SourceType.UTILITY,
        SourceType.GENERATOR,
        SourceType.UPS,
        SourceType.BATTERY,
        SourceType.SOLAR_PV,
    } <= source_types
    # every source is attached to a node that exists in the inventory
    assert all(s.node_id in FAC.node_ids for s in FAC.sources)


def test_facility_frequency_defaults_to_60hz() -> None:
    assert FAC.facility.nominal_frequency_hz == 60.0


def test_facility_declares_the_three_voltage_levels() -> None:
    levels = set(FAC.facility.nominal_voltage_levels)
    assert {13800.0, 400.0, 230.0} <= levels


def test_all_data_is_labelled_synthetic() -> None:
    for node in FAC.nodes:
        assert node.provenance.source is ProvenanceSource.SYNTHETIC, node.id
        assert node.rated is not None
        for field_name in type(node.rated).model_fields:
            provenanced = getattr(node.rated, field_name)
            if provenanced is not None:
                assert provenanced.provenance.source is ProvenanceSource.SYNTHETIC


def test_critical_loads_are_marked_critical() -> None:
    db003 = FAC.node("DB-003")
    assert db003.criticality is Criticality.CRITICAL


def test_expected_key_assets_are_present() -> None:
    expected = {
        "UTIL-001",
        "MTR-MAIN-001",
        "SWGR-MV-001",
        "TX-001",
        "TX-002",
        "CB-TIE-001",
        "CAP-001",
        "HF-001",
        "GEN-001",
        "ATS-001",
        "UPS-001",
        "BATT-001",
        "PV-001",
        "INV-001",
        "MCC-001",
        "MCC-002",
        "MCC-003",
    }
    assert expected <= FAC.node_ids


def test_expected_asset_counts() -> None:
    def count(prefix: str) -> int:
        return sum(1 for n in FAC.nodes if n.id.startswith(prefix))

    assert count("M-") == 8  # M-001..M-008 motors
    assert count("VFD-") == 4  # VFD-001..VFD-004
    assert count("P-") == 3  # P-001..P-003 pumps
    assert count("CH-") == 2  # CH-001, CH-002 chillers


def test_edges_reference_existing_nodes() -> None:
    for edge in FAC.edges:
        assert edge.from_node_id in FAC.node_ids
        assert edge.to_node_id in FAC.node_ids
        if edge.switching_device_node_id is not None:
            assert edge.switching_device_node_id in FAC.node_ids


def test_bus_tie_is_normally_open() -> None:
    tie_edges = [e for e in FAC.edges if e.switching_device_node_id == "CB-TIE-001"]
    assert tie_edges, "expected a bus-tie edge governed by CB-TIE-001"
    assert all(e.switch_state.value == "OPEN" for e in tie_edges)


def test_load_is_deterministic() -> None:
    other = load_reference_facility()
    assert other.model_dump() == FAC.model_dump()


def test_unknown_node_lookup_raises() -> None:
    with pytest.raises(KeyError):
        FAC.node("does-not-exist")
