"""Tests for the append-only audit chain."""

from __future__ import annotations

from packages.s3m_engine_contract.audit import (
    GENESIS_HASH,
    AuditChain,
    VerificationIssueKind,
)


def _append(chain: AuditChain, packet_id: str = "pkt-1") -> None:
    chain.append(
        packet_id=packet_id,
        packet_hash=f"hash-of-{packet_id}",
        engine_class="s3m_reasoner",
        routing_decision="asset_health->s3m_reasoner",
        model_version="s3m-reasoner-2026.08.0",
        prompt_template_version="card-v1",
        invocation_fingerprint="fp-" + packet_id,
        output_hash="out-" + packet_id,
        grounding_passed=True,
        violation_codes=[],
    )


def _three_record_chain() -> AuditChain:
    chain = AuditChain()
    _append(chain, "pkt-1")
    _append(chain, "pkt-2")
    _append(chain, "pkt-3")
    return chain


def test_empty_chain_head_is_genesis():
    assert AuditChain().head_hash == GENESIS_HASH


def test_first_record_links_to_genesis():
    chain = AuditChain()
    _append(chain)
    assert chain.records()[0].previous_hash == GENESIS_HASH


def test_records_are_sequenced():
    chain = _three_record_chain()
    assert [r.sequence for r in chain.records()] == [0, 1, 2]


def test_each_record_links_to_previous():
    chain = _three_record_chain()
    records = chain.records()
    assert records[1].previous_hash == records[0].record_hash
    assert records[2].previous_hash == records[1].record_hash


def test_valid_chain_verifies():
    chain = _three_record_chain()
    result = chain.verify_chain()
    assert result.valid is True
    assert result.issues == []


def test_audit_chain_detects_a_tampered_record():
    chain = _three_record_chain()
    records = list(chain.records())
    # Mutate a field but keep the old (now stale) record_hash.
    tampered = records[1].model_copy(update={"output_hash": "out-forged"})
    records[1] = tampered
    forged_chain = AuditChain.from_records(records)
    result = forged_chain.verify_chain()
    assert result.valid is False
    assert any(i.kind is VerificationIssueKind.TAMPERED for i in result.issues)


def test_audit_chain_detects_a_reordered_record():
    chain = _three_record_chain()
    records = list(chain.records())
    records[0], records[1] = records[1], records[0]
    reordered_chain = AuditChain.from_records(records)
    result = reordered_chain.verify_chain()
    assert result.valid is False
    assert any(i.kind is VerificationIssueKind.REORDERED for i in result.issues)


def test_record_hash_is_hex_sha256():
    chain = AuditChain()
    _append(chain)
    record_hash = chain.records()[0].record_hash
    assert len(record_hash) == 64
    int(record_hash, 16)


def test_recompute_hash_matches_stored_for_untampered():
    chain = _three_record_chain()
    for record in chain.records():
        assert record.compute_hash() == record.record_hash


def test_records_returns_immutable_tuple():
    chain = _three_record_chain()
    assert isinstance(chain.records(), tuple)


def test_violation_codes_recorded():
    chain = AuditChain()
    chain.append(
        packet_id="pkt-9",
        packet_hash="h",
        engine_class="s3m_reasoner",
        routing_decision="x",
        model_version="v1",
        prompt_template_version="p1",
        invocation_fingerprint="fp",
        output_hash="o",
        grounding_passed=False,
        violation_codes=["CONTROL_LANGUAGE"],
    )
    assert chain.records()[0].violation_codes == ["CONTROL_LANGUAGE"]
