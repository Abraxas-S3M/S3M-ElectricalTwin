"""The operator-facing artefact an S3M engine emits: :class:`RecommendationCard`.

A card is the grounded output of a single routing decision. Every quantitative
or causal statement it makes must be traceable to evidence that was present in
the originating packet's ``evidence_pool``. That grounding contract is enforced
structurally: a card containing a ``NUMERIC``, ``CATEGORICAL`` or ``CAUSAL``
claim with no cited evidence is INVALID and cannot be constructed.

No language model is involved anywhere in Work Package 0. The ``model_version``
and ``prompt_template_version`` fields exist so the contract is stable for later
work packages; here they default to a sentinel indicating no model was used.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from .packet import ControlBoundary, Evidence
from .routing import EngineClass, RoutingDecision, Urgency

__all__ = [
    "ClaimKind",
    "ValidationState",
    "ApprovalStatus",
    "Claim",
    "RankedCause",
    "FinancialExposure",
    "GroundingReport",
    "RecommendationConfidence",
    "RecommendationCard",
    "NO_MODEL_SENTINEL",
]

# Sentinel recorded on artefacts produced without any language-model call.
NO_MODEL_SENTINEL: str = "none"


class ClaimKind(str, Enum):
    """The nature of a single claim made on a card."""

    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    CAUSAL = "CAUSAL"
    RECOMMENDATION = "RECOMMENDATION"
    CONTEXTUAL = "CONTEXTUAL"


# Claim kinds that assert a checkable fact and therefore MUST cite evidence.
_EVIDENCE_REQUIRED_KINDS: frozenset[ClaimKind] = frozenset(
    {ClaimKind.NUMERIC, ClaimKind.CATEGORICAL, ClaimKind.CAUSAL}
)


class ValidationState(str, Enum):
    """How far a card has progressed through validation."""

    NOT_VALIDATED = "NOT_VALIDATED"
    PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class ApprovalStatus(str, Enum):
    """The operator-review lifecycle of a card."""

    PENDING_OPERATOR_REVIEW = "PENDING_OPERATOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class Claim(BaseModel):
    """A single statement a card makes.

    ``evidence_ids`` reference :class:`~packages.s3m_engine_contract.packet.Evidence`
    entries from the originating packet's evidence pool.
    """

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    text: str
    claim_kind: ClaimKind
    evidence_ids: list[str] = Field(default_factory=list)
    resolved: bool = False


class RankedCause(BaseModel):
    """A candidate cause with its rank and supporting evidence."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    description: str
    likelihood: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)


class FinancialExposure(BaseModel):
    """A synthetic estimate of financial exposure."""

    model_config = ConfigDict(extra="forbid")

    amount: float = Field(ge=0.0)
    currency: str = "USD"
    basis: str = ""


class GroundingReport(BaseModel):
    """A summary of how well a card's claims are grounded in evidence."""

    model_config = ConfigDict(extra="forbid")

    total_claims: int = Field(default=0, ge=0)
    grounded_claims: int = Field(default=0, ge=0)
    ungrounded_claim_ids: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def coverage_ratio(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return round(self.grounded_claims / self.total_claims, 6)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_fully_grounded(self) -> bool:
        return not self.ungrounded_claim_ids


# Plain-language names for each confidence component, used to report the
# dominant (weakest) limitation.
_CONFIDENCE_COMPONENT_LABELS: dict[str, str] = {
    "data_sufficiency": "data sufficiency",
    "model_maturity": "model maturity",
    "physics_agreement": "physics agreement",
    "historical_precedent": "historical precedent",
}


class RecommendationConfidence(BaseModel):
    """Confidence in a card, decomposed into named components.

    ``composite`` is COMPUTED as the equal-weighted mean of the four components
    and is never directly assignable — attempting to pass ``composite`` (or any
    other unknown field) raises a validation error, so the composite can never
    be set inconsistently with its components. ``dominant_limitation`` names the
    weakest component in plain language.
    """

    model_config = ConfigDict(extra="forbid")

    data_sufficiency: float = Field(ge=0.0, le=1.0)
    model_maturity: float = Field(ge=0.0, le=1.0)
    physics_agreement: float = Field(ge=0.0, le=1.0)
    historical_precedent: float = Field(ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def composite(self) -> float:
        return round(
            (
                self.data_sufficiency
                + self.model_maturity
                + self.physics_agreement
                + self.historical_precedent
            )
            / 4.0,
            6,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dominant_limitation(self) -> str:
        components = {
            "data_sufficiency": self.data_sufficiency,
            "model_maturity": self.model_maturity,
            "physics_agreement": self.physics_agreement,
            "historical_precedent": self.historical_precedent,
        }
        # Deterministic tie-break: the declared order above wins on ties.
        weakest_key = min(components, key=lambda key: (components[key], list(components).index(key)))
        return _CONFIDENCE_COMPONENT_LABELS[weakest_key]


class RecommendationCard(BaseModel):
    """A grounded, operator-facing recommendation.

    Invariant: any ``NUMERIC``, ``CATEGORICAL`` or ``CAUSAL`` claim must cite at
    least one piece of evidence. This is enforced by :meth:`_enforce_grounding`.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    node_ids: list[str] = Field(default_factory=list)
    urgency: Urgency
    rationale: str
    evidence: list[Evidence] = Field(default_factory=list)
    ranked_causes: list[RankedCause] = Field(default_factory=list)
    recommended_inspection: str | None = None
    recommended_action: str | None = None
    estimated_financial_exposure: FinancialExposure | None = None
    validation_state: ValidationState = ValidationState.NOT_VALIDATED
    control_boundary: ControlBoundary = Field(default_factory=ControlBoundary)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_OPERATOR_REVIEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    packet_id: str
    packet_hash: str
    engine_class: EngineClass
    routing_decision: RoutingDecision
    model_version: str = NO_MODEL_SENTINEL
    prompt_template_version: str = NO_MODEL_SENTINEL
    output_hash: str = ""
    grounding_report: GroundingReport = Field(default_factory=GroundingReport)
    confidence: RecommendationConfidence
    claims: list[Claim] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_grounding(self) -> "RecommendationCard":
        offending = [
            claim.claim_id
            for claim in self.claims
            if claim.claim_kind in _EVIDENCE_REQUIRED_KINDS and not claim.evidence_ids
        ]
        if offending:
            raise ValueError(
                "Card is invalid: the following claims assert a checkable fact "
                "but cite no evidence: " + ", ".join(offending)
            )
        return self
