"""Tests for the insufficient-data refusal card."""

from __future__ import annotations

from conftest import make_packet

from packages.s3m_engine_contract.cards import CardStatus, HealthBand
from packages.s3m_engine_contract.grounding import verify_grounding
from packages.s3m_engine_contract.refusal import insufficient_data_card


def test_insufficient_data_card_has_insufficient_band():
    packet = make_packet()
    card = insufficient_data_card(packet, ["not enough evidence"])
    assert card.health_band is HealthBand.INSUFFICIENT_DATA


def test_insufficient_data_card_has_no_recommendations():
    packet = make_packet()
    card = insufficient_data_card(packet, ["not enough evidence"])
    assert card.recommendations == []
    assert card.claims == []


def test_insufficient_data_card_populates_reasons():
    packet = make_packet()
    card = insufficient_data_card(packet, ["reason one", "reason two"])
    assert card.reasons == ["reason one", "reason two"]


def test_insufficient_data_card_defaults_reason_when_empty():
    packet = make_packet()
    card = insufficient_data_card(packet, [])
    assert card.reasons


def test_insufficient_data_card_zero_confidence():
    packet = make_packet()
    card = insufficient_data_card(packet, ["x"])
    assert card.confidence.data_sufficiency == 0.0
    assert card.confidence.model_fidelity == 0.0
    assert card.confidence.corroboration == 0.0


def test_insufficient_data_card_always_passes_verify_grounding():
    packet = make_packet()
    card = insufficient_data_card(packet, ["insufficient evidence"])
    assert verify_grounding(card, packet).passed is True


def test_insufficient_data_card_passes_even_below_floor():
    packet = make_packet(data_sufficiency=0.05)
    card = insufficient_data_card(packet, ["insufficient evidence"])
    assert verify_grounding(card, packet).passed is True


def test_insufficient_data_card_synthetic_is_preliminary_and_passes():
    packet = make_packet(is_entirely_synthetic=True)
    card = insufficient_data_card(packet, ["insufficient evidence"])
    assert card.status is CardStatus.PRELIMINARY
    assert card.demonstration_marker
    assert verify_grounding(card, packet).passed is True


def test_insufficient_data_card_carries_packet_id():
    packet = make_packet(packet_id="pkt-xyz")
    card = insufficient_data_card(packet, ["x"])
    assert card.packet_id == "pkt-xyz"
