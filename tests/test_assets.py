"""Tests for the canonical electrical asset graph."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from packages.canonical_electrical_model.assets import (
    Asset,
    AssetGraph,
    AssetType,
    Connection,
    EnergizationState,
)


def _graph() -> AssetGraph:
    return AssetGraph(
        assets=[
            Asset(asset_id="bus-1", asset_type=AssetType.BUSBAR, nominal_voltage_kv=11.0),
            Asset(
                asset_id="tx-1",
                asset_type=AssetType.TRANSFORMER,
                energization=EnergizationState.ENERGIZED,
            ),
        ],
        connections=[
            Connection(connection_id="c-1", from_asset_id="bus-1", to_asset_id="tx-1")
        ],
    )


def test_default_energization_is_unknown():
    asset = Asset(asset_id="a", asset_type=AssetType.LOAD)
    assert asset.energization is EnergizationState.UNKNOWN


def test_graph_lookup_returns_asset():
    graph = _graph()
    assert graph.asset("tx-1") is not None
    assert graph.asset("tx-1").asset_type is AssetType.TRANSFORMER


def test_graph_lookup_missing_returns_none():
    assert _graph().asset("nope") is None


def test_dangling_connection_rejected():
    with pytest.raises(ValidationError):
        AssetGraph(
            assets=[Asset(asset_id="bus-1", asset_type=AssetType.BUSBAR)],
            connections=[
                Connection(connection_id="c", from_asset_id="bus-1", to_asset_id="ghost")
            ],
        )


def test_duplicate_asset_id_rejected():
    with pytest.raises(ValidationError):
        AssetGraph(
            assets=[
                Asset(asset_id="dup", asset_type=AssetType.BUSBAR),
                Asset(asset_id="dup", asset_type=AssetType.LOAD),
            ]
        )


def test_energization_state_has_unknown_and_grounded():
    values = {state.value for state in EnergizationState}
    assert {"energized", "de_energized", "grounded", "unknown"} <= values


def test_asset_types_include_core_equipment():
    values = {t.value for t in AssetType}
    for expected in ("busbar", "transformer", "circuit_breaker", "feeder", "meter"):
        assert expected in values


def test_empty_asset_id_rejected():
    with pytest.raises(ValidationError):
        Asset(asset_id="", asset_type=AssetType.LOAD)
