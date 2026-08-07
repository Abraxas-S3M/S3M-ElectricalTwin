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
