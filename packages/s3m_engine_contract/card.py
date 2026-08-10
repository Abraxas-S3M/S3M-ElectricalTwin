"""The operator-facing artefact the S3M engine produces: a recommendation card.

A :class:`RecommendationCard` is advisory only. It carries its reasoning as a
set of :class:`Claim` objects, each of which must be grounded in the evidence it
cites. The invariant enforced here is structural: any factual claim (numeric,
categorical or causal) that cites no evidence makes the whole card invalid.

The card defaults to ``ApprovalStatus.PENDING_OPERATOR_REVIEW`` and carries the
canonical :class:`ControlBoundary`: nothing here is acted upon without a human
operator, and nothing here controls anything. All data is synthetic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from packages.canonical_electrical_model import (
    ApprovalStatus,
    ControlBoundary,
    Evidence,
    HealthBand,
    RankedCause,
    ValidationState,
)

from .routing import EngineClass, RoutingDecision, Urgency


class ClaimKind(str, Enum):
    """The kind of assertion a claim makes.

    NUMERIC, CATEGORICAL and CAUSAL claims are factual and MUST cite evidence.
    RECOMMENDATION and CONTEXTUAL claims are advisory/framing and need not.
    """

    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    CAUSAL = "CAUSAL"
    RECOMMENDATION = "RECOMMENDATION"
    CONTEXTUAL = "CONTEXTUAL"


#: Claim kinds that must be grounded in at least one piece of evidence.
_MUST_CITE_EVIDENCE: frozenset[ClaimKind] = frozenset(
    {ClaimKind.NUMERIC, ClaimKind.CATEGORICAL, ClaimKind.CAUSAL}
)


class Claim(BaseModel):
    """A single assertion made by the card, with the evidence it cites."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    text: str
    claim_kind: ClaimKind
    evidence_ids: list[str] = Field(default_factory=list)
    numeric_value: float | None = None
    resolved: bool = False


class GroundingCoverage(BaseModel):
    """A summary of whether the card's claims are grounded in evidence."""

    model_config = ConfigDict(extra="forbid")

    grounded: bool = False
    resolved_claim_ids: list[str] = Field(default_factory=list)
    unresolved_claim_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class GroundingViolation(BaseModel):
    """A single failure recorded by the deterministic grounding gate.

    ``code`` is a stable, machine-readable check code (see
    :class:`~packages.s3m_engine_contract.grounding.GroundingCheck`);
    ``claim_id`` names the offending claim when the violation is attributable to
    one, and is ``None`` for structural (card-level) violations.
    """

    model_config = ConfigDict(extra="forbid")

    code: str
    severity: str
    detail: str
    claim_id: str | None = None


class GroundingReport(BaseModel):
    """The verdict of the deterministic grounding gate for one card.

    Produced by :func:`~packages.s3m_engine_contract.grounding.verify_grounding`.
    ``passed`` is ``True`` only when ``violations`` is empty; ``stripped_claim_ids``
    records claims removed by
    :func:`~packages.s3m_engine_contract.grounding.enforce`.
    """

    model_config = ConfigDict(extra="forbid")

    passed: bool
    violations: list[GroundingViolation] = Field(default_factory=list)
    stripped_claim_ids: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FinancialExposure(BaseModel):
    """An advisory estimate of financial exposure. Synthetic and non-binding."""

    model_config = ConfigDict(extra="forbid")

    currency: str = "USD"
    expected_amount: float = Field(ge=0.0)
    low: float | None = Field(default=None, ge=0.0)
    high: float | None = Field(default=None, ge=0.0)
    basis: str | None = None


class RecommendationConfidence(BaseModel):
    """A decomposed, explainable confidence for a recommendation.

    The four components are in ``[0, 1]``. ``composite`` is derived from them
    and is never directly assignable; ``dominant_limitation`` names the weakest
    component in plain language so the reason for a low score is always legible.
    """

    model_config = ConfigDict(extra="forbid")

    data_sufficiency: float = Field(ge=0.0, le=1.0)
    model_maturity: float = Field(ge=0.0, le=1.0)
    physics_agreement: float = Field(ge=0.0, le=1.0)
    historical_precedent: float = Field(ge=0.0, le=1.0)

    def _components(self) -> list[tuple[str, float]]:
        # Fixed order gives a deterministic tie-break for the weakest component.
        return [
            ("data sufficiency", self.data_sufficiency),
            ("model maturity", self.model_maturity),
            ("physics agreement", self.physics_agreement),
            ("historical precedent", self.historical_precedent),
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def composite(self) -> float:
        """Mean of the four components, in ``[0, 1]``."""
        values = [value for _name, value in self._components()]
        return sum(values) / len(values)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dominant_limitation(self) -> str:
        """Plain-language name of the weakest (limiting) component."""
        name, _value = min(self._components(), key=lambda item: item[1])
        return name


class RecommendationCard(BaseModel):
    """An advisory recommendation produced by the S3M engine."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

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
    health_band: HealthBand | None = None
    is_demonstration: bool = False
    insufficient_data_reasons: list[str] = Field(default_factory=list)
    validation_state: ValidationState = ValidationState.PENDING
    control_boundary: ControlBoundary = Field(
        default_factory=lambda: ControlBoundary(
            rationale=(
                "RecommendationCard is advisory; it requires human approval and "
                "performs no control write."
            )
        )
    )
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_OPERATOR_REVIEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    packet_id: str
    packet_hash: str
    engine_class: EngineClass
    routing_decision: RoutingDecision
    # No language model is invoked in Work Package 0; these are recorded for the
    # contract shape and default to explicit "none" markers.
    model_version: str = "none"
    prompt_template_version: str = "none"
    output_hash: str = ""
    grounding_coverage: GroundingCoverage | None = None
    grounding_report: GroundingReport | None = None
    confidence: RecommendationConfidence
    claims: list[Claim] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_evidence_for_factual_claims(self) -> RecommendationCard:
        offenders = [
            claim.claim_id
            for claim in self.claims
            if claim.claim_kind in _MUST_CITE_EVIDENCE and not claim.evidence_ids
        ]
        if offenders:
            raise ValueError(
                "factual claims (NUMERIC/CATEGORICAL/CAUSAL) must cite at least one "
                f"evidence id; uncited claims: {offenders}"
            )
        return self


__all__ = [
    "ClaimKind",
    "Claim",
    "GroundingCoverage",
    "GroundingViolation",
    "GroundingReport",
    "FinancialExposure",
    "RecommendationConfidence",
    "RecommendationCard",
]
