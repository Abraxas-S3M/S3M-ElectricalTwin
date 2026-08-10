"""Tests for the read-only ElectricalTwin API."""

from __future__ import annotations

import pytest
from app.main import create_app
from fastapi.testclient import TestClient

from packages.s3m_engine_contract.grounding import GROUNDING_RULE_DEFINITIONS
from packages.s3m_engine_contract.packets import EngineClass, PacketClass, UrgencyLevel


@pytest.fixture()
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["posture"] == "advisory-read-only"


def test_safety_reports_read_only(client: TestClient):
    response = client.get("/safety")
    assert response.status_code == 200
    body = response.json()
    assert body["control_write_enabled"] is False
    assert "read-only" in body["advisory_statement"]
    assert body["prohibited_actions"]


def test_meta_provenance_lists_vocabularies(client: TestClient):
    body = client.get("/meta/provenance").json()
    assert "data_provenance" in body
    assert "validation_state" in body
    assert body["data_provenance"]["synthetic"]


def test_engine_contract_lists_everything(client: TestClient):
    body = client.get("/engine/contract").json()
    assert set(body["engine_classes"]) == {e.value for e in EngineClass}
    assert set(body["packet_classes"]) == {p.value for p in PacketClass}
    assert set(body["urgency_levels"]) == {u.value for u in UrgencyLevel}
    assert len(body["routing_table"]) == len(PacketClass)


def test_grounding_rules_lists_every_check(client: TestClient):
    body = client.get("/engine/grounding-rules").json()
    returned = {rule["code"] for rule in body["rules"]}
    assert returned == set(GROUNDING_RULE_DEFINITIONS.keys())
    for rule in body["rules"]:
        assert rule["definition"].strip()


def test_only_get_methods_allowed(client: TestClient):
    # A POST to a read-only endpoint must not be accepted.
    assert client.post("/safety").status_code in (404, 405)


def test_all_documented_endpoints_available(client: TestClient):
    for path in ("/health", "/safety", "/meta/provenance", "/engine/contract", "/engine/grounding-rules"):
        assert client.get(path).status_code == 200
