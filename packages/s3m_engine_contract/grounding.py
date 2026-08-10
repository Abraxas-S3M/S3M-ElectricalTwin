"""The Grounding Gate — a deterministic verifier between engine and operator.

There is no language model in this module. It takes a
:class:`~packages.s3m_engine_contract.cards.RecommendationCard` and the
:class:`~packages.s3m_engine_contract.packets.EnginePacket` it was produced from
and mechanically checks that every assertion the card makes is grounded in the
packet's evidence. Each failed check produces a named
:class:`Violation`. :func:`enforce` then strips or downgrades the card so that a
violation can never be silently passed to an operator.

The checks are:

``EVIDENCE_RESOLUTION``
    Every referenced ``evidence_id`` exists in the packet's evidence pool.
``UNCITED_CLAIM``
    No numeric, categorical or causal claim lacks supporting evidence.
``NUMERIC_PROVENANCE``
    Every numeric value in the card resolves to a value present in the packet
    within tolerance. A number the engine invented is a violation.
``ALTERNATIVES_REQUIRED``
    Any card with a causal claim carries at least two ranked alternatives and at
    least one item of refuting evidence considered.
``FORBIDDEN_ASSERTION``
    The card must not assert calibration, validation, code-compliance,
    protection-coordination, selectivity or arc-flash results.
``CONTROL_LANGUAGE``
    No imperative control language directed at equipment. Recommendations
    phrased to a human operator are permitted.
``SUFFICIENCY_FLOOR``
    Below the configured data-sufficiency floor the card must be
    ``INSUFFICIENT_DATA``.
``SYNTHETIC_LABEL``
    If the card's provenance summary is entirely synthetic, the card must be
    ``PRELIMINARY`` and carry a demonstration marker.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from packages.canonical_electrical_model.safety import EQUIPMENT_CONTROL_VERBS
from packages.s3m_engine_contract.cards import (
    EVIDENCE_BEARING_CLAIM_TYPES,
    CardStatus,
    Claim,
    ConfidenceComponents,
    HealthBand,
    RecommendationCard,
)
from packages.s3m_engine_contract.packets import EnginePacket

DEMONSTRATION_MARKER: str = (
    "DEMONSTRATION — synthetic data only; not a statement about any real "
    "installation."
)


class ViolationCode(str, Enum):
    """The named grounding checks."""

    EVIDENCE_RESOLUTION = "EVIDENCE_RESOLUTION"
    UNCITED_CLAIM = "UNCITED_CLAIM"
    NUMERIC_PROVENANCE = "NUMERIC_PROVENANCE"
    ALTERNATIVES_REQUIRED = "ALTERNATIVES_REQUIRED"
    FORBIDDEN_ASSERTION = "FORBIDDEN_ASSERTION"
    CONTROL_LANGUAGE = "CONTROL_LANGUAGE"
    SUFFICIENCY_FLOOR = "SUFFICIENCY_FLOOR"
    SYNTHETIC_LABEL = "SYNTHETIC_LABEL"


class Severity(str, Enum):
    """How :func:`enforce` should react to a violation.

    ``CLAIM``
        The offending claim is stripped from the card.
    ``STRUCTURAL``
        The card as a whole is downgraded to ``INSUFFICIENT_DATA``.
    ``LABEL``
        The card's labelling is corrected (synthetic → preliminary + marker).
    """

    CLAIM = "claim"
    STRUCTURAL = "structural"
    LABEL = "label"


#: Which severity each violation code carries.
SEVERITY_BY_CODE: dict[ViolationCode, Severity] = {
    ViolationCode.EVIDENCE_RESOLUTION: Severity.CLAIM,
    ViolationCode.UNCITED_CLAIM: Severity.CLAIM,
    ViolationCode.NUMERIC_PROVENANCE: Severity.CLAIM,
    ViolationCode.ALTERNATIVES_REQUIRED: Severity.STRUCTURAL,
    ViolationCode.FORBIDDEN_ASSERTION: Severity.STRUCTURAL,
    ViolationCode.CONTROL_LANGUAGE: Severity.STRUCTURAL,
    ViolationCode.SUFFICIENCY_FLOOR: Severity.STRUCTURAL,
    ViolationCode.SYNTHETIC_LABEL: Severity.LABEL,
}

GROUNDING_RULE_DEFINITIONS: dict[str, str] = {
    ViolationCode.EVIDENCE_RESOLUTION.value: (
        "Every evidence_id referenced by a claim, recommendation or refuting "
        "reference must exist in the packet's evidence pool."
    ),
    ViolationCode.UNCITED_CLAIM.value: (
        "Every numeric, categorical or causal claim must cite at least one item "
        "of evidence. Narrative framing needs no citation."
    ),
    ViolationCode.NUMERIC_PROVENANCE.value: (
        "Every numeric value stated by the card must resolve, within the claim's "
        "tolerance, to a value present in the packet. A number that appears in "
        "the card but nowhere in the packet is treated as invented."
    ),
    ViolationCode.ALTERNATIVES_REQUIRED.value: (
        "Any card that asserts a cause must carry at least two ranked "
        "alternative hypotheses and at least one item of refuting evidence that "
        "was considered."
    ),
    ViolationCode.FORBIDDEN_ASSERTION.value: (
        "The card must not assert calibration, validation, code-compliance, "
        "protection-coordination, selectivity or arc-flash results. Those remain "
        "the deliverable of a licensed engineer."
    ),
    ViolationCode.CONTROL_LANGUAGE.value: (
        "The card must not contain imperative control language directed at "
        "equipment (open, close, trip, start, stop, set, write, adjust). "
        "Recommendations phrased to a human operator are permitted."
    ),
    ViolationCode.SUFFICIENCY_FLOOR.value: (
        "If the supporting data sits below the configured sufficiency floor the "
        "card must report INSUFFICIENT_DATA rather than a substantive finding."
    ),
    ViolationCode.SYNTHETIC_LABEL.value: (
        "If the card's data is entirely synthetic it must be marked PRELIMINARY "
        "and carry a demonstration marker so it can never be mistaken for a "
        "statement about a real installation."
    ),
}

#: Forbidden result topics mapped to the lowercase substrings that signal them.
_FORBIDDEN_TOPICS: dict[str, tuple[str, ...]] = {
    "calibration": ("calibrat",),
    "validation": ("validated", "validation"),
    "code_compliance": ("code compliant", "code-compliant", "code compliance", "compliant with code"),
    "protection_coordination": ("protection coordinat", "coordination study", "coordinated protection"),
    "selectivity": ("selectiv",),
    "arc_flash": ("arc flash", "arc-flash", "arcflash", "incident energy"),
}

#: Tokens that mark a sentence as addressed to a human. Their presence makes an
#: otherwise control-shaped sentence a permitted recommendation.
_HUMAN_MARKERS: frozenset[str] = frozenset(
    {
        "operator",
        "operators",
        "engineer",
        "engineers",
        "technician",
        "technicians",
        "personnel",
        "crew",
        "dispatcher",
        "staff",
        "human",
        "recommend",
        "recommends",
        "recommended",
        "consider",
        "considering",
        "advise",
        "advised",
        "review",
        "reviewing",
        "evaluate",
        "evaluating",
        "inspect",
        "inspection",
        "assess",
        "verify",
        "confirm",
    }
)

#: Non-human subjects that, when told to actuate, indicate machine-directed
#: control language.
_MACHINE_SUBJECTS: frozenset[str] = frozenset(
    {"system", "platform", "controller", "scada", "rtu", "plc"}
)

#: Nouns that indicate a sentence targets physical equipment.
_EQUIPMENT_NOUNS: frozenset[str] = frozenset(
    {
        "breaker",
        "breakers",
        "feeder",
        "feeders",
        "bus",
        "busbar",
        "busbars",
        "transformer",
        "transformers",
        "relay",
        "relays",
        "recloser",
        "reclosers",
        "switch",
        "switches",
        "disconnector",
        "disconnectors",
        "capacitor",
        "line",
        "lines",
        "valve",
        "load",
    }
)

_ID_LIKE = re.compile(r"[a-z]+-?\d")


class GroundingConfig(BaseModel):
    """Tunable thresholds for the grounding gate."""

    model_config = {"frozen": True}

    sufficiency_floor: float = Field(0.4, ge=0.0, le=1.0)
    minimum_alternatives: int = Field(2, ge=1)
    minimum_refuting_evidence: int = Field(1, ge=0)


DEFAULT_CONFIG = GroundingConfig()


class Violation(BaseModel):
    """A single named grounding failure."""

    model_config = {"frozen": True}

    code: ViolationCode
    severity: Severity
    detail: str
    offending_claim_id: str | None = None


class GroundingReport(BaseModel):
    """The result of running the grounding gate over a card."""

    passed: bool
    violations: list[Violation] = Field(default_factory=list)
    stripped_claim_ids: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    def codes(self) -> list[str]:
        """Return the violation codes as strings, in order."""

        return [violation.code.value for violation in self.violations]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!?;\n]", text) if part.strip()]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _references_equipment(sentence_lower: str, tokens: list[str]) -> bool:
    if any(noun in _EQUIPMENT_NOUNS for noun in tokens):
        return True
    return bool(_ID_LIKE.search(sentence_lower))


def contains_control_language(text: str) -> bool:
    """Return ``True`` if ``text`` issues an imperative control command.

    The heuristic is deliberately conservative: a sentence addressed to a human
    (containing an operator/engineer marker) is always permitted. A sentence is
    flagged only when it either opens with an equipment control verb aimed at
    physical equipment, or tells a non-human system to actuate.
    """

    for sentence in _sentences(text):
        lower = sentence.lower()
        tokens = _tokens(sentence)
        if not tokens:
            continue
        if any(marker in _HUMAN_MARKERS for marker in tokens):
            continue
        if tokens[0] in EQUIPMENT_CONTROL_VERBS and _references_equipment(lower, tokens):
            return True
        for index, token in enumerate(tokens[:-1]):
            if token in _MACHINE_SUBJECTS and any(
                verb in EQUIPMENT_CONTROL_VERBS for verb in tokens[index + 1 :]
            ):
                return True
    return False


def _forbidden_topic(text: str) -> str | None:
    lower = text.lower()
    for topic, needles in _FORBIDDEN_TOPICS.items():
        if any(needle in lower for needle in needles):
            return topic
    return None


def _resolves_to_packet_value(
    claim: Claim, packet_values: list[float]
) -> bool:
    if claim.numeric_value is None:
        return True
    target = claim.numeric_value
    for candidate in packet_values:
        tolerance = claim.absolute_tolerance + claim.relative_tolerance * abs(candidate)
        if abs(target - candidate) <= tolerance:
            return True
    return False


def verify_grounding(
    card: RecommendationCard,
    packet: EnginePacket,
    config: GroundingConfig = DEFAULT_CONFIG,
) -> GroundingReport:
    """Run every grounding check over ``card`` given its source ``packet``."""

    violations: list[Violation] = []
    pool_ids = packet.evidence_ids
    packet_values = [
        item.value for item in packet.evidence_pool if item.value is not None
    ]

    # EVIDENCE_RESOLUTION -------------------------------------------------
    for claim in card.claims:
        for evidence_id in claim.evidence_ids:
            if evidence_id not in pool_ids:
                violations.append(
                    Violation(
                        code=ViolationCode.EVIDENCE_RESOLUTION,
                        severity=Severity.CLAIM,
                        detail=(
                            f"claim {claim.claim_id} references evidence "
                            f"{evidence_id!r} which is absent from the packet"
                        ),
                        offending_claim_id=claim.claim_id,
                    )
                )
    for recommendation in card.recommendations:
        for evidence_id in recommendation.evidence_ids:
            if evidence_id not in pool_ids:
                violations.append(
                    Violation(
                        code=ViolationCode.EVIDENCE_RESOLUTION,
                        severity=Severity.CLAIM,
                        detail=(
                            f"recommendation {recommendation.recommendation_id} "
                            f"references evidence {evidence_id!r} which is absent "
                            "from the packet"
                        ),
                        offending_claim_id=recommendation.recommendation_id,
                    )
                )
    for refuting in card.refuting_evidence_considered:
        if refuting.evidence_id not in pool_ids:
            violations.append(
                Violation(
                    code=ViolationCode.EVIDENCE_RESOLUTION,
                    severity=Severity.CLAIM,
                    detail=(
                        f"refuting evidence {refuting.evidence_id!r} is absent "
                        "from the packet"
                    ),
                    offending_claim_id=None,
                )
            )

    # UNCITED_CLAIM -------------------------------------------------------
    for claim in card.claims:
        if claim.claim_type in EVIDENCE_BEARING_CLAIM_TYPES and not claim.evidence_ids:
            violations.append(
                Violation(
                    code=ViolationCode.UNCITED_CLAIM,
                    severity=Severity.CLAIM,
                    detail=(
                        f"{claim.claim_type.value} claim {claim.claim_id} cites no "
                        "evidence"
                    ),
                    offending_claim_id=claim.claim_id,
                )
            )

    # NUMERIC_PROVENANCE --------------------------------------------------
    for claim in card.claims:
        if claim.numeric_value is None:
            continue
        if not _resolves_to_packet_value(claim, packet_values):
            violations.append(
                Violation(
                    code=ViolationCode.NUMERIC_PROVENANCE,
                    severity=Severity.CLAIM,
                    detail=(
                        f"numeric value {claim.numeric_value} in claim "
                        f"{claim.claim_id} does not resolve to any value in the "
                        "packet within tolerance"
                    ),
                    offending_claim_id=claim.claim_id,
                )
            )

    # ALTERNATIVES_REQUIRED ----------------------------------------------
    if card.has_causal_claim() and (
        len(card.alternatives) < config.minimum_alternatives
        or len(card.refuting_evidence_considered) < config.minimum_refuting_evidence
    ):
        violations.append(
            Violation(
                code=ViolationCode.ALTERNATIVES_REQUIRED,
                severity=Severity.STRUCTURAL,
                detail=(
                    "a causal claim requires at least "
                    f"{config.minimum_alternatives} ranked alternatives and "
                    f"{config.minimum_refuting_evidence} item(s) of refuting "
                    f"evidence; found {len(card.alternatives)} alternative(s) "
                    f"and {len(card.refuting_evidence_considered)} refuting item(s)"
                ),
                offending_claim_id=None,
            )
        )

    # FORBIDDEN_ASSERTION -------------------------------------------------
    for claim in card.claims:
        topic = _forbidden_topic(claim.statement)
        if topic is not None:
            violations.append(
                Violation(
                    code=ViolationCode.FORBIDDEN_ASSERTION,
                    severity=Severity.STRUCTURAL,
                    detail=(
                        f"claim {claim.claim_id} asserts a {topic} result, which "
                        "is outside the platform's advisory scope"
                    ),
                    offending_claim_id=claim.claim_id,
                )
            )
    for recommendation in card.recommendations:
        topic = _forbidden_topic(recommendation.text)
        if topic is not None:
            violations.append(
                Violation(
                    code=ViolationCode.FORBIDDEN_ASSERTION,
                    severity=Severity.STRUCTURAL,
                    detail=(
                        f"recommendation {recommendation.recommendation_id} asserts "
                        f"a {topic} result, which is outside the platform's "
                        "advisory scope"
                    ),
                    offending_claim_id=recommendation.recommendation_id,
                )
            )

    # CONTROL_LANGUAGE ----------------------------------------------------
    for claim in card.claims:
        if contains_control_language(claim.statement):
            violations.append(
                Violation(
                    code=ViolationCode.CONTROL_LANGUAGE,
                    severity=Severity.STRUCTURAL,
                    detail=(
                        f"claim {claim.claim_id} contains imperative control "
                        "language directed at equipment"
                    ),
                    offending_claim_id=claim.claim_id,
                )
            )
    for recommendation in card.recommendations:
        if contains_control_language(recommendation.text):
            violations.append(
                Violation(
                    code=ViolationCode.CONTROL_LANGUAGE,
                    severity=Severity.STRUCTURAL,
                    detail=(
                        f"recommendation {recommendation.recommendation_id} contains "
                        "imperative control language directed at equipment"
                    ),
                    offending_claim_id=recommendation.recommendation_id,
                )
            )

    # SUFFICIENCY_FLOOR ---------------------------------------------------
    if (
        card.is_substantive()
        and card.provenance_summary.data_sufficiency < config.sufficiency_floor
        and card.health_band is not HealthBand.INSUFFICIENT_DATA
    ):
        violations.append(
            Violation(
                code=ViolationCode.SUFFICIENCY_FLOOR,
                severity=Severity.STRUCTURAL,
                detail=(
                    "data sufficiency "
                    f"{card.provenance_summary.data_sufficiency:.3f} is below the "
                    f"floor {config.sufficiency_floor:.3f}; a substantive card is "
                    "not permitted and it must report INSUFFICIENT_DATA"
                ),
                offending_claim_id=None,
            )
        )

    # SYNTHETIC_LABEL -----------------------------------------------------
    if card.provenance_summary.is_entirely_synthetic:
        properly_labelled = (
            card.status is CardStatus.PRELIMINARY
            and bool(card.demonstration_marker)
        )
        if not properly_labelled:
            violations.append(
                Violation(
                    code=ViolationCode.SYNTHETIC_LABEL,
                    severity=Severity.LABEL,
                    detail=(
                        "card is built on entirely synthetic data but is not "
                        "labelled PRELIMINARY with a demonstration marker"
                    ),
                    offending_claim_id=None,
                )
            )

    stripped = sorted(
        {
            violation.offending_claim_id
            for violation in violations
            if violation.severity is Severity.CLAIM
            and violation.offending_claim_id is not None
        }
    )

    return GroundingReport(
        passed=not violations,
        violations=violations,
        stripped_claim_ids=stripped,
    )


def enforce(
    card: RecommendationCard,
    packet: EnginePacket,
    config: GroundingConfig = DEFAULT_CONFIG,
) -> RecommendationCard:
    """Return a card that carries no un-remediated grounding violation.

    Claim-level violations strip the offending claim; structural violations
    downgrade the whole card to ``INSUFFICIENT_DATA``; a synthetic-label
    violation corrects the labelling. The grounding report is always attached so
    that a violation is never silently passed through.
    """

    report = verify_grounding(card, packet, config)
    if report.passed:
        return card.model_copy(update={"grounding_report": report})

    strip_ids = set(report.stripped_claim_ids)
    has_structural = any(
        violation.severity is Severity.STRUCTURAL for violation in report.violations
    )
    needs_synthetic_label = (
        any(
            violation.code is ViolationCode.SYNTHETIC_LABEL
            for violation in report.violations
        )
        or card.provenance_summary.is_entirely_synthetic
    )

    updates: dict[str, object] = {"grounding_report": report}

    if needs_synthetic_label:
        updates["status"] = CardStatus.PRELIMINARY
        updates["demonstration_marker"] = DEMONSTRATION_MARKER

    if has_structural:
        structural_reasons = [
            f"{violation.code.value}: {violation.detail}"
            for violation in report.violations
            if violation.severity is Severity.STRUCTURAL
        ]
        updates["health_band"] = HealthBand.INSUFFICIENT_DATA
        updates["claims"] = []
        updates["recommendations"] = []
        updates["alternatives"] = []
        updates["refuting_evidence_considered"] = []
        updates["confidence"] = ConfidenceComponents.zero()
        updates["reasons"] = [*card.reasons, *structural_reasons]
    else:
        updates["claims"] = [
            claim for claim in card.claims if claim.claim_id not in strip_ids
        ]
        updates["recommendations"] = [
            rec
            for rec in card.recommendations
            if rec.recommendation_id not in strip_ids
        ]

    return card.model_copy(update=updates)
