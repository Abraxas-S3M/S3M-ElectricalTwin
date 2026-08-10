"""Tests for the RecommendationCard grounding and confidence invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from packages.canonical_electrical_model import ApprovalStatus
from packages.s3m_engine_contract.card import (
    Claim,
    ClaimKind,
    RecommendationCard,
    RecommendationConfidence,
)
from packages.s3m_engine_contract.routing import (
    EngineClass,
    PacketClass,
    Urgency,
    route,
)


def _confidence() -> RecommendationConfidence:
    return RecommendationConfidence(
        data_sufficiency=0.8,
        model_maturity=0.4,
        physics_agreement=0.9,
        historical_precedent=0.7,
    )


def _card(claims):
    decision = route(PacketClass.ROOT_CAUSE, Urgency.URGENT)
    return RecommendationCard(
        id="card-1",
        title="Investigate feeder overheating",
        node_ids=["n1"],
        urgency=Urgency.URGENT,
        rationale="Synthetic advisory rationale.",
        packet_id="pkt-1",
        packet_hash="0" * 64,
        engine_class=decision.engine_class,
        routing_decision=decision,
        confidence=_confidence(),
        claims=claims,
    )


def test_card_with_uncited_numeric_claim_fails_validation():
    with pytest.raises(ValidationError):
        _card([Claim(claim_id="c1", text="Load is 250 A", claim_kind=ClaimKind.NUMERIC)])


def test_card_with_uncited_categorical_or_causal_claim_fails():
    with pytest.raises(ValidationError):
        _card(
            [
                Claim(
                    claim_id="c2",
                    text="Transformer is degraded",
                    claim_kind=ClaimKind.CATEGORICAL,
                )
            ]
        )
    with pytest.raises(ValidationError):
        _card(
            [
                Claim(
                    claim_id="c3",
                    text="Sag caused by upstream fault",
                    claim_kind=ClaimKind.CAUSAL,
                )
            ]
        )


def test_card_with_cited_factual_claims_is_valid():
    card = _card(
        [
            Claim(
                claim_id="c1",
                text="Load is 250 A",
                claim_kind=ClaimKind.NUMERIC,
                evidence_ids=["e1"],
            ),
            Claim(
                claim_id="c4",
                text="Consider a thermal inspection",
                claim_kind=ClaimKind.RECOMMENDATION,
            ),
            Claim(claim_id="c5", text="During peak demand", claim_kind=ClaimKind.CONTEXTUAL),
        ]
    )
    assert card.approval_status is ApprovalStatus.PENDING_OPERATOR_REVIEW
    assert card.engine_class is EngineClass.TACTICAL
    assert card.control_boundary.control_write_enabled is False


def test_advisory_claims_need_no_evidence():
    card = _card(
        [Claim(claim_id="c6", text="Recommend follow-up", claim_kind=ClaimKind.RECOMMENDATION)]
    )
    assert card.claims[0].evidence_ids == []


def test_composite_confidence_cannot_be_set_inconsistently():
    conf = _confidence()
    expected = (0.8 + 0.4 + 0.9 + 0.7) / 4.0
    assert abs(conf.composite - expected) < 1e-12
    # composite is derived: it cannot be supplied at construction ...
    with pytest.raises(ValidationError):
        RecommendationConfidence(
            data_sufficiency=0.8,
            model_maturity=0.4,
            physics_agreement=0.9,
            historical_precedent=0.7,
            composite=0.99,
        )
    # ... nor assigned afterwards.
    with pytest.raises((ValidationError, AttributeError, TypeError)):
        conf.composite = 0.99


def test_dominant_limitation_names_the_weakest_component():
    assert _confidence().dominant_limitation == "model maturity"
