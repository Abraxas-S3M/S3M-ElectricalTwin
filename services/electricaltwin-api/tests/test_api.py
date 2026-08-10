"""Endpoint tests for the advisory, read-only ElectricalTwin API."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

_client = TestClient(app)


def test_health_reports_read_only() -> None:
    response = _client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["read_only"] is True


def test_safety_exposes_control_boundary_and_advisory() -> None:
    response = _client.get("/safety")
    assert response.status_code == 200
    body = response.json()
    assert body["control_write_enabled"] is False
    assert "advisory" in body["advisory_statement"].lower()
    assert body["control_boundary"]["control_write_enabled"] is False
    assert body["control_boundary"]["requires_human_approval"] is True


def test_meta_provenance_lists_vocabularies_with_definitions() -> None:
    body = _client.get("/meta/provenance").json()
    assert {"data_provenance", "validation_state"} <= set(body)
    for entry in body["data_provenance"]:
        assert entry["value"] and entry["definition"]
    validation_values = {e["value"] for e in body["validation_state"]}
    assert "CALIBRATED" in validation_values
    assert "INSUFFICIENT_DATA" in validation_values


def test_engine_contract_exposes_full_routing_table() -> None:
    body = _client.get("/engine/contract").json()
    assert set(body["engine_classes"]) == {
        "TACTICAL",
        "REASONING",
        "PLANNING",
        "BILINGUAL",
    }
    # The routing table is total: every (packet_class, urgency) pair.
    expected = len(body["packet_classes"]) * len(body["urgency_levels"])
    assert len(body["routing_table"]) == expected


def test_grounding_rules_expose_every_check() -> None:
    body = _client.get("/engine/grounding-rules").json()
    codes = {check["code"] for check in body["checks"]}
    assert codes == {
        "EVIDENCE_RESOLUTION",
        "UNCITED_CLAIM",
        "NUMERIC_PROVENANCE",
        "ALTERNATIVES_REQUIRED",
        "FORBIDDEN_ASSERTION",
        "CONTROL_LANGUAGE",
        "SUFFICIENCY_FLOOR",
        "SYNTHETIC_LABEL",
    }
    for check in body["checks"]:
        assert check["definition"]
