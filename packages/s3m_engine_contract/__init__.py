"""The S3M engine contract: packets in, recommendation cards out.

This package defines the boundary between the S3M reasoning engine and the
operator. It contains:

* :mod:`~packages.s3m_engine_contract.cards` — the recommendation card, its
  claims, evidence and confidence model.
* :mod:`~packages.s3m_engine_contract.packets` — the input packet vocabulary,
  engine classes and urgency levels.
* :mod:`~packages.s3m_engine_contract.routing` — the packet-to-engine routing
  table.
* :mod:`~packages.s3m_engine_contract.grounding` — the deterministic grounding
  gate that sits between the engine and the operator.
* :mod:`~packages.s3m_engine_contract.determinism` — reproducibility guarantees.
* :mod:`~packages.s3m_engine_contract.refusal` — the insufficient-data card.
* :mod:`~packages.s3m_engine_contract.audit` — the append-only audit chain.

Work Package 0 contains **no LLM invocation**. It fixes the contract and the
guardrails only.
"""S3M ElectricalTwin engine contract.

The contract the S3M reasoning brain speaks through: deterministic engine
routing, the packet an engine consumes, and the recommendation card it emits.
No language model is invoked anywhere in this package.
"""

from __future__ import annotations

from .card import (
    ApprovalStatus,
    Claim,
    ClaimKind,
    FinancialExposure,
    GroundingReport,
    RankedCause,
    RecommendationCard,
    RecommendationConfidence,
    ValidationState,
)
from .packet import (
    ControlBoundary,
    DataSufficiency,
    ElectricalTwinPacket,
    Evidence,
    ProvenanceSummary,
    Reading,
    TopologyEdge,
    TopologyNode,
    TopologySnapshot,
    compute_packet_hash,
)
from .routing import (
    EngineClass,
    PacketClass,
    RoutingDecision,
    Urgency,
    route,
)

__all__ = [
    # routing
    "EngineClass",
    "PacketClass",
    "Urgency",
    "RoutingDecision",
    "route",
    # packet
    "ElectricalTwinPacket",
    "Reading",
    "TopologyNode",
    "TopologyEdge",
    "TopologySnapshot",
    "Evidence",
    "ProvenanceSummary",
    "DataSufficiency",
    "ControlBoundary",
    "compute_packet_hash",
    # card
    "RecommendationCard",
    "Claim",
    "ClaimKind",
    "RankedCause",
    "FinancialExposure",
    "GroundingReport",
    "RecommendationConfidence",
    "ValidationState",
    "ApprovalStatus",
]
"""S3M engine contract types for S3M ElectricalTwin (advisory, read-only).

Placeholder package. It defines the read-only contract between the analytics
engine and its consumers. No contract defined here may express a control-write
or actuation operation.
"""
