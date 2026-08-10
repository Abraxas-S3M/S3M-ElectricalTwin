"""The deterministic grounding gate.

``verify_grounding`` is the deterministic verifier that sits between the
reasoning engine and the operator. It contains **no language model**: it is a
pure, rule-based audit of a :class:`RecommendationCard` against the
:class:`ElectricalTwinPacket` it was produced from.

The gate never *trusts* a card. Every quantitative or causal statement a card
makes must trace back to evidence that was present in the packet's closed-world
``evidence_pool``; a number the engine invented, a claim with no citation, a
lone unchallenged hypothesis, an assertion the platform is not permitted to
make, or an imperative directed at equipment are each recorded as a named
violation. :func:`enforce` then applies the report: it strips the offending
claims, downgrades a structurally unsound card to an ``INSUFFICIENT_DATA``
refusal, and attaches the report so nothing passes silently.

Evidence in the packet's ``evidence_pool`` is cited by its ``source_ref`` and
carries ``observed``/``expected`` values; a card's claims reference those
``source_ref`` tokens and may assert a ``numeric_value`` that must resolve to a
value present in the pool.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

from packages.canonical_electrical_model import HealthBand, ValidationState

from .card import (
    ClaimKind,
    GroundingReport,
    GroundingViolation,
    RecommendationCard,
)
from .packet import ElectricalTwinPacket

__all__ = [
    "GroundingCheck",
    "Severity",
    "GroundingConfig",
    "DEFAULT_GROUNDING_CONFIG",
    "CHECK_DEFINITIONS",
    "GroundingReport",
    "GroundingViolation",
    "verify_grounding",
    "enforce",
]


class GroundingCheck(str, Enum):
    """The named checks the deterministic grounding gate performs."""

    EVIDENCE_RESOLUTION = "EVIDENCE_RESOLUTION"
    UNCITED_CLAIM = "UNCITED_CLAIM"
    NUMERIC_PROVENANCE = "NUMERIC_PROVENANCE"
    ALTERNATIVES_REQUIRED = "ALTERNATIVES_REQUIRED"
    FORBIDDEN_ASSERTION = "FORBIDDEN_ASSERTION"
    CONTROL_LANGUAGE = "CONTROL_LANGUAGE"
    SUFFICIENCY_FLOOR = "SUFFICIENCY_FLOOR"
    SYNTHETIC_LABEL = "SYNTHETIC_LABEL"


class Severity(str, Enum):
    """Severity of a grounding violation."""

    ERROR = "ERROR"
    WARNING = "WARNING"


#: Plain-language definition of each check, surfaced by the API.
CHECK_DEFINITIONS: dict[str, str] = {
    GroundingCheck.EVIDENCE_RESOLUTION.value: (
        "Every evidence identifier referenced by a claim must exist in the "
        "packet's closed-world evidence pool."
    ),
    GroundingCheck.UNCITED_CLAIM.value: (
        "A numeric, categorical or causal claim must cite at least one piece of "
        "evidence. Soft (recommendation/contextual) claims need not."
    ),
    GroundingCheck.NUMERIC_PROVENANCE.value: (
        "Every numeric value a card asserts must resolve to a value present in "
        "the packet within tolerance. A number the engine invented is rejected."
    ),
    GroundingCheck.ALTERNATIVES_REQUIRED.value: (
        "A card that makes a causal claim must carry at least two ranked "
        "alternatives and must have considered at least one item of refuting "
        "evidence, so no single hypothesis stands unchallenged."
    ),
    GroundingCheck.FORBIDDEN_ASSERTION.value: (
        "The card must not assert calibration, formal validation, code "
        "compliance, protection coordination, selectivity or arc-flash results; "
        "those are licensed-engineer deliverables, not S3M outputs."
    ),
    GroundingCheck.CONTROL_LANGUAGE.value: (
        "The card must not contain imperative control language directed at "
        "equipment (open, close, trip, start, stop, set, write, adjust). "
        "Recommendations addressed to a human operator are permitted."
    ),
    GroundingCheck.SUFFICIENCY_FLOOR.value: (
        "When the packet's data-sufficiency composite is below the configured "
        "floor, the card must be an INSUFFICIENT_DATA refusal rather than a "
        "substantive recommendation."
    ),
    GroundingCheck.SYNTHETIC_LABEL.value: (
        "When the packet is entirely synthetic, the card must be marked as a "
        "preliminary demonstration and must not present itself as a validated "
        "result."
    ),
}


@dataclass(frozen=True)
class GroundingConfig:
    """Tunable thresholds for the grounding gate (deterministic, no model)."""

    sufficiency_floor: float = 0.5
    numeric_abs_tol: float = 1e-6
    numeric_rel_tol: float = 1e-3


DEFAULT_GROUNDING_CONFIG = GroundingConfig()

# Claim kinds that assert a checkable fact and therefore MUST cite evidence.
_CHECKABLE_KINDS = frozenset(
    {ClaimKind.NUMERIC, ClaimKind.CATEGORICAL, ClaimKind.CAUSAL}
)

# Claim-attributable checks; the rest are structural (card-level) violations.
_CLAIM_LEVEL_CODES = frozenset(
    {
        GroundingCheck.EVIDENCE_RESOLUTION.value,
        GroundingCheck.UNCITED_CLAIM.value,
        GroundingCheck.NUMERIC_PROVENANCE.value,
    }
)

# Substrings that, in a card's operator-facing text, would assert a result the
# platform is not authorised to produce.
_FORBIDDEN_ASSERTIONS: tuple[str, ...] = (
    "calibrat",              # calibration / calibrated
    "arc flash",
    "arc-flash",
    "arcflash",
    "protection coordinat",  # protection coordination / coordinated
    "coordination study",
    "selectivit",            # selectivity / selective
    "code compliance",
    "code-compliant",
    "compliant with the code",
    "nfpa 70e",
    "formally validated",
    "fully validated",
    "validation confirms",
    "has been validated",
)

# Imperative control verbs that must never be directed at equipment.
_CONTROL_VERBS = ("open", "close", "trip", "start", "stop", "set", "write", "adjust")

# Equipment nouns a control verb might target.
_EQUIPMENT_NOUNS = (
    "breaker", "switch", "relay", "feeder", "bus", "busbar", "panel", "valve",
    "drive", "vfd", "plc", "device", "disconnect", "contactor", "recloser",
    "tap", "setpoint", "set point", "register", "coil", "transformer", "motor",
)

# Framing that marks text as a recommendation to a human, not a command.
_HUMAN_FRAMING = (
    "recommend", "advise", "advis", "suggest", "consider", "should ",
    "the operator", "a qualified", "an engineer", "engineer ", "propose",
    "we recommend", "it is recommended", "operator to", "personnel",
)

_CONTROL_PATTERN = re.compile(
    r"\b(" + "|".join(_CONTROL_VERBS) + r")\b\s+(?:the\s+|a\s+|an\s+)?(?:"
    + "|".join(re.escape(noun) for noun in _EQUIPMENT_NOUNS)
    + r")\b",
    re.IGNORECASE,
)


def _card_text_fields(card: RecommendationCard) -> list[str]:
    """Return the operator-facing free-text fragments carried by a card."""

    fragments = [card.title, card.rationale]
    if card.recommended_inspection:
        fragments.append(card.recommended_inspection)
    if card.recommended_action:
        fragments.append(card.recommended_action)
    fragments.extend(claim.text for claim in card.claims)
    return fragments


def _imperative_fragments(card: RecommendationCard) -> list[str]:
    """Fragments that could carry an instruction (actions and claim text)."""

    fragments: list[str] = []
    if card.recommended_action:
        fragments.append(card.recommended_action)
    if card.recommended_inspection:
        fragments.append(card.recommended_inspection)
    fragments.extend(claim.text for claim in card.claims)
    return fragments


def _numbers_within_tolerance(value: float, candidate: float, cfg: GroundingConfig) -> bool:
    return math.isclose(
        value, candidate, rel_tol=cfg.numeric_rel_tol, abs_tol=cfg.numeric_abs_tol
    )


def _pool_ids(packet: ElectricalTwinPacket) -> set[str]:
    return {ev.source_ref for ev in packet.evidence_pool if ev.source_ref is not None}


def _pool_values(packet: ElectricalTwinPacket) -> list[float]:
    values: list[float] = []
    for ev in packet.evidence_pool:
        for candidate in (ev.observed, ev.expected):
            if candidate is not None:
                values.append(candidate)
    return values


def _is_substantive(card: RecommendationCard) -> bool:
    """A card is substantive if it recommends action or asserts checkable facts."""

    if card.recommended_action or card.recommended_inspection:
        return True
    if card.ranked_causes:
        return True
    return any(claim.claim_kind in _CHECKABLE_KINDS for claim in card.claims)


def _is_insufficient_data(card: RecommendationCard) -> bool:
    return (
        card.health_band is HealthBand.INSUFFICIENT_DATA
        or card.validation_state is ValidationState.INSUFFICIENT_DATA
    )


def verify_grounding(
    card: RecommendationCard,
    packet: ElectricalTwinPacket,
    config: GroundingConfig = DEFAULT_GROUNDING_CONFIG,
) -> GroundingReport:
    """Audit *card* against *packet* and return a :class:`GroundingReport`.

    The function is pure and deterministic: the same card and packet always
    yield the same report. It never mutates its inputs.
    """

    violations: list[GroundingViolation] = []
    pool_ids = _pool_ids(packet)
    pool_values = _pool_values(packet)

    # EVIDENCE_RESOLUTION + UNCITED_CLAIM + NUMERIC_PROVENANCE (claim level).
    for claim in card.claims:
        dangling = [eid for eid in claim.evidence_ids if eid not in pool_ids]
        if dangling:
            violations.append(
                GroundingViolation(
                    code=GroundingCheck.EVIDENCE_RESOLUTION.value,
                    severity=Severity.ERROR.value,
                    detail=(
                        f"Claim {claim.claim_id!r} cites evidence not present in "
                        f"the packet evidence pool: {', '.join(dangling)}."
                    ),
                    claim_id=claim.claim_id,
                )
            )
        if claim.claim_kind in _CHECKABLE_KINDS and not claim.evidence_ids:
            violations.append(
                GroundingViolation(
                    code=GroundingCheck.UNCITED_CLAIM.value,
                    severity=Severity.ERROR.value,
                    detail=(
                        f"Claim {claim.claim_id!r} is a {claim.claim_kind.value} "
                        "claim but cites no evidence."
                    ),
                    claim_id=claim.claim_id,
                )
            )
        if claim.claim_kind is ClaimKind.NUMERIC and claim.numeric_value is not None:
            resolved = any(
                _numbers_within_tolerance(claim.numeric_value, candidate, config)
                for candidate in pool_values
            )
            if not resolved:
                violations.append(
                    GroundingViolation(
                        code=GroundingCheck.NUMERIC_PROVENANCE.value,
                        severity=Severity.ERROR.value,
                        detail=(
                            f"Claim {claim.claim_id!r} asserts the value "
                            f"{claim.numeric_value!r}, which does not resolve to "
                            "any value in the packet within tolerance."
                        ),
                        claim_id=claim.claim_id,
                    )
                )

    # ALTERNATIVES_REQUIRED.
    has_causal = any(c.claim_kind is ClaimKind.CAUSAL for c in card.claims)
    if has_causal:
        enough_alternatives = len(card.ranked_causes) >= 2
        considered_refutation = any(
            cause.refuting_evidence for cause in card.ranked_causes
        )
        if not (enough_alternatives and considered_refutation):
            violations.append(
                GroundingViolation(
                    code=GroundingCheck.ALTERNATIVES_REQUIRED.value,
                    severity=Severity.ERROR.value,
                    detail=(
                        "A card asserting a causal claim must carry at least two "
                        "ranked alternatives and at least one item of refuting "
                        f"evidence considered (found {len(card.ranked_causes)} "
                        f"alternative(s), refutation considered: "
                        f"{considered_refutation})."
                    ),
                    claim_id=None,
                )
            )

    # FORBIDDEN_ASSERTION.
    haystack = " \n ".join(_card_text_fields(card)).lower()
    for phrase in _FORBIDDEN_ASSERTIONS:
        if phrase in haystack:
            violations.append(
                GroundingViolation(
                    code=GroundingCheck.FORBIDDEN_ASSERTION.value,
                    severity=Severity.ERROR.value,
                    detail=(
                        "The card asserts a result the platform is not authorised "
                        f"to produce (matched phrase: {phrase!r})."
                    ),
                    claim_id=None,
                )
            )
            break

    # CONTROL_LANGUAGE.
    for fragment in _imperative_fragments(card):
        lowered = fragment.lower()
        if _CONTROL_PATTERN.search(fragment) and not any(
            marker in lowered for marker in _HUMAN_FRAMING
        ):
            violations.append(
                GroundingViolation(
                    code=GroundingCheck.CONTROL_LANGUAGE.value,
                    severity=Severity.ERROR.value,
                    detail=(
                        "The card contains imperative control language directed "
                        f"at equipment: {fragment!r}. Phrase recommendations to a "
                        "human operator instead."
                    ),
                    claim_id=None,
                )
            )
            break

    # SUFFICIENCY_FLOOR.
    if (
        packet.data_sufficiency.composite < config.sufficiency_floor
        and _is_substantive(card)
        and not _is_insufficient_data(card)
    ):
        violations.append(
            GroundingViolation(
                code=GroundingCheck.SUFFICIENCY_FLOOR.value,
                severity=Severity.ERROR.value,
                detail=(
                    "Packet data-sufficiency composite "
                    f"{packet.data_sufficiency.composite} is below the floor "
                    f"{config.sufficiency_floor}; a substantive card is not "
                    "permitted and it must be an INSUFFICIENT_DATA refusal."
                ),
                claim_id=None,
            )
        )

    # SYNTHETIC_LABEL.
    if packet.provenance_summary.is_entirely_synthetic:
        allowed_states = {ValidationState.PRELIMINARY, ValidationState.INSUFFICIENT_DATA}
        if not (card.is_demonstration and card.validation_state in allowed_states):
            violations.append(
                GroundingViolation(
                    code=GroundingCheck.SYNTHETIC_LABEL.value,
                    severity=Severity.ERROR.value,
                    detail=(
                        "The packet is entirely synthetic, so the card must be a "
                        "PRELIMINARY, demonstration-marked artefact and must not "
                        "present itself as a validated result."
                    ),
                    claim_id=None,
                )
            )

    return GroundingReport(passed=not violations, violations=violations)


def enforce(
    card: RecommendationCard,
    packet: ElectricalTwinPacket,
    config: GroundingConfig = DEFAULT_GROUNDING_CONFIG,
) -> RecommendationCard:
    """Return a grounded card, applying the report. Never passes a violation.

    Claim-attributable violations cause the offending claims to be stripped.
    Structural violations downgrade the card to an ``INSUFFICIENT_DATA`` refusal
    (recommendations removed). The resulting :class:`GroundingReport` (with the
    stripped claim ids recorded) is attached to the returned card.
    """

    report = verify_grounding(card, packet, config)

    stripped_ids = sorted(
        {
            violation.claim_id
            for violation in report.violations
            if violation.claim_id is not None and violation.code in _CLAIM_LEVEL_CODES
        }
    )
    has_structural = any(
        violation.claim_id is None or violation.code not in _CLAIM_LEVEL_CODES
        for violation in report.violations
    )

    surviving_claims = [c for c in card.claims if c.claim_id not in stripped_ids]

    updates: dict[str, object] = {"claims": surviving_claims}
    if has_structural:
        updates.update(
            validation_state=ValidationState.INSUFFICIENT_DATA,
            health_band=HealthBand.INSUFFICIENT_DATA,
            recommended_action=None,
            recommended_inspection=None,
            ranked_causes=[],
            estimated_financial_exposure=None,
            is_demonstration=(
                card.is_demonstration
                or packet.provenance_summary.is_entirely_synthetic
            ),
        )

    enforced = card.model_copy(update=updates)

    final_report = verify_grounding(enforced, packet, config).model_copy(
        update={"stripped_claim_ids": stripped_ids}
    )
    return enforced.model_copy(update={"grounding_report": final_report})
