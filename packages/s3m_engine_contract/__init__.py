"""S3M engine contract for S3M ElectricalTwin (advisory, read-only).

S3M is the reasoning brain of the platform; this package defines the contract it
speaks through. It has three parts:

* :mod:`~packages.s3m_engine_contract.routing` -- a pure, deterministic, total
  mapping from a packet's class and urgency to the engine that handles it.
* :mod:`~packages.s3m_engine_contract.packet` -- the hashable bundle of observed
  facts (the ``evidence_pool`` being the only facts the engine may cite).
* :mod:`~packages.s3m_engine_contract.card` -- the advisory recommendation card,
  whose factual claims must be grounded in cited evidence.

No language model is invoked anywhere in this package. Everything is read-only:
artefacts carry the canonical :class:`ControlBoundary` and default to pending
operator review. All data is synthetic.
"""

from __future__ import annotations

from .card import (
    Claim,
    ClaimKind,
    FinancialExposure,
    GroundingReport,
    RecommendationCard,
    RecommendationConfidence,
)
from .packet import (
    DataSufficiency,
    ElectricalTwinPacket,
    ProvenanceSummary,
    compute_packet_hash,
)
from .routing import (
    ROUTING_TABLE,
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
    "ROUTING_TABLE",
    "route",
    # packet
    "ProvenanceSummary",
    "DataSufficiency",
    "ElectricalTwinPacket",
    "compute_packet_hash",
    # card
    "ClaimKind",
    "Claim",
    "GroundingReport",
    "FinancialExposure",
    "RecommendationConfidence",
    "RecommendationCard",
]
