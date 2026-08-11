"""Endpoint tests for the read-only reference-facility API routes."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

_client = TestClient(app)


def test_reference_facility_returns_metadata_and_inventory() -> None:
    response = _client.get("/reference/facility")
    assert response.status_code == 200
    body = response.json()
    assert body["facility"]["id"]
    assert len(body["assets"]) >= 15
    assert body["sources"]
    assert "synthetic" in body["synthetic_notice"].lower()


def test_reference_topology_default_variant() -> None:
    response = _client.get("/reference/topology")
    assert response.status_code == 200
    body = response.json()
    assert body["variant"] == "normal"
    assert body["snapshot"]["nodes"]
    assert body["snapshot"]["edges"]


def test_reference_topology_named_variant() -> None:
    body = _client.get("/reference/topology", params={"variant": "utility_outage"}).json()
    tie = {e["id"]: e["switch_state"] for e in body["snapshot"]["edges"]}
    assert tie["E-GEN-MSB"] == "CLOSED"
    assert tie["E-UTIL-XFMR"] == "OPEN"


def test_reference_topology_unknown_variant_is_404() -> None:
    assert _client.get("/reference/topology", params={"variant": "nope"}).status_code == 404


def test_reference_energization_returns_solver_rows() -> None:
    response = _client.get("/reference/energization", params={"variant": "normal"})
    assert response.status_code == 200
    rows = {row["node_id"]: row for row in response.json()["results"]}
    assert rows["LOAD-A1"]["state"] == "ENERGIZED_PRIMARY"


def test_reference_energization_indeterminate_variant() -> None:
    body = _client.get(
        "/reference/energization", params={"variant": "sensor_dropout"}
    ).json()
    states = {row["node_id"]: row["state"] for row in body["results"]}
    assert states["PANEL-A"] == "INDETERMINATE"


def test_reference_energization_unknown_variant_is_404() -> None:
    response = _client.get("/reference/energization", params={"variant": "nope"})
    assert response.status_code == 404


def test_reference_scenarios_lists_scenarios_with_ground_truth() -> None:
    body = _client.get("/reference/scenarios").json()
    ids = {scenario["scenario_id"] for scenario in body["scenarios"]}
    assert "SC-08" in ids
    for scenario in body["scenarios"]:
        assert scenario["narrative"]
        assert scenario["ground_truth"]["summary"]


def test_reference_replay_manifest_returns_hash_without_data() -> None:
    response = _client.get(
        "/reference/replay/manifest",
        params={
            "scenario_id": "SC-08",
            "seed": 42,
            "start": "2026-01-05T00:00:00",
            "end": "2026-01-06T00:00:00",
            "interval_s": 300,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["result_hash"]) == 64
    assert body["reading_count"] > 0
    assert "readings" not in body
    assert body["monitored_points"]


def test_reference_replay_manifest_is_reproducible() -> None:
    params = {
        "scenario_id": "SC-08",
        "seed": 42,
        "start": "2026-01-05T00:00:00",
        "end": "2026-01-06T00:00:00",
        "interval_s": 300,
    }
    first = _client.get("/reference/replay/manifest", params=params).json()
    second = _client.get("/reference/replay/manifest", params=params).json()
    assert first["result_hash"] == second["result_hash"]


def test_reference_replay_manifest_unknown_scenario_is_404() -> None:
    response = _client.get(
        "/reference/replay/manifest",
        params={
            "scenario_id": "SC-999",
            "seed": 1,
            "start": "2026-01-05T00:00:00",
            "end": "2026-01-06T00:00:00",
            "interval_s": 60,
        },
    )
    assert response.status_code == 404


def test_reference_replay_manifest_invalid_window_is_400() -> None:
    response = _client.get(
        "/reference/replay/manifest",
        params={
            "scenario_id": "SC-01",
            "seed": 1,
            "start": "2026-01-06T00:00:00",
            "end": "2026-01-05T00:00:00",
            "interval_s": 60,
        },
    )
    assert response.status_code == 400


def test_reference_routes_are_read_only_get_only() -> None:
    # A POST to any reference route must not be allowed (read-only service).
    assert _client.post("/reference/facility").status_code == 405
    assert _client.post("/reference/scenarios").status_code == 405
