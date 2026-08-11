"""Tests for the reference facility demonstration scenarios."""

from __future__ import annotations

import pytest

from packages.reference_facility import (
    TOPOLOGY_VARIANTS,
    UnknownScenarioError,
    all_scenarios,
    get_scenario,
    scenario_ids,
)


def test_at_least_eight_scenarios_present() -> None:
    assert len(all_scenarios()) >= 8


def test_sc_08_is_present() -> None:
    scenario = get_scenario("SC-08")
    assert scenario.scenario_id == "SC-08"
    assert scenario.title


def test_scenario_ids_are_unique_and_sorted() -> None:
    ids = scenario_ids()
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


def test_every_scenario_has_narrative_and_ground_truth() -> None:
    for scenario in all_scenarios():
        assert scenario.narrative
        assert scenario.ground_truth.summary
        assert scenario.ground_truth.root_cause
        assert scenario.ground_truth.expected_diagnosis
        assert "synthetic" in scenario.ground_truth.notes.lower()


def test_every_scenario_references_a_valid_variant() -> None:
    for scenario in all_scenarios():
        assert scenario.topology_variant in TOPOLOGY_VARIANTS


def test_every_scenario_has_monitored_points() -> None:
    for scenario in all_scenarios():
        assert scenario.monitored
        for point in scenario.monitored:
            assert point.node_id and point.channel and point.unit


def test_switching_event_fractions_are_within_window() -> None:
    for scenario in all_scenarios():
        for event in scenario.switching_events:
            assert 0.0 <= event.at_fraction < 1.0


def test_perturbation_windows_are_ordered() -> None:
    for scenario in all_scenarios():
        for perturbation in scenario.perturbations:
            assert 0.0 <= perturbation.start_fraction <= perturbation.end_fraction <= 1.0


def test_unknown_scenario_raises() -> None:
    with pytest.raises(UnknownScenarioError):
        get_scenario("SC-999")


def test_scenarios_serialise_to_json() -> None:
    for scenario in all_scenarios():
        payload = scenario.model_dump(mode="json")
        assert payload["scenario_id"]
        assert payload["ground_truth"]["summary"]
