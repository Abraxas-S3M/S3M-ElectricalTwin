"""Shared fixtures and builders for the WP0 test suite.

All data here is synthetic and describes no real installation.
"""

from __future__ import annotations

import pytest

from packages.canonical_electrical_model.provenance import (
    DataProvenance,
    ValidationState,
)
from packages.s3m_engine_contract.cards import (
    Alternative,
    Audience,
    CardStatus,
    Claim,
    ClaimType,
    ConfidenceComponents,
    Evidence,
    HealthBand,
    ProvenanceSummary,
    Recommendation,
    RecommendationCard,
    RefutingEvidenceRef,
)
from packages.s3m_engine_contract.packets import (
    EnginePacket,
    PacketClass,
    UrgencyLevel,
)


def make_evidence_pool() -> list[Evidence]:
    """A small synthetic evidence pool with resolvable numeric values."""

    return [
        Evidence(
            evidence_id="ev-top-oil-temp",
            description="Transformer TX-1 top-oil temperature",
            value=92.4,
            unit="degC",
            provenance=DataProvenance.MEASURED_TELEMETRY,
            validation_state=ValidationState.ENGINEER_REVIEWED,
        ),
        Evidence(
            evidence_id="ev-load-pct",
            description="TX-1 loading",
            value=88.0,
            unit="percent",
            provenance=DataProvenance.MEASURED_TELEMETRY,
            validation_state=ValidationState.ENGINEER_REVIEWED,
        ),
        Evidence(
            evidence_id="ev-ambient",
            description="Ambient temperature",
            value=34.0,
            unit="degC",
            provenance=DataProvenance.MEASURED_TELEMETRY,
            validation_state=ValidationState.FIELD_VERIFIED,
        ),
    ]


def make_packet(
    *,
    packet_id: str = "pkt-0001",
    packet_class: PacketClass = PacketClass.ASSET_HEALTH,
    is_entirely_synthetic: bool = False,
    data_sufficiency: float = 0.72,
    urgency: UrgencyLevel = UrgencyLevel.ELEVATED,
) -> EnginePacket:
    """Build a synthetic packet."""

    dominant = (
        DataProvenance.SYNTHETIC if is_entirely_synthetic else DataProvenance.MEASURED_TELEMETRY
    )
    return EnginePacket(
        packet_id=packet_id,
        packet_class=packet_class,
        urgency=urgency,
        evidence_pool=make_evidence_pool(),
        provenance_summary=ProvenanceSummary(
            is_entirely_synthetic=is_entirely_synthetic,
            data_sufficiency=data_sufficiency,
            dominant_provenance=dominant,
            dominant_validation_state=ValidationState.ENGINEER_REVIEWED,
        ),
    )


def make_grounded_card(
    *,
    packet: EnginePacket | None = None,
    data_sufficiency: float = 0.72,
    is_entirely_synthetic: bool = False,
) -> RecommendationCard:
    """Build a card that is expected to pass the grounding gate."""

    pkt = packet or make_packet(
        data_sufficiency=data_sufficiency, is_entirely_synthetic=is_entirely_synthetic
    )
    status = CardStatus.PRELIMINARY if is_entirely_synthetic else CardStatus.PROVISIONAL
    marker = (
        "DEMONSTRATION — synthetic data only; not a statement about any real installation."
        if is_entirely_synthetic
        else None
    )
    return RecommendationCard(
        card_id="card-0001",
        packet_id=pkt.packet_id,
        health_band=HealthBand.ELEVATED_ATTENTION,
        status=status,
        headline="TX-1 top-oil temperature is elevated relative to loading and ambient.",
        claims=[
            Claim(
                claim_id="cl-1",
                claim_type=ClaimType.NUMERIC,
                statement="Top-oil temperature is 92.4 degC.",
                evidence_ids=("ev-top-oil-temp",),
                numeric_value=92.4,
                numeric_unit="degC",
            ),
            Claim(
                claim_id="cl-2",
                claim_type=ClaimType.CATEGORICAL,
                statement="Loading is in the elevated band.",
                evidence_ids=("ev-load-pct",),
            ),
            Claim(
                claim_id="cl-3",
                claim_type=ClaimType.CAUSAL,
                statement=(
                    "The elevated top-oil temperature is most consistent with "
                    "sustained high loading at high ambient."
                ),
                evidence_ids=("ev-load-pct", "ev-ambient"),
            ),
        ],
        alternatives=[
            Alternative(
                alternative_id="alt-1",
                description="Sustained high loading at high ambient.",
                rank=1,
                relative_likelihood=0.6,
            ),
            Alternative(
                alternative_id="alt-2",
                description="Degraded cooling reducing heat rejection.",
                rank=2,
                relative_likelihood=0.3,
            ),
        ],
        refuting_evidence_considered=[
            RefutingEvidenceRef(
                evidence_id="ev-ambient",
                consideration="Ambient is high but not extreme.",
            )
        ],
        recommendations=[
            Recommendation(
                recommendation_id="rec-1",
                text=(
                    "Recommend that the operator review TX-1 cooling-system status "
                    "and recent loading history."
                ),
                audience=Audience.HUMAN_OPERATOR,
                evidence_ids=("ev-load-pct",),
            )
        ],
        confidence=ConfidenceComponents(
            data_sufficiency=data_sufficiency,
            model_fidelity=0.55,
            corroboration=0.5,
        ),
        provenance_summary=ProvenanceSummary(
            is_entirely_synthetic=is_entirely_synthetic,
            data_sufficiency=data_sufficiency,
            dominant_provenance=(
                DataProvenance.SYNTHETIC
                if is_entirely_synthetic
                else DataProvenance.MEASURED_TELEMETRY
            ),
            dominant_validation_state=ValidationState.ENGINEER_REVIEWED,
        ),
        demonstration_marker=marker,
    )


@pytest.fixture()
def packet() -> EnginePacket:
    return make_packet()


@pytest.fixture()
def grounded_card(packet: EnginePacket) -> RecommendationCard:
    return make_grounded_card(packet=packet)
