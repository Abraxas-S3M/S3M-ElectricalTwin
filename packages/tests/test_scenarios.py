"""Ground-truth invariants for the thirteen seeded scenarios.

These tests treat the scenario catalogue as a benchmark contract: the labels
must be internally consistent (a fault cannot be detectable before it starts,
every referenced node must exist, the control must be truly clean) so that a
detector scored against them is being scored against something falsifiable.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from packages.reference_facility import (
    ALL_DETECTORS,
    Detector,
    FaultCategory,
    facility_node_ids,
)
from packages.reference_facility.scenarios import (
    ScenarioGroundTruth,
    all_scenarios,
    scenario_by_id,
    scenario_ids,
)

_SCENARIOS = all_scenarios()
_FAULT_SCENARIOS = [s for s in _SCENARIOS if not s.is_control()]
_EXPECTED_IDS = tuple(f"SC-{n:02d}" for n in range(13))


def _pid(scenario: ScenarioGroundTruth) -> str:
    return scenario.scenario_id


def test_exactly_thirteen_scenarios() -> None:
    assert len(_SCENARIOS) == 13


def test_scenario_ids_are_the_expected_set() -> None:
    assert scenario_ids() == _EXPECTED_IDS


def test_scenario_ids_unique() -> None:
    ids = [s.scenario_id for s in _SCENARIOS]
    assert len(ids) == len(set(ids))


def test_exactly_one_control_scenario() -> None:
    controls = [s for s in _SCENARIOS if s.is_control()]
    assert len(controls) == 1
    assert controls[0].scenario_id == "SC-00"


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_should_not_trigger_is_non_empty(scenario: ScenarioGroundTruth) -> None:
    assert len(scenario.should_not_trigger) > 0


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_should_not_trigger_entries_are_detectors(
    scenario: ScenarioGroundTruth,
) -> None:
    assert all(isinstance(d, Detector) for d in scenario.should_not_trigger)


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_should_not_trigger_has_no_duplicates(
    scenario: ScenarioGroundTruth,
) -> None:
    assert len(scenario.should_not_trigger) == len(set(scenario.should_not_trigger))


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_detectable_from_at_or_after_onset(
    scenario: ScenarioGroundTruth,
) -> None:
    if scenario.onset_at is None:
        assert scenario.detectable_from is None
    else:
        assert scenario.detectable_from is not None
        assert scenario.detectable_from >= scenario.onset_at


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_every_fault_node_exists_in_facility(
    scenario: ScenarioGroundTruth,
) -> None:
    ids = facility_node_ids()
    for node_id in scenario.fault_node_ids:
        assert node_id in ids


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_severity_and_narrative_present(
    scenario: ScenarioGroundTruth,
) -> None:
    assert scenario.severity.value
    assert scenario.narrative.strip()


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=_pid)
def test_fault_category_none_iff_control(
    scenario: ScenarioGroundTruth,
) -> None:
    is_none = scenario.fault_category is FaultCategory.NONE
    assert is_none == scenario.is_control()


def test_control_has_no_fault_nodes() -> None:
    sc00 = scenario_by_id("SC-00")
    assert sc00.fault_node_ids == ()


def test_control_expects_no_detector() -> None:
    sc00 = scenario_by_id("SC-00")
    assert sc00.expected_detector is None


def test_control_silences_every_detector() -> None:
    sc00 = scenario_by_id("SC-00")
    assert set(sc00.should_not_trigger) == set(ALL_DETECTORS)
    assert len(sc00.should_not_trigger) == len(ALL_DETECTORS)


@pytest.mark.parametrize("scenario", _FAULT_SCENARIOS, ids=_pid)
def test_fault_scenarios_have_fault_nodes(
    scenario: ScenarioGroundTruth,
) -> None:
    assert len(scenario.fault_node_ids) > 0


@pytest.mark.parametrize("scenario", _FAULT_SCENARIOS, ids=_pid)
def test_fault_scenarios_have_onset_and_detectable(
    scenario: ScenarioGroundTruth,
) -> None:
    assert scenario.onset_at is not None
    assert scenario.detectable_from is not None


@pytest.mark.parametrize("scenario", _FAULT_SCENARIOS, ids=_pid)
def test_fault_scenarios_name_an_expected_detector(
    scenario: ScenarioGroundTruth,
) -> None:
    assert scenario.expected_detector is not None


@pytest.mark.parametrize("scenario", _FAULT_SCENARIOS, ids=_pid)
def test_expected_detector_is_not_silenced(
    scenario: ScenarioGroundTruth,
) -> None:
    assert scenario.expected_detector not in scenario.should_not_trigger


@pytest.mark.parametrize("scenario", _FAULT_SCENARIOS, ids=_pid)
def test_expected_plus_silenced_covers_all_detectors(
    scenario: ScenarioGroundTruth,
) -> None:
    # For a single-fault scenario, exactly one detector fires and every other
    # detector must be listed as silent — no detector is left unaccounted for.
    covered = set(scenario.should_not_trigger) | {scenario.expected_detector}
    assert covered == set(ALL_DETECTORS)


def test_scenario_by_id_round_trips() -> None:
    for scenario in _SCENARIOS:
        assert scenario_by_id(scenario.scenario_id) is scenario


def test_scenario_by_id_unknown_raises() -> None:
    with pytest.raises(KeyError):
        scenario_by_id("SC-99")


def test_ground_truth_is_immutable() -> None:
    sc08 = scenario_by_id("SC-08")
    with pytest.raises(FrozenInstanceError):
        sc08.severity = FaultCategory.NONE  # type: ignore[misc]


def test_differentiator_sc08_exact() -> None:
    sc08 = scenario_by_id("SC-08")
    assert sc08.fault_category is FaultCategory.UNMETERED_LOAD
    assert sc08.fault_node_ids == ("MCC-003",)
    assert sc08.expected_detector is Detector.UNMETERED_LOAD


def test_differentiator_sc09_exact() -> None:
    sc09 = scenario_by_id("SC-09")
    assert sc09.fault_category is FaultCategory.POSITION_INCONSISTENCY
    assert sc09.fault_node_ids == ("CB-LV-005",)
    assert sc09.expected_detector is Detector.POSITION_CONSISTENCY
    # An impossible reported state is inconsistent the instant it appears.
    assert sc09.detectable_from == sc09.onset_at


def test_differentiator_sc11_exact() -> None:
    sc11 = scenario_by_id("SC-11")
    assert sc11.fault_category is FaultCategory.METER_DRIFT
    assert sc11.fault_node_ids == ("MTR-MCC-002",)
    assert sc11.expected_detector is Detector.METER_DRIFT
    # A slow drift is not detectable at onset; it needs weeks of divergence.
    assert sc11.detectable_from is not None and sc11.onset_at is not None
    assert sc11.detectable_from > sc11.onset_at
