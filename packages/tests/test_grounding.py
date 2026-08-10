"""Tests for the deterministic grounding gate.

Each named test exercises one grounding check in isolation: a card that is
otherwise fully grounded is given exactly one defect, and the gate is asserted
to raise the corresponding violation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.canonical_electrical_model import (
    Evidence,
    HealthBand,
    RankedCause,
    ValidationState,
)
from packages.s3m_engine_contract.card import (
    Claim,
    ClaimKind,
    RecommendationCard,
    RecommendationConfidence,
)
from packages.s3m_engine_contract.grounding import (
    GroundingCheck,
    enforce,
    verify_grounding,
)
from packages.s3m_engine_contract.packet import (
    DataSufficiency,
    ElectricalTwinPacket,
    ProvenanceSummary,
)
from packages.s3m_engine_contract.routing import PacketClass, Urgency, route

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 1, 1, 1, tzinfo=UTC)


def _evidence(source_ref: str = "ev-1", observed: float = 11.0) -> Evidence:
    return Evidence(
        kind="measurement",
        node_id="n1",
        channel="voltage",
        window_start=_T0,
        window_end=_T1,
        observed=observed,
        unit="kV",
        source_ref=source_ref,
    )


def _packet(*, synthetic: bool = True, sufficient: bool = True) -> ElectricalTwinPacket:
    if sufficient:
        ds = DataSufficiency(
            channel_coverage=0.9,
            quality_ratio=0.9,
            history_depth_hours=168.0,
            metering_completeness=0.9,
        )
    else:
        ds = DataSufficiency(
            channel_coverage=0.1,
            quality_ratio=0.1,
            history_depth_hours=1.0,
            metering_completeness=0.1,
        )
    return ElectricalTwinPacket(
        packet_id="pkt-1",
        packet_class=PacketClass.ANOMALY_INVESTIGATION,
        urgency=Urgency.ROUTINE,
        created_at=_T0,
        facility_id="fac-1",
        node_ids=["n1"],
        window_start=_T0,
        window_end=_T1,
        evidence_pool=[_evidence()],
        provenance_summary=ProvenanceSummary(is_entirely_synthetic=synthetic),
        data_sufficiency=ds,
    )


def _card(*, claims=None, ranked_causes=None, **overrides) -> RecommendationCard:
    decision = route(PacketClass.ANOMALY_INVESTIGATION, Urgency.ROUTINE)
    base = dict(
        id="card-1",
        title="Synthetic preliminary finding",
        node_ids=["n1"],
        urgency=Urgency.ROUTINE,
        rationale="A synthetic, preliminary observation for demonstration only.",
        health_band=HealthBand.AT_RISK,
        is_demonstration=True,
        validation_state=ValidationState.PRELIMINARY,
        packet_id="pkt-1",
        packet_hash="0" * 64,
        engine_class=decision.engine_class,
        routing_decision=decision,
        confidence=RecommendationConfidence(
            data_sufficiency=0.8,
            model_maturity=0.6,
            physics_agreement=0.7,
            historical_precedent=0.6,
        ),
        claims=claims if claims is not None else [],
        ranked_causes=ranked_causes if ranked_causes is not None else [],
    )
    base.update(overrides)
    return RecommendationCard(**base)


def _codes(report) -> set[str]:
    return {v.code for v in report.violations}


def test_clean_card_passes_grounding() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c1",
                text="Voltage at n1 is 11.0 kV.",
                claim_kind=ClaimKind.NUMERIC,
                evidence_ids=["ev-1"],
                numeric_value=11.0,
            )
        ]
    )
    report = verify_grounding(card, _packet())
    assert report.passed is True
    assert report.violations == []


def test_uncited_numeric_claim_fails_with_uncited_claim() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c1",
                text="Voltage at n1 is 11.0 kV.",
                claim_kind=ClaimKind.NUMERIC,
                evidence_ids=["ev-1"],
                numeric_value=11.0,
            )
        ]
    )
    # Append an uncited numeric claim, bypassing the card's construction guard.
    card.claims.append(
        Claim(
            claim_id="c-uncited",
            text="Current at n1 is 200 A.",
            claim_kind=ClaimKind.NUMERIC,
            evidence_ids=[],
        )
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.UNCITED_CLAIM.value in _codes(report)
    assert report.passed is False


def test_dangling_evidence_id_fails_with_evidence_resolution() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c1",
                text="Voltage at n1 is 11.0 kV.",
                claim_kind=ClaimKind.NUMERIC,
                evidence_ids=["ev-does-not-exist"],
                numeric_value=11.0,
            )
        ]
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.EVIDENCE_RESOLUTION.value in _codes(report)


def test_number_absent_from_packet_fails_with_numeric_provenance() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c1",
                text="Voltage at n1 is 47.3 kV.",
                claim_kind=ClaimKind.NUMERIC,
                evidence_ids=["ev-1"],
                numeric_value=47.3,  # not present anywhere in the packet
            )
        ]
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.NUMERIC_PROVENANCE.value in _codes(report)


def test_lone_causal_claim_fails_with_alternatives_required() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c1",
                text="The sag was caused by an upstream tap change.",
                claim_kind=ClaimKind.CAUSAL,
                evidence_ids=["ev-1"],
            )
        ],
        ranked_causes=[],  # no ranked alternatives, no refutation considered
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.ALTERNATIVES_REQUIRED.value in _codes(report)


def test_causal_claim_with_alternatives_and_refutation_passes() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c1",
                text="The sag most likely followed an upstream tap change.",
                claim_kind=ClaimKind.CAUSAL,
                evidence_ids=["ev-1"],
            )
        ],
        ranked_causes=[
            RankedCause(
                hypothesis="Upstream tap change",
                rank=1,
                likelihood=0.6,
                supporting_evidence=[_evidence()],
                refuting_evidence=[_evidence(source_ref="ev-2", observed=11.1)],
            ),
            RankedCause(
                hypothesis="Large motor start",
                rank=2,
                likelihood=0.3,
                supporting_evidence=[_evidence()],
            ),
        ],
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.ALTERNATIVES_REQUIRED.value not in _codes(report)


def test_asserting_calibration_fails_with_forbidden_assertion() -> None:
    card = _card(
        rationale="Calibration of the model confirms the transformer is healthy.",
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.FORBIDDEN_ASSERTION.value in _codes(report)


def test_equipment_directed_imperative_fails_with_control_language() -> None:
    card = _card(
        recommended_action="Open breaker CB-12 and trip the feeder now.",
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.CONTROL_LANGUAGE.value in _codes(report)


def test_operator_directed_recommendation_is_permitted() -> None:
    card = _card(
        recommended_action=(
            "Recommend that a qualified operator inspect breaker CB-12 at the "
            "next opportunity."
        ),
    )
    report = verify_grounding(card, _packet())
    assert GroundingCheck.CONTROL_LANGUAGE.value not in _codes(report)


def test_substantive_card_below_floor_fails_with_sufficiency_floor() -> None:
    card = _card(
        recommended_action="Schedule a thermographic survey of the main switchboard.",
    )
    report = verify_grounding(card, _packet(sufficient=False))
    assert GroundingCheck.SUFFICIENCY_FLOOR.value in _codes(report)


def test_synthetic_packet_forces_preliminary() -> None:
    # A card that presents itself as validated on an entirely synthetic packet.
    card = _card(
        is_demonstration=False,
        validation_state=ValidationState.VALIDATED,
    )
    report = verify_grounding(card, _packet(synthetic=True))
    assert GroundingCheck.SYNTHETIC_LABEL.value in _codes(report)


def test_enforce_strips_offending_claim_and_attaches_report() -> None:
    card = _card(
        claims=[
            Claim(
                claim_id="c-good",
                text="Voltage at n1 is 11.0 kV.",
                claim_kind=ClaimKind.NUMERIC,
                evidence_ids=["ev-1"],
                numeric_value=11.0,
            )
        ]
    )
    card.claims.append(
        Claim(
            claim_id="c-bad",
            text="Frequency is 61.7 Hz.",
            claim_kind=ClaimKind.NUMERIC,
            evidence_ids=["ev-1"],
            numeric_value=61.7,  # not in the packet -> NUMERIC_PROVENANCE
        )
    )
    enforced = enforce(card, _packet())
    surviving = {c.claim_id for c in enforced.claims}
    assert "c-bad" not in surviving
    assert "c-good" in surviving
    assert enforced.grounding_report is not None
    assert "c-bad" in enforced.grounding_report.stripped_claim_ids


def test_enforce_downgrades_structural_violation_to_insufficient_data() -> None:
    card = _card(
        recommended_action="Schedule a thermographic survey of the main switchboard.",
    )
    enforced = enforce(card, _packet(sufficient=False))
    assert enforced.validation_state is ValidationState.INSUFFICIENT_DATA
    assert enforced.health_band is HealthBand.INSUFFICIENT_DATA
    assert enforced.recommended_action is None
    assert enforced.grounding_report is not None
