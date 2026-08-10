"""Tests for the tamper-evident, append-only audit chain."""

from __future__ import annotations

from packages.s3m_engine_contract.audit import EngineAuditChain
from packages.s3m_engine_contract.determinism import invocation_fingerprint
from packages.s3m_engine_contract.routing import PacketClass, Urgency, route


def _chain_with(n: int) -> EngineAuditChain:
    chain = EngineAuditChain()
    for i in range(n):
        decision = route(PacketClass.ASSET_CONDITION, Urgency.ROUTINE)
        chain.append(
            packet_id=f"pkt-{i}",
            packet_hash=f"{i:064x}",
            engine_class=decision.engine_class.value,
            routing_decision=decision,
            model_version="model-1",
            prompt_template_version="tmpl-1",
            invocation_fingerprint=invocation_fingerprint(
                f"{i:064x}", "tmpl-1", "model-1", decision.engine_class.value
            ),
            output_hash=f"out-{i}",
            grounding_passed=True,
            violation_codes=[],
            actor="s3m-engine",
        )
    return chain


def test_fresh_chain_verifies() -> None:
    chain = _chain_with(3)
    result = chain.verify_chain()
    assert result.valid is True
    assert result.length == 3
    assert result.broken_at is None


def test_records_are_hash_linked() -> None:
    chain = _chain_with(3)
    records = chain.records
    assert records[0].previous_hash == "0" * 64
    for earlier, later in zip(records, records[1:], strict=False):
        assert later.previous_hash == earlier.record_hash


def test_audit_chain_detects_a_tampered_record() -> None:
    chain = _chain_with(3)
    # Tamper with a record's payload after it was committed.
    chain.records[1].output_hash = "tampered-output"
    result = chain.verify_chain()
    assert result.valid is False
    assert result.broken_at == 1
    assert "tamper" in result.reason.lower()


def test_audit_chain_detects_a_reordered_record() -> None:
    chain = _chain_with(3)
    records = chain._records  # noqa: SLF001 - test reaches in to simulate reordering
    records[0], records[1] = records[1], records[0]
    result = chain.verify_chain()
    assert result.valid is False
    assert result.broken_at is not None
