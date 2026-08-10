"""The insufficient-data card — the platform's honest refusal.

When the evidence does not support a substantive answer, the correct output is
not a hedged guess but an explicit refusal. :func:`insufficient_data_card`
constructs a card that carries no recommendations, zero confidence and
populated reasons, and that is guaranteed to pass the grounding gate.
"""

from __future__ import annotations

import uuid

from packages.s3m_engine_contract.cards import (
    CardStatus,
    ConfidenceComponents,
    HealthBand,
    ProvenanceSummary,
    RecommendationCard,
)
from packages.s3m_engine_contract.grounding import DEMONSTRATION_MARKER
from packages.s3m_engine_contract.packets import EnginePacket


def insufficient_data_card(
    packet: EnginePacket, reasons: list[str]
) -> RecommendationCard:
    """Return a grounded ``INSUFFICIENT_DATA`` card for ``packet``.

    The card makes no claims and no recommendations, so there is nothing for the
    grounding gate to flag. If the packet is entirely synthetic the card is
    additionally marked ``PRELIMINARY`` with a demonstration marker so that it
    also satisfies the synthetic-label rule.
    """

    is_synthetic = packet.provenance_summary.is_entirely_synthetic
    provenance = ProvenanceSummary(
        is_entirely_synthetic=is_synthetic,
        data_sufficiency=packet.provenance_summary.data_sufficiency,
        dominant_provenance=packet.provenance_summary.dominant_provenance,
        dominant_validation_state=packet.provenance_summary.dominant_validation_state,
    )

    populated_reasons = list(reasons) if reasons else [
        "The available evidence is insufficient to support a substantive finding."
    ]

    return RecommendationCard(
        card_id=f"card-{uuid.uuid4().hex}",
        packet_id=packet.packet_id,
        health_band=HealthBand.INSUFFICIENT_DATA,
        status=CardStatus.PRELIMINARY if is_synthetic else CardStatus.PROVISIONAL,
        headline="Insufficient data to reach a substantive conclusion.",
        claims=[],
        recommendations=[],
        alternatives=[],
        refuting_evidence_considered=[],
        confidence=ConfidenceComponents.zero(),
        provenance_summary=provenance,
        reasons=populated_reasons,
        demonstration_marker=DEMONSTRATION_MARKER if is_synthetic else None,
    )
