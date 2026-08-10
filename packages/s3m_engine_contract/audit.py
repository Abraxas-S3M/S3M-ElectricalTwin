"""Tamper-evident audit chain for S3M reasoning invocations.

Every reasoning invocation appends one :class:`EngineAuditRecord` to an
append-only, hash-linked chain: each record commits to the previous record's
hash, so any later edit or reordering breaks the chain and is detected by
:meth:`EngineAuditChain.verify_chain`.

.. warning::

    **This is a WP0-only, in-memory implementation.** It exists to pin the audit
    *contract* and to prove the hash-chain semantics under test. It keeps the
    entire chain in process memory, is not concurrency-safe, and does not
    survive a restart. It **MUST be replaced by a durable, append-only,
    PostgreSQL-backed audit service** (with write-once storage and independent
    verification) **before any pilot deployment.** Do not rely on this module
    for any real auditability guarantee.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from .routing import RoutingDecision

__all__ = [
    "GENESIS_HASH",
    "EngineAuditRecord",
    "ChainVerification",
    "EngineAuditChain",
]

#: The previous-hash value of the first record in a chain.
GENESIS_HASH: str = "0" * 64


class EngineAuditRecord(BaseModel):
    """One append-only, hash-linked audit record for a reasoning invocation."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    sequence: int
    previous_hash: str
    record_hash: str
    packet_id: str
    packet_hash: str
    engine_class: str
    routing_decision: RoutingDecision
    model_version: str
    prompt_template_version: str
    invocation_fingerprint: str
    output_hash: str
    grounding_passed: bool
    violation_codes: list[str] = Field(default_factory=list)
    created_at: datetime
    actor: str

    def canonical_json(self) -> str:
        """Canonical JSON of the record excluding its own ``record_hash``."""

        payload = self.model_dump(mode="json", exclude={"record_hash"})
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        """Recompute this record's hash from its ``previous_hash`` and content."""

        digest = hashlib.sha256(
            (self.previous_hash + self.canonical_json()).encode("utf-8")
        )
        return digest.hexdigest()


class ChainVerification(BaseModel):
    """The outcome of verifying an audit chain."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    length: int
    broken_at: int | None = None
    reason: str = ""


class EngineAuditChain:
    """An append-only, in-memory, hash-linked chain of audit records.

    See the module docstring: this is a WP0-only implementation and must be
    replaced by a durable PostgreSQL-backed service before any pilot.
    """

    def __init__(self, genesis_hash: str = GENESIS_HASH) -> None:
        self._genesis_hash = genesis_hash
        self._records: list[EngineAuditRecord] = []

    def __len__(self) -> int:
        return len(self._records)

    @property
    def records(self) -> tuple[EngineAuditRecord, ...]:
        """An immutable view of the appended records."""

        return tuple(self._records)

    @property
    def head_hash(self) -> str:
        """The hash of the most recent record (or the genesis hash if empty)."""

        return self._records[-1].record_hash if self._records else self._genesis_hash

    def append(
        self,
        *,
        packet_id: str,
        packet_hash: str,
        engine_class: str,
        routing_decision: RoutingDecision,
        model_version: str,
        prompt_template_version: str,
        invocation_fingerprint: str,
        output_hash: str,
        grounding_passed: bool,
        violation_codes: list[str] | None = None,
        actor: str,
        created_at: datetime | None = None,
    ) -> EngineAuditRecord:
        """Append a new record, hash-linking it to the current head."""

        record = EngineAuditRecord(
            record_id=uuid.uuid4().hex,
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
            created_at=created_at or datetime.now(UTC),
            actor=actor,
        )
        record.record_hash = record.compute_hash()
        self._records.append(record)
        return record

    def verify_chain(self) -> ChainVerification:
        """Verify integrity and ordering, detecting tampering and reordering."""

        previous = self._genesis_hash
        for index, record in enumerate(self._records):
            if record.sequence != index:
                return ChainVerification(
                    valid=False,
                    length=len(self._records),
                    broken_at=index,
                    reason=(
                        f"Record at position {index} has sequence "
                        f"{record.sequence}; the chain has been reordered."
                    ),
                )
            if record.previous_hash != previous:
                return ChainVerification(
                    valid=False,
                    length=len(self._records),
                    broken_at=index,
                    reason=(
                        f"Record at position {index} does not link to its "
                        "predecessor; the chain has been reordered or truncated."
                    ),
                )
            if record.compute_hash() != record.record_hash:
                return ChainVerification(
                    valid=False,
                    length=len(self._records),
                    broken_at=index,
                    reason=(
                        f"Record at position {index} fails its hash check; its "
                        "contents have been tampered with."
                    ),
                )
            previous = record.record_hash

        return ChainVerification(valid=True, length=len(self._records))
