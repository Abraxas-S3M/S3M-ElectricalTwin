"""Canonical electrical model: shared enumerations and value vocabularies.

This package provides the controlled vocabularies (enumerations) that the S3M
ElectricalTwin packages agree on. All data described here is synthetic.
"""

from __future__ import annotations

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
