"""Input packets, engine classes and urgency levels.

An :class:`EnginePacket` is the unit of work handed to the reasoning engine. It
carries the evidence pool, the provenance roll-up and enough context for the
:mod:`packages.s3m_engine_contract.routing` table to select an engine. The
engine classes here name the *validated calculators* the platform delegates to
plus the S3M reasoner itself; S3M reasons, the validated engines calculate (see
``docs/adr/ADR-0002`` and ``docs/adr/ADR-0006``).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from packages.s3m_engine_contract.cards import Evidence, ProvenanceSummary


class EngineClass(str, Enum):
    """The engines the platform can route a packet to.

    The physics engines are validated, licensed-open-source calculators (see
    ``docs/adr/ADR-0003``). ``S3M_REASONER`` is the reasoning brain: it frames
    questions, weighs evidence and composes cards, but it does not calculate
    physical results itself.
    """

    LOAD_FLOW_BALANCED = "load_flow_balanced"
    SHORT_CIRCUIT_IEC60909 = "short_circuit_iec60909"
    CONTINGENCY_N1 = "contingency_n1"
    UNBALANCED_HARMONICS = "unbalanced_harmonics"
    DISPATCH_STORAGE = "dispatch_storage"
    S3M_REASONER = "s3m_reasoner"


class PacketClass(str, Enum):
    """The kinds of analysis a packet can request."""

    STEADY_STATE_LOADING = "steady_state_loading"
    FAULT_LEVEL = "fault_level"
    CONTINGENCY_N1 = "contingency_n1"
    POWER_QUALITY = "power_quality"
    DISPATCH_ECONOMICS = "dispatch_economics"
    ASSET_HEALTH = "asset_health"
    ANOMALY_TRIAGE = "anomaly_triage"


class UrgencyLevel(str, Enum):
    """Advisory urgency. These describe how promptly a human should look; they
    never authorise or imply automated action."""

    ROUTINE = "routine"
    ELEVATED = "elevated"
    URGENT = "urgent"
    IMMEDIATE_REVIEW = "immediate_review"


class EnginePacket(BaseModel):
    """A unit of work submitted to the reasoning engine."""

    model_config = {"frozen": True}

    packet_id: str = Field(..., min_length=1)
    packet_class: PacketClass
    urgency: UrgencyLevel = UrgencyLevel.ROUTINE
    evidence_pool: list[Evidence] = Field(default_factory=list)
    provenance_summary: ProvenanceSummary = Field(default_factory=ProvenanceSummary)
    topology_validated: bool = False

    def evidence(self, evidence_id: str) -> Evidence | None:
        """Return the pooled evidence with ``evidence_id`` or ``None``."""

        for item in self.evidence_pool:
            if item.evidence_id == evidence_id:
                return item
        return None

    @property
    def evidence_ids(self) -> frozenset[str]:
        """The set of evidence ids present in the pool."""

        return frozenset(item.evidence_id for item in self.evidence_pool)
