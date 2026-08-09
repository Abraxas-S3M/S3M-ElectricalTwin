"""Recommendation cards enforce grounding and a computed confidence."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from packages.s3m_engine_contract.card import (
    ApprovalStatus,
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


def _confidence(**overrides) -> RecommendationConfidence:
    base = dict(
        data_sufficiency=0.8,
        model_maturity=0.6,
        physics_agreement=0.9,
        historical_precedent=0.7,
    )
    base.update(overrides)
    return RecommendationConfidence(**base)


def _build_card(claims=None, **overrides) -> RecommendationCard:
    decision = route(PacketClass.ALARM_TRIAGE, Urgency.IMMEDIATE)
    base = dict(
        id="card-1",
        title="Synthetic alarm triage",
        node_ids=["n1"],
        urgency=Urgency.IMMEDIATE,
        rationale="Synthetic rationale.",
        packet_id="pkt-0001",
        packet_hash="0" * 64,
        engine_class=decision.engine,
        routing_decision=decision,
        confidence=_confidence(),
        claims=claims if claims is not None else [],
    )
    base.update(overrides)
    return RecommendationCard(**base)


def test_default_approval_status_is_pending_operator_review() -> None:
    assert _build_card().approval_status is ApprovalStatus.PENDING_OPERATOR_REVIEW


def test_card_with_grounded_claims_is_valid() -> None:
    claims = [
        Claim(
            claim_id="c1",
            text="Voltage at n1 is 11.0 kV.",
            claim_kind=ClaimKind.NUMERIC,
            evidence_ids=["ev-1"],
        ),
        Claim(
            claim_id="c2",
            text="Inspect n1 breaker.",
            claim_kind=ClaimKind.RECOMMENDATION,
            evidence_ids=[],
        ),
    ]
    card = _build_card(claims=claims)
    assert len(card.claims) == 2


@pytest.mark.parametrize(
    "kind",
    [ClaimKind.NUMERIC, ClaimKind.CATEGORICAL, ClaimKind.CAUSAL],
)
def test_uncited_checkable_claim_fails_validation(kind: ClaimKind) -> None:
    claims = [
        Claim(
            claim_id="c-bad",
            text="An uncited checkable claim.",
            claim_kind=kind,
            evidence_ids=[],
        )
    ]
    with pytest.raises(ValidationError):
        _build_card(claims=claims)


@pytest.mark.parametrize(
    "kind",
    [ClaimKind.RECOMMENDATION, ClaimKind.CONTEXTUAL],
)
def test_uncited_soft_claim_is_allowed(kind: ClaimKind) -> None:
    claims = [
        Claim(
            claim_id="c-soft",
            text="A soft claim needing no evidence.",
            claim_kind=kind,
            evidence_ids=[],
        )
    ]
    card = _build_card(claims=claims)
    assert card.claims[0].claim_kind is kind


def test_confidence_composite_is_computed() -> None:
    conf = _confidence(
        data_sufficiency=0.8,
        model_maturity=0.6,
        physics_agreement=0.9,
        historical_precedent=0.7,
    )
    assert conf.composite == pytest.approx(0.75)


def test_confidence_composite_cannot_be_set() -> None:
    with pytest.raises(ValidationError):
        RecommendationConfidence(
            data_sufficiency=0.1,
            model_maturity=0.1,
            physics_agreement=0.1,
            historical_precedent=0.1,
            composite=0.99,  # inconsistent with components -> rejected
        )


def test_dominant_limitation_names_weakest_component() -> None:
    conf = _confidence(
        data_sufficiency=0.2,
        model_maturity=0.9,
        physics_agreement=0.9,
        historical_precedent=0.9,
    )
    assert conf.dominant_limitation == "data sufficiency"

    conf2 = _confidence(
        data_sufficiency=0.9,
        model_maturity=0.9,
        physics_agreement=0.3,
        historical_precedent=0.9,
    )
    assert conf2.dominant_limitation == "physics agreement"


def test_card_carries_routing_decision_and_engine() -> None:
    card = _build_card()
    assert card.engine_class is EngineClass.TACTICAL
    assert card.routing_decision.engine is EngineClass.TACTICAL
    assert card.model_version == "none"
    assert card.prompt_template_version == "none"
