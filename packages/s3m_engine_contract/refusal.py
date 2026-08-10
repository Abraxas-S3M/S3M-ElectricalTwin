"""The refusal path: an explicit, grounded "we do not know yet" card.

When a packet cannot support a substantive recommendation, the engine must say
so plainly rather than improvise. :func:`insufficient_data_card` builds the
canonical refusal: an ``INSUFFICIENT_DATA`` card that makes no recommendation,
carries zero confidence, records why it is refusing, and -- by construction --
always passes the deterministic grounding gate.
"""

from __future__ import annotations

from collections.abc import Sequence

from packages.canonical_electrical_model import HealthBand, ValidationState

from .card import RecommendationCard, RecommendationConfidence
from .packet import ElectricalTwinPacket, compute_packet_hash
from .routing import route

__all__ = ["insufficient_data_card"]

_ZERO_CONFIDENCE = RecommendationConfidence(
    data_sufficiency=0.0,
    model_maturity=0.0,
    physics_agreement=0.0,
    historical_precedent=0.0,
)


def insufficient_data_card(
    packet: ElectricalTwinPacket,
    reasons: Sequence[str],
) -> RecommendationCard:
    """Build an ``INSUFFICIENT_DATA`` refusal card for *packet*.

    The card carries the health band ``INSUFFICIENT_DATA``, makes no
    recommendation, records *reasons* verbatim, has zero confidence components,
    and is marked as a preliminary demonstration artefact so it passes the
    grounding gate for both real and entirely-synthetic packets. It is
    deliberately free of claims and ranked causes so nothing can be ungrounded.
    """

    decision = route(packet.packet_class, packet.urgency)
    packet_hash = packet.packet_hash or compute_packet_hash(packet)
    reason_list = list(reasons)

    return RecommendationCard(
        id=f"insufficient-data-{packet.packet_id}",
        title="Insufficient data to advise",
        node_ids=list(packet.node_ids),
        urgency=packet.urgency,
        rationale=(
            "The available data does not support a substantive recommendation. "
            "S3M is declining to advise and is returning an explicit "
            "insufficient-data result rather than an unsupported one."
        ),
        evidence=[],
        ranked_causes=[],
        recommended_inspection=None,
        recommended_action=None,
        estimated_financial_exposure=None,
        health_band=HealthBand.INSUFFICIENT_DATA,
        is_demonstration=True,
        insufficient_data_reasons=reason_list,
        validation_state=ValidationState.INSUFFICIENT_DATA,
        packet_id=packet.packet_id,
        packet_hash=packet_hash,
        engine_class=decision.engine_class,
        routing_decision=decision,
        model_version="none",
        prompt_template_version="none",
        confidence=_ZERO_CONFIDENCE,
        claims=[],
    )
