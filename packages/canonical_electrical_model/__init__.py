"""Canonical electrical model.

Pydantic v2 models describing the *observed* and *rated* reality of an
electrical network: topology (a directed graph with live switching state),
telemetry, and the analytic contracts populated by later work packages, plus
the controlled vocabularies (enumerations) shared across the S3M ElectricalTwin
packages.

By design the package is read-only: no model carries a setpoint, command,
write target, or control action, and :class:`ControlBoundary` encodes that
invariant explicitly. All data described here is synthetic.
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
    ApprovalStatus,
    AssetType,
    ContributionDirection,
    Criticality,
    DataProvenance,
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
from .safety import CONTROL_WRITE_ENABLED, assert_read_only
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
    "ApprovalStatus",
    "AssetType",
    "ContributionDirection",
    "Criticality",
    "DataProvenance",
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
    # safety
    "CONTROL_WRITE_ENABLED",
    "assert_read_only",
]
