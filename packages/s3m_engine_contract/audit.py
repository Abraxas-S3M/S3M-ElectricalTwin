"""Append-only audit chain for reasoning invocations.

.. warning::

   **This is a Work-Package-0 in-memory implementation only.** It exists to fix
   the audit-record shape and the hash-chaining semantics so the rest of the
   platform can be built and tested against a stable interface. It keeps the
   entire chain in process memory and loses it on restart. It **must be replaced
   by a durable, PostgreSQL-backed append-only audit service before any pilot
   deployment.** This limitation is also recorded in the project ``README.md``.

Each :class:`EngineAuditRecord` is linked to its predecessor by a hash:
``record_hash = sha256(previous_hash + canonical_json(record))`` where
``canonical_json(record)`` is the record's canonical JSON serialisation with the
``record_hash`` field itself excluded. :meth:`AuditChain.verify_chain` recomputes
every hash and re-checks every link, so both tampering (a mutated field) and
reordering (two records swapped) are detected.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

#: The hash that precedes the first record in a chain.
GENESIS_HASH: str = "0" * 64


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def canonical_json(payload: dict[str, Any]) -> str:
    """Return a canonical, stable JSON string for ``payload``."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


class EngineAuditRecord(BaseModel):
    """One immutable entry in the audit chain."""

    model_config = {"frozen": True}

    record_id: str
    sequence: int = Field(..., ge=0)
    previous_hash: str
    record_hash: str
    packet_id: str
    packet_hash: str
    engine_class: str
    routing_decision: str
    model_version: str
    prompt_template_version: str
    invocation_fingerprint: str
    output_hash: str
    grounding_passed: bool
    violation_codes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    actor: str = "s3m-engine"

    def _hashable_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"record_hash"})

    def compute_hash(self) -> str:
        """Recompute this record's hash from its fields and ``previous_hash``."""

        material = self.previous_hash + canonical_json(self._hashable_payload())
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


class VerificationIssueKind(str, Enum):
    """Why a chain failed verification."""

    TAMPERED = "tampered"
    REORDERED = "reordered"
    SEQUENCE = "sequence"


class VerificationIssue(BaseModel):
    """A single detected problem in a chain."""

    model_config = {"frozen": True}

    index: int
    record_id: str
    kind: VerificationIssueKind
    detail: str


class ChainVerification(BaseModel):
    """The result of verifying a chain."""

    valid: bool
    issues: list[VerificationIssue] = Field(default_factory=list)


class AuditChain:
    """An append-only, hash-linked, in-memory chain of audit records.

    See the module docstring: this implementation is for Work Package 0 only and
    must be replaced by a durable PostgreSQL-backed service before any pilot.
    """

    def __init__(self) -> None:
        self._records: list[EngineAuditRecord] = []

    @property
    def head_hash(self) -> str:
        """The hash of the last record, or the genesis hash if empty."""

        if not self._records:
            return GENESIS_HASH
        return self._records[-1].record_hash

    def records(self) -> tuple[EngineAuditRecord, ...]:
        """Return the records as an immutable tuple."""

        return tuple(self._records)

    def append(
        self,
        *,
        packet_id: str,
        packet_hash: str,
        engine_class: str,
        routing_decision: str,
        model_version: str,
        prompt_template_version: str,
        invocation_fingerprint: str,
        output_hash: str,
        grounding_passed: bool,
        violation_codes: list[str] | None = None,
        actor: str = "s3m-engine",
        record_id: str | None = None,
        created_at: datetime | None = None,
    ) -> EngineAuditRecord:
        """Append a new record, linking it to the current head."""

        draft = EngineAuditRecord(
            record_id=record_id or f"audit-{uuid.uuid4().hex}",
            sequence=len(self._records),
            previous_hash=self.head_hash,
            record_hash="",
            packet_id=packet_id,
            packet_hash=packet_hash,
            engine_class=engine_class,
            routing_decision=routing_decision,
            model_version=model_version,
            prompt_template_version=prompt_template_version,
            invocation_fingerprint=invocation_fingerprint,
            output_hash=output_hash,
            grounding_passed=grounding_passed,
            violation_codes=list(violation_codes or []),
            created_at=created_at or _utcnow(),
            actor=actor,
        )
        sealed = draft.model_copy(update={"record_hash": draft.compute_hash()})
        self._records.append(sealed)
        return sealed

    @classmethod
    def from_records(cls, records: list[EngineAuditRecord]) -> AuditChain:
        """Build a chain from existing records without re-sealing them.

        This is primarily used by tests to construct tampered or reordered
        chains; it deliberately does not recompute hashes.
        """

        chain = cls()
        chain._records = list(records)
        return chain

    def verify_chain(self) -> ChainVerification:
        """Verify integrity: recompute every hash and re-check every link."""

        issues: list[VerificationIssue] = []
        expected_previous = GENESIS_HASH

        for index, record in enumerate(self._records):
            if record.compute_hash() != record.record_hash:
                issues.append(
                    VerificationIssue(
                        index=index,
                        record_id=record.record_id,
                        kind=VerificationIssueKind.TAMPERED,
                        detail=(
                            "stored record_hash does not match the hash "
                            "recomputed from the record's fields"
                        ),
                    )
                )
            if record.previous_hash != expected_previous:
                issues.append(
                    VerificationIssue(
                        index=index,
                        record_id=record.record_id,
                        kind=VerificationIssueKind.REORDERED,
                        detail=(
                            "previous_hash does not match the preceding record's "
                            "hash; the chain link is broken or records were "
                            "reordered"
                        ),
                    )
                )
            if record.sequence != index:
                issues.append(
                    VerificationIssue(
                        index=index,
                        record_id=record.record_id,
                        kind=VerificationIssueKind.SEQUENCE,
                        detail=(
                            f"record sequence {record.sequence} does not match its "
                            f"position {index} in the chain"
                        ),
                    )
                )
            expected_previous = record.record_hash

        return ChainVerification(valid=not issues, issues=issues)
