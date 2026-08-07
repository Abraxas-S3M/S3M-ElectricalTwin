"""Tests for the deterministic grounding gate."""

from __future__ import annotations

from conftest import make_grounded_card, make_packet

from packages.s3m_engine_contract.cards import (
    Audience,
    CardStatus,
    Claim,
    ClaimType,
    HealthBand,
    ProvenanceSummary,
    Recommendation,
    RefutingEvidenceRef,
)
from packages.s3m_engine_contract.grounding import (
    Severity,
    ViolationCode,
    contains_control_language,
    enforce,
    verify_grounding,
)


def _codes(card, packet) -> list[str]:
    return verify_grounding(card, packet).codes()


# --- baseline -----------------------------------------------------------


def test_grounded_card_passes_cleanly():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    report = verify_grounding(card, packet)
    assert report.passed is True
    assert report.violations == []
    assert report.stripped_claim_ids == []


def test_report_records_checked_at_timestamp():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    report = verify_grounding(card, packet)
    assert report.checked_at is not None


# --- UNCITED_CLAIM ------------------------------------------------------


def test_uncited_numeric_claim_fails_with_uncited_claim():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-uncited",
            claim_type=ClaimType.NUMERIC,
            statement="Loading is 88 percent.",
            evidence_ids=(),
            numeric_value=88.0,
        )
    )
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.UNCITED_CLAIM.value in report.codes()


def test_uncited_categorical_claim_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(claim_id="cl-cat", claim_type=ClaimType.CATEGORICAL, statement="X", evidence_ids=())
    )
    assert ViolationCode.UNCITED_CLAIM.value in _codes(card, packet)


def test_uncited_causal_claim_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(claim_id="cl-cau", claim_type=ClaimType.CAUSAL, statement="A causes B", evidence_ids=())
    )
    assert ViolationCode.UNCITED_CLAIM.value in _codes(card, packet)


def test_narrative_claim_needs_no_evidence():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-narr",
            claim_type=ClaimType.NARRATIVE,
            statement="This assessment covers TX-1 only.",
            evidence_ids=(),
        )
    )
    assert verify_grounding(card, packet).passed is True


# --- EVIDENCE_RESOLUTION ------------------------------------------------


def test_dangling_evidence_id_fails_with_evidence_resolution():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-dangle",
            claim_type=ClaimType.CATEGORICAL,
            statement="References missing evidence.",
            evidence_ids=("ev-does-not-exist",),
        )
    )
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.EVIDENCE_RESOLUTION.value in report.codes()


def test_dangling_recommendation_evidence_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.recommendations.append(
        Recommendation(
            recommendation_id="rec-dangle",
            text="Recommend the operator review the trend.",
            audience=Audience.HUMAN_OPERATOR,
            evidence_ids=("ev-missing",),
        )
    )
    assert ViolationCode.EVIDENCE_RESOLUTION.value in _codes(card, packet)


def test_dangling_refuting_evidence_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.refuting_evidence_considered.append(
        RefutingEvidenceRef(evidence_id="ev-missing", consideration="n/a")
    )
    assert ViolationCode.EVIDENCE_RESOLUTION.value in _codes(card, packet)


# --- NUMERIC_PROVENANCE -------------------------------------------------


def test_number_absent_from_packet_fails_with_numeric_provenance():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-invented",
            claim_type=ClaimType.NUMERIC,
            statement="The fault level is 31.5 kA.",
            evidence_ids=("ev-load-pct",),
            numeric_value=31.5,
        )
    )
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.NUMERIC_PROVENANCE.value in report.codes()


def test_numeric_value_within_tolerance_resolves():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-tol",
            claim_type=ClaimType.NUMERIC,
            statement="Top-oil temperature is about 92.4 degC.",
            evidence_ids=("ev-top-oil-temp",),
            numeric_value=92.85,
            relative_tolerance=0.01,
        )
    )
    assert verify_grounding(card, packet).passed is True


def test_numeric_value_outside_tolerance_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-tol2",
            claim_type=ClaimType.NUMERIC,
            statement="Top-oil temperature is 120 degC.",
            evidence_ids=("ev-top-oil-temp",),
            numeric_value=120.0,
            relative_tolerance=0.01,
        )
    )
    assert ViolationCode.NUMERIC_PROVENANCE.value in _codes(card, packet)


# --- ALTERNATIVES_REQUIRED ----------------------------------------------


def test_lone_causal_claim_fails_with_alternatives_required():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.alternatives.clear()
    card.refuting_evidence_considered.clear()
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.ALTERNATIVES_REQUIRED.value in report.codes()


