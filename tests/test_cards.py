"""Tests for the card, claim and confidence models."""

from __future__ import annotations

import pytest
from conftest import make_grounded_card, make_packet
from pydantic import ValidationError

from packages.s3m_engine_contract.cards import (
    EVIDENCE_BEARING_CLAIM_TYPES,
    Alternative,
    ClaimType,
    ConfidenceComponents,
    HealthBand,
)


def test_evidence_bearing_types_exclude_narrative():
    assert ClaimType.NARRATIVE not in EVIDENCE_BEARING_CLAIM_TYPES
    assert ClaimType.NUMERIC in EVIDENCE_BEARING_CLAIM_TYPES
    assert ClaimType.CATEGORICAL in EVIDENCE_BEARING_CLAIM_TYPES
    assert ClaimType.CAUSAL in EVIDENCE_BEARING_CLAIM_TYPES


def test_confidence_zero_helper():
    zero = ConfidenceComponents.zero()
    assert (zero.data_sufficiency, zero.model_fidelity, zero.corroboration) == (0.0, 0.0, 0.0)


def test_confidence_component_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ConfidenceComponents(data_sufficiency=1.5)


def test_card_has_causal_claim_detection():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    assert card.has_causal_claim() is True


def test_card_without_causal_claim():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims = [c for c in card.claims if c.claim_type is not ClaimType.CAUSAL]
    assert card.has_causal_claim() is False


def test_card_is_substantive_with_claims():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    assert card.is_substantive() is True


def test_card_not_substantive_when_empty():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims = []
    card.recommendations = []
    assert card.is_substantive() is False


def test_health_band_includes_insufficient_data():
    assert HealthBand.INSUFFICIENT_DATA.value == "insufficient_data"


def test_alternative_requires_positive_rank():
    with pytest.raises(ValidationError):
        Alternative(alternative_id="a", description="x", rank=0, relative_likelihood=0.5)


def test_alternative_likelihood_bounded():
    with pytest.raises(ValidationError):
        Alternative(alternative_id="a", description="x", rank=1, relative_likelihood=2.0)


def test_empty_card_id_rejected():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    payload = card.model_dump()
    payload["card_id"] = ""
    with pytest.raises(ValidationError):
        type(card).model_validate(payload)
