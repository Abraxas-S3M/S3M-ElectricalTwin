"""Recommendation cards, claims, evidence and confidence.

A :class:`RecommendationCard` is the only artefact the reasoning engine is
allowed to emit toward an operator. Everything a card asserts must be expressed
as a :class:`Claim`, and every claim that makes a factual assertion must cite
:class:`Evidence` drawn from the input packet's evidence pool. Causal claims
additionally carry ranked :class:`Alternative` hypotheses and the refuting
evidence that was considered.

These models are pure data. The rules that decide whether a card is *grounded*
live in :mod:`packages.s3m_engine_contract.grounding`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from packages.canonical_electrical_model.provenance import (
    DataProvenance,
    ValidationState,
)


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class HealthBand(str, Enum):
    """The headline assessment a card carries.

    ``INSUFFICIENT_DATA`` is not a failure mode; it is the correct, honest
    answer whenever the evidence does not support a substantive conclusion.
    """

    HEALTHY = "healthy"
    ELEVATED_ATTENTION = "elevated_attention"
    DEGRADED = "degraded"
    AT_RISK = "at_risk"
    INSUFFICIENT_DATA = "insufficient_data"


class CardStatus(str, Enum):
    """The maturity/labelling of a card, orthogonal to its :class:`HealthBand`."""

    PRELIMINARY = "preliminary"
    PROVISIONAL = "provisional"
    REVIEWED = "reviewed"


class ClaimType(str, Enum):
    """The kinds of assertion a claim can make."""

    #: A statement about a quantity; must resolve to a value in the packet.
    NUMERIC = "numeric"
    #: A statement placing something into a category; must cite evidence.
    CATEGORICAL = "categorical"
    #: A statement asserting cause; must cite evidence and carry alternatives.
    CAUSAL = "causal"
    #: Framing or context that asserts no external fact; needs no evidence.
    NARRATIVE = "narrative"


#: Claim types that make an external factual assertion and therefore require
#: supporting evidence. ``NARRATIVE`` is deliberately excluded.
EVIDENCE_BEARING_CLAIM_TYPES: frozenset[ClaimType] = frozenset(
    {ClaimType.NUMERIC, ClaimType.CATEGORICAL, ClaimType.CAUSAL}
)


class Audience(str, Enum):
    """Who a recommendation is addressed to. Only humans are ever addressed."""

    HUMAN_OPERATOR = "human_operator"
    LICENSED_ENGINEER = "licensed_engineer"


class Evidence(BaseModel):
    """A single item of evidence in a packet's evidence pool."""

    model_config = {"frozen": True}

    evidence_id: str = Field(..., min_length=1)
    description: str = ""
    value: float | None = None
    unit: str | None = None
    provenance: DataProvenance = DataProvenance.INFERRED
    validation_state: ValidationState = ValidationState.UNVALIDATED


class Alternative(BaseModel):
    """A ranked alternative hypothesis considered for a causal claim."""

    model_config = {"frozen": True}

    alternative_id: str = Field(..., min_length=1)
    description: str
    rank: int = Field(..., ge=1)
    relative_likelihood: float = Field(..., ge=0.0, le=1.0)


class RefutingEvidenceRef(BaseModel):
    """A pointer to evidence that was weighed *against* a card's conclusion."""

    model_config = {"frozen": True}

    evidence_id: str = Field(..., min_length=1)
    consideration: str = ""


class Claim(BaseModel):
    """A single assertion made by a card."""

    model_config = {"frozen": True}

    claim_id: str = Field(..., min_length=1)
    claim_type: ClaimType
    statement: str = ""
    evidence_ids: tuple[str, ...] = ()
    numeric_value: float | None = None
    numeric_unit: str | None = None
    #: Absolute + relative tolerance used when resolving ``numeric_value``.
    absolute_tolerance: float = 1e-9
    relative_tolerance: float = 0.01


class Recommendation(BaseModel):
    """A single human-directed recommendation.

    Recommendations are always addressed to a human. They must never contain
    imperative control language directed at equipment; the grounding gate
    enforces this.
    """

    model_config = {"frozen": True}

    recommendation_id: str = Field(..., min_length=1)
    text: str
    audience: Audience = Audience.HUMAN_OPERATOR
    evidence_ids: tuple[str, ...] = ()


class ConfidenceComponents(BaseModel):
    """Decomposed confidence, each component in ``[0, 1]``."""

    model_config = {"frozen": True}

    data_sufficiency: float = Field(0.0, ge=0.0, le=1.0)
    model_fidelity: float = Field(0.0, ge=0.0, le=1.0)
    corroboration: float = Field(0.0, ge=0.0, le=1.0)

    @classmethod
    def zero(cls) -> ConfidenceComponents:
        """Return an all-zero confidence, used by refusal cards."""

        return cls(data_sufficiency=0.0, model_fidelity=0.0, corroboration=0.0)


class ProvenanceSummary(BaseModel):
    """A card-level roll-up of where its supporting data came from."""

    model_config = {"frozen": True}

    is_entirely_synthetic: bool = False
    data_sufficiency: float = Field(0.0, ge=0.0, le=1.0)
    dominant_provenance: DataProvenance = DataProvenance.INFERRED
    dominant_validation_state: ValidationState = ValidationState.UNVALIDATED


class RecommendationCard(BaseModel):
    """The single artefact the reasoning engine emits toward an operator."""

    card_id: str = Field(..., min_length=1)
    packet_id: str = Field(..., min_length=1)
    health_band: HealthBand
    status: CardStatus = CardStatus.PROVISIONAL
    headline: str = ""
    claims: list[Claim] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    refuting_evidence_considered: list[RefutingEvidenceRef] = Field(default_factory=list)
    confidence: ConfidenceComponents = Field(default_factory=ConfidenceComponents.zero)
    provenance_summary: ProvenanceSummary = Field(default_factory=ProvenanceSummary)
    reasons: list[str] = Field(default_factory=list)
    demonstration_marker: str | None = None
    grounding_report: object | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    def has_causal_claim(self) -> bool:
        """Return ``True`` if any claim asserts causation."""

        return any(claim.claim_type is ClaimType.CAUSAL for claim in self.claims)

    def is_substantive(self) -> bool:
        """Return ``True`` if the card asserts anything beyond a refusal.

        A card is substantive if it carries evidence-bearing claims or any
        recommendation. A bare ``INSUFFICIENT_DATA`` card is not substantive.
        """

        if self.recommendations:
            return True
        return any(
            claim.claim_type in EVIDENCE_BEARING_CLAIM_TYPES for claim in self.claims
        )