def test_causal_claim_with_one_alternative_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.alternatives.pop()  # leave a single alternative
    assert ViolationCode.ALTERNATIVES_REQUIRED.value in _codes(card, packet)


def test_causal_claim_without_refuting_evidence_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.refuting_evidence_considered.clear()
    assert ViolationCode.ALTERNATIVES_REQUIRED.value in _codes(card, packet)


def test_non_causal_card_needs_no_alternatives():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims = [c for c in card.claims if c.claim_type is not ClaimType.CAUSAL]
    card.alternatives.clear()
    card.refuting_evidence_considered.clear()
    assert verify_grounding(card, packet).passed is True


# --- FORBIDDEN_ASSERTION ------------------------------------------------


def test_asserting_calibration_fails_with_forbidden_assertion():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-cal",
            claim_type=ClaimType.CATEGORICAL,
            statement="The protection relay is calibrated within tolerance.",
            evidence_ids=("ev-load-pct",),
        )
    )
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.FORBIDDEN_ASSERTION.value in report.codes()


def test_asserting_selectivity_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-sel",
            claim_type=ClaimType.CATEGORICAL,
            statement="Full selectivity is achieved between the two devices.",
            evidence_ids=("ev-load-pct",),
        )
    )
    assert ViolationCode.FORBIDDEN_ASSERTION.value in _codes(card, packet)


def test_asserting_arc_flash_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.recommendations.append(
        Recommendation(
            recommendation_id="rec-af",
            text="The arc flash incident energy is within category 2.",
            audience=Audience.LICENSED_ENGINEER,
        )
    )
    assert ViolationCode.FORBIDDEN_ASSERTION.value in _codes(card, packet)


def test_asserting_protection_coordination_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-pc",
            claim_type=ClaimType.CATEGORICAL,
            statement="Protection coordination is confirmed across all feeders.",
            evidence_ids=("ev-load-pct",),
        )
    )
    assert ViolationCode.FORBIDDEN_ASSERTION.value in _codes(card, packet)


def test_asserting_code_compliance_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-code",
            claim_type=ClaimType.CATEGORICAL,
            statement="The installation is code compliant.",
            evidence_ids=("ev-load-pct",),
        )
    )
    assert ViolationCode.FORBIDDEN_ASSERTION.value in _codes(card, packet)


# --- CONTROL_LANGUAGE ---------------------------------------------------


def test_equipment_directed_imperative_fails_with_control_language():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.recommendations.append(
        Recommendation(
            recommendation_id="rec-ctrl",
            text="Open breaker BRK-12 to shed load.",
            audience=Audience.HUMAN_OPERATOR,
        )
    )
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.CONTROL_LANGUAGE.value in report.codes()


def test_system_directed_actuation_fails():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-sys",
            claim_type=ClaimType.NARRATIVE,
            statement="The system will trip breaker BRK-12 automatically.",
            evidence_ids=(),
        )
    )
    assert ViolationCode.CONTROL_LANGUAGE.value in _codes(card, packet)


def test_human_directed_recommendation_permitted():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.recommendations.append(
        Recommendation(
            recommendation_id="rec-ok",
            text="Recommend that the operator consider opening breaker BRK-12 after review.",
            audience=Audience.HUMAN_OPERATOR,
        )
    )
    assert verify_grounding(card, packet).passed is True


def test_contains_control_language_direct_command_true():
    assert contains_control_language("Trip breaker BRK-9.") is True


def test_contains_control_language_human_framed_false():
    assert (
        contains_control_language(
            "Recommend the engineer evaluate whether to open feeder F-3."
        )
        is False
    )


def test_contains_control_language_no_equipment_false():
    assert contains_control_language("Start of the event was at 14:02.") is False


# --- SUFFICIENCY_FLOOR --------------------------------------------------


def test_substantive_card_below_floor_fails_with_sufficiency_floor():
    packet = make_packet(data_sufficiency=0.1)
    card = make_grounded_card(packet=packet, data_sufficiency=0.1)
    card.provenance_summary = ProvenanceSummary(
        is_entirely_synthetic=False,
        data_sufficiency=0.1,
        dominant_provenance=card.provenance_summary.dominant_provenance,
        dominant_validation_state=card.provenance_summary.dominant_validation_state,
    )
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.SUFFICIENCY_FLOOR.value in report.codes()


