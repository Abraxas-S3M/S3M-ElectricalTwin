"""Tests for the insufficient-data refusal path."""

from __future__ import annotations

from datetime import UTC, datetime

from packages.canonical_electrical_model import Evidence, HealthBand, ValidationState
from packages.s3m_engine_contract.grounding import verify_grounding
from packages.s3m_engine_contract.packet import (
    DataSufficiency,
    ElectricalTwinPacket,
    ProvenanceSummary,
)
from packages.s3m_engine_contract.refusal import insufficient_data_card
from packages.s3m_engine_contract.routing import PacketClass, Urgency

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 1, 1, 1, tzinfo=UTC)


def _packet(*, synthetic: bool = True, sufficient: bool = False) -> ElectricalTwinPacket:
    composite = 0.9 if sufficient else 0.1
    return ElectricalTwinPacket(
        packet_id="pkt-refuse",
        packet_class=PacketClass.ASSET_CONDITION,
        urgency=Urgency.ELEVATED,
        created_at=_T0,
        facility_id="fac-1",
        node_ids=["n1", "n2"],
        window_start=_T0,
        window_end=_T1,
        evidence_pool=[
            Evidence(
                kind="measurement",
                node_id="n1",
                channel="voltage",
                window_start=_T0,
                window_end=_T1,
                observed=1.0,
                source_ref="ev-1",
            )
        ],
        provenance_summary=ProvenanceSummary(is_entirely_synthetic=synthetic),
        data_sufficiency=DataSufficiency(
            channel_coverage=composite,
            quality_ratio=composite,
            history_depth_hours=168.0 * composite,
            metering_completeness=composite,
        ),
    )


def test_refusal_card_is_insufficient_data_with_zero_confidence() -> None:
    card = insufficient_data_card(_packet(), ["no telemetry for node n2"])
    assert card.health_band is HealthBand.INSUFFICIENT_DATA
    assert card.validation_state is ValidationState.INSUFFICIENT_DATA
    assert card.recommended_action is None
    assert card.recommended_inspection is None
    assert card.confidence.composite == 0.0
    assert card.insufficient_data_reasons == ["no telemetry for node n2"]


def test_insufficient_data_card_always_passes_verify_grounding() -> None:
    # Passes for both synthetic and non-synthetic, sufficient and insufficient
    # packets: it is a grounded refusal by construction.
    for synthetic in (True, False):
        for sufficient in (True, False):
            packet = _packet(synthetic=synthetic, sufficient=sufficient)
            card = insufficient_data_card(packet, ["insufficient evidence"])
            report = verify_grounding(card, packet)
            assert report.passed is True, report.violations


def test_refusal_card_routes_consistently_with_packet() -> None:
    packet = _packet()
    card = insufficient_data_card(packet, ["reason"])
    assert card.packet_id == packet.packet_id
    assert card.routing_decision.packet_class is packet.packet_class
    assert card.engine_class is card.routing_decision.engine_class
