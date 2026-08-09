"""Analytic contracts.

These models define the *shape* of analytic outputs produced by later work
packages (health scoring, anomaly detection, power-quality classification,
root-cause ranking). They are declared here so producers and consumers agree
on the contract now; the fields are populated later.

The package is read-only by design. :class:`ControlBoundary` makes that
explicit and enforces it: it is a frozen assertion that control writes are
disabled and human approval is required. Constructing it with any other value
raises.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field, model_validator

from .common import CanonicalModel
from .enums import (
    AnomalyDomain,
    ContributionDirection,
    HealthBand,
    ITICRegion,
    PhaseTag,
    PowerQualityEventType,
    Severity,
    ValidationState,
)
from .provenance import Provenance


class Evidence(CanonicalModel):
    """A piece of observed-vs-expected evidence supporting an analytic claim."""

    kind: str
    node_id: str
    channel: str
    window_start: datetime
    window_end: datetime
    observed: Optional[float] = None
    expected: Optional[float] = None
    unit: Optional[str] = None
    provenance: Provenance = Field(default_factory=Provenance)
    source_ref: Optional[str] = None


class HealthContribution(CanonicalModel):
    """One weighted factor contributing to a health score."""

    factor_name: str
    weight: float
    contribution: float
    direction: ContributionDirection
    explanation: str


class HealthScore(CanonicalModel):
    """A health score for a node, with explainable contributions."""

    node_id: str
    score: float = Field(ge=0.0, le=100.0)
    band: HealthBand
    contributions: list[HealthContribution] = Field(default_factory=list)
    uncertainty_low: Optional[float] = None
    uncertainty_high: Optional[float] = None
    validation_state: ValidationState = ValidationState.PENDING
    computed_at: datetime
    insufficient_data_reasons: list[str] = Field(default_factory=list)


class AnomalyResult(CanonicalModel):
    """A detected anomaly with its supporting evidence."""

    node_id: str
    domain: AnomalyDomain
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    residual: Optional[float] = None
    expected: Optional[float] = None
    observed: Optional[float] = None
    evidence: list[Evidence] = Field(default_factory=list)
    validation_state: ValidationState = ValidationState.PENDING


class PowerQualityEvent(CanonicalModel):
    """A classified power-quality event."""

    node_id: str
    event_type: PowerQualityEventType
    started_at: datetime
    ended_at: Optional[datetime] = None
    magnitude_pu: Optional[float] = Field(default=None, ge=0.0)
    duration_ms: Optional[float] = Field(default=None, ge=0.0)
    affected_phases: list[PhaseTag] = Field(default_factory=list)
    itic_region: Optional[ITICRegion] = None
    standard_reference: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)


class RankedCause(CanonicalModel):
    """A ranked root-cause hypothesis."""

    hypothesis: str
    rank: int = Field(ge=1)
    likelihood: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[Evidence] = Field(default_factory=list)
    refuting_evidence: list[Evidence] = Field(default_factory=list)


class ControlBoundary(CanonicalModel):
    """Frozen assertion that this system does not perform control writes.

    Both boolean fields are frozen. The invariant is enforced at construction:
    ``requires_human_approval`` must be ``True`` and ``control_write_enabled``
    must be ``False``. Constructing with any other value raises.
    """

    requires_human_approval: bool = Field(frozen=True, default=True)
    control_write_enabled: bool = Field(frozen=True, default=False)
    rationale: str

    @model_validator(mode="after")
    def _enforce_read_only_boundary(self) -> "ControlBoundary":
        if self.requires_human_approval is not True:
            raise ValueError(
                "ControlBoundary.requires_human_approval must be True; "
                "this system requires human approval and cannot disable it."
            )
        if self.control_write_enabled is not False:
            raise ValueError(
                "ControlBoundary.control_write_enabled must be False; "
                "this system does not perform control writes."
            )
        return self
