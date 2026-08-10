"""Canonical electrical model: assets, energization state and safety posture.

This package holds the vocabulary the rest of the platform reasons over:

* :mod:`~packages.canonical_electrical_model.safety` — the immutable read-only
  safety posture and the control boundary description.
* :mod:`~packages.canonical_electrical_model.provenance` — the
  :class:`DataProvenance` and :class:`ValidationState` vocabularies.
* :mod:`~packages.canonical_electrical_model.assets` — the canonical electrical
  asset graph and :class:`EnergizationState`.
"""

from packages.canonical_electrical_model.safety import (
    CONTROL_WRITE_ENABLED,
    ControlBoundary,
    assert_read_only,
    control_boundary,
)

__all__ = [
    "CONTROL_WRITE_ENABLED",
    "ControlBoundary",
    "assert_read_only",
    "control_boundary",
]
"""Canonical electrical model.

Pydantic v2 models describing the *observed* and *rated* reality of an
electrical network: topology (a directed graph with live switching state),
telemetry, and the analytic contracts populated by later work packages.

By design the package is read-only: no model carries a setpoint, command,
write target, or control action, and :class:`ControlBoundary` encodes that
invariant explicitly.
"""Canonical electrical model: shared enumerations and value vocabularies.

This package provides the controlled vocabularies (enumerations) that the S3M
ElectricalTwin packages agree on. All data described here is synthetic.
"""

from __future__ import annotations

from .analytics import (
    AnomalyResult,
    ControlBoundary,
    Evidence,
    HealthContribution,
    HealthScore,
    PowerQualityEvent,
    RankedCause,
)
from .common import CanonicalModel, Location
from .enums import (
    AnomalyDomain,
    AssetType,
    ContributionDirection,
    Criticality,
    EdgeKind,
    HealthBand,
    ITICRegion,
    PhaseTag,
    PowerQualityEventType,
    Quality,
    SectorProfile,
    Severity,
    SourceType,
    SwitchState,
    ValidationState,
)
from .provenance import Provenance, Provenanced, ProvenanceSource
from .ratings import EdgeImpedance, RatedData
from .telemetry import ElectricalReading
from .topology import (
    ElectricalEdge,
    ElectricalNode,
    Facility,
    SourceNode,
    TopologySnapshot,
)

__all__ = [
    # common
    "CanonicalModel",
    "Location",
    # provenance
    "Provenance",
    "Provenanced",
    "ProvenanceSource",
    # enums
    "AnomalyDomain",
    "AssetType",
    "ContributionDirection",
    "Criticality",
    "EdgeKind",
    "HealthBand",
    "ITICRegion",
    "PhaseTag",
    "PowerQualityEventType",
    "Quality",
    "SectorProfile",
    "Severity",
    "SourceType",
    "SwitchState",
    "ValidationState",
    # ratings
    "EdgeImpedance",
    "RatedData",
    # topology
    "ElectricalEdge",
    "ElectricalNode",
    "Facility",
    "SourceNode",
    "TopologySnapshot",
    # telemetry
    "ElectricalReading",
    # analytics
    "AnomalyResult",
    "ControlBoundary",
    "Evidence",
    "HealthContribution",
    "HealthScore",
    "PowerQualityEvent",
    "RankedCause",
]
from .enums import (
    ApprovalStatus,
    AssetType,
    Criticality,
    DataProvenance,
    DataQuality,
    EnergizationState,
    HealthBand,
    PhaseTag,
    PowerQualityEventType,
    SourceType,
    SwitchState,
    TelemetryChannel,
    ValidationState,
    is_customer_sourced,
)

__all__ = [
    "ApprovalStatus",
    "AssetType",
    "Criticality",
    "DataProvenance",
    "DataQuality",
    "EnergizationState",
    "HealthBand",
    "PhaseTag",
    "PowerQualityEventType",
    "SourceType",
    "SwitchState",
    "TelemetryChannel",
    "ValidationState",
    "is_customer_sourced",
]
"""Canonical electrical model for S3M ElectricalTwin (advisory, read-only)."""

from canonical_electrical_model.safety import (
    CONTROL_WRITE_ENABLED,
    assert_read_only,
)

__all__ = ["CONTROL_WRITE_ENABLED", "assert_read_only"]