def test_insufficient_data_band_below_floor_is_permitted():
    packet = make_packet(data_sufficiency=0.1)
    card = make_grounded_card(packet=packet, data_sufficiency=0.1)
    card.health_band = HealthBand.INSUFFICIENT_DATA
    card.provenance_summary = ProvenanceSummary(
        is_entirely_synthetic=False,
        data_sufficiency=0.1,
        dominant_provenance=card.provenance_summary.dominant_provenance,
        dominant_validation_state=card.provenance_summary.dominant_validation_state,
    )
    assert ViolationCode.SUFFICIENCY_FLOOR.value not in _codes(card, packet)


# --- SYNTHETIC_LABEL ----------------------------------------------------


def test_synthetic_packet_forces_preliminary():
    packet = make_packet(is_entirely_synthetic=True)
    card = make_grounded_card(packet=packet, is_entirely_synthetic=True)
    # Break the labelling: synthetic data but not marked preliminary.
    card.status = CardStatus.REVIEWED
    card.demonstration_marker = None
    report = verify_grounding(card, packet)
    assert report.passed is False
    assert ViolationCode.SYNTHETIC_LABEL.value in report.codes()

    enforced = enforce(card, packet)
    assert enforced.status is CardStatus.PRELIMINARY
    assert enforced.demonstration_marker


def test_synthetic_card_properly_labelled_passes():
    packet = make_packet(is_entirely_synthetic=True)
    card = make_grounded_card(packet=packet, is_entirely_synthetic=True)
    assert verify_grounding(card, packet).passed is True


# --- enforce ------------------------------------------------------------


def test_enforce_strips_uncited_claim_and_keeps_others():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-strip",
            claim_type=ClaimType.CATEGORICAL,
            statement="Uncited.",
            evidence_ids=(),
        )
    )
    enforced = enforce(card, packet)
    remaining = {c.claim_id for c in enforced.claims}
    assert "cl-strip" not in remaining
    assert "cl-1" in remaining


def test_enforce_downgrades_structural_violation_to_insufficient_data():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.recommendations.append(
        Recommendation(
            recommendation_id="rec-ctrl",
            text="Close breaker BRK-3 now.",
            audience=Audience.HUMAN_OPERATOR,
        )
    )
    enforced = enforce(card, packet)
    assert enforced.health_band is HealthBand.INSUFFICIENT_DATA
    assert enforced.recommendations == []
    assert enforced.reasons


def test_enforce_never_silently_passes_violation():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-bad",
            claim_type=ClaimType.NUMERIC,
            statement="Invented.",
            evidence_ids=("ev-load-pct",),
            numeric_value=9999.0,
        )
    )
    enforced = enforce(card, packet)
    assert enforced.grounding_report is not None


def test_enforced_card_passes_reverification():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.recommendations.append(
        Recommendation(
            recommendation_id="rec-ctrl",
            text="Open breaker BRK-1.",
            audience=Audience.HUMAN_OPERATOR,
        )
    )
    enforced = enforce(card, packet)
    assert verify_grounding(enforced, packet).passed is True


def test_enforce_passing_card_attaches_report():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    enforced = enforce(card, packet)
    assert enforced.grounding_report is not None


def test_stripped_claim_ids_reported():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-x",
            claim_type=ClaimType.CATEGORICAL,
            statement="Uncited.",
            evidence_ids=(),
        )
    )
    report = verify_grounding(card, packet)
    assert "cl-x" in report.stripped_claim_ids


def test_severity_mapping_for_claim_level_codes():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(
            claim_id="cl-u",
            claim_type=ClaimType.NUMERIC,
            statement="x",
            evidence_ids=(),
            numeric_value=None,
        )
    )
    report = verify_grounding(card, packet)
    uncited = [v for v in report.violations if v.code is ViolationCode.UNCITED_CLAIM]
    assert uncited and uncited[0].severity is Severity.CLAIM


def test_multiple_violations_all_reported():
    packet = make_packet()
    card = make_grounded_card(packet=packet)
    card.claims.append(
        Claim(claim_id="cl-a", claim_type=ClaimType.CATEGORICAL, statement="x", evidence_ids=())
    )
    card.claims.append(
        Claim(
            claim_id="cl-b",
            claim_type=ClaimType.NUMERIC,
            statement="y",
            evidence_ids=("ev-load-pct",),
            numeric_value=12345.0,
        )
    )
    codes = _codes(card, packet)
    assert ViolationCode.UNCITED_CLAIM.value in codes
    assert ViolationCode.NUMERIC_PROVENANCE.value in codes
