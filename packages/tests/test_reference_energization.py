"""Tests for reference facility energization on the engineering solver."""

from __future__ import annotations

import pytest

from packages.electrical_engineering import EnergizationState
from packages.reference_facility import (
    UnknownVariantError,
    energization,
    energization_rows,
)


def test_normal_energizes_loads_from_primary() -> None:
    results = energization("normal")
    assert results["LOAD-A1"].state is EnergizationState.ENERGIZED_PRIMARY
    assert results["LOAD-B1"].state is EnergizationState.ENERGIZED_PRIMARY
    assert results["LOAD-CRIT1"].state is EnergizationState.ENERGIZED_PRIMARY


def test_utility_outage_energizes_from_backup_generator() -> None:
    results = energization("utility_outage")
    assert results["MSB"].state is EnergizationState.ENERGIZED_BACKUP
    assert results["LOAD-A1"].state is EnergizationState.ENERGIZED_BACKUP


def test_sensor_dropout_yields_indeterminate_downstream() -> None:
    results = energization("sensor_dropout")
    for node_id in ("XFMR-A", "PANEL-A", "LOAD-A1", "LOAD-A2"):
        assert results[node_id].state is EnergizationState.INDETERMINATE
    # Bus B side is unaffected and remains definitely energized.
    assert results["LOAD-B1"].state is EnergizationState.ENERGIZED_PRIMARY


def test_partial_maintenance_carries_bus_b_over_tie() -> None:
    results = energization("partial_maintenance")
    # Bus B main feeder is open; bus B is carried across the closed tie from A.
    assert results["BUS-B"].state is EnergizationState.ENERGIZED_PRIMARY
    assert results["LOAD-B1"].state is not EnergizationState.DE_ENERGIZED
    # The supply path to bus B now runs through bus A and the tie.
    assert "BUS-A" in results["BUS-B"].path


def test_energization_rows_are_sorted_and_serialisable() -> None:
    rows = energization_rows("normal")
    node_ids = [row["node_id"] for row in rows]
    assert node_ids == sorted(node_ids)
    for row in rows:
        assert set(row) == {
            "node_id",
            "state",
            "source_node_id",
            "path",
            "is_backfed",
            "indeterminate_reason",
        }
        assert isinstance(row["state"], str)


def test_energization_rows_unknown_variant_raises() -> None:
    with pytest.raises(UnknownVariantError):
        energization_rows("nope")
