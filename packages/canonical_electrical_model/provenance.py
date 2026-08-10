"""Provenance primitives.

Every substantive value in the canonical model is provenance-labelled so that
downstream analytics can reason about *where a number came from* and *how much
to trust it*. Provenance is descriptive metadata only; it never carries a
control action.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import Field

from .common import CanonicalModel


class ProvenanceSource(str, Enum):
    """Origin of a value."""

    MEASURED = "MEASURED"
    NAMEPLATE = "NAMEPLATE"
    DERIVED = "DERIVED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    INFERRED = "INFERRED"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    SIMULATED = "SIMULATED"
    SYNTHETIC = "SYNTHETIC"
    UNKNOWN = "UNKNOWN"


class Provenance(CanonicalModel):
    """Descriptive label recording where a value came from."""

    source: ProvenanceSource = ProvenanceSource.UNKNOWN
    method: str | None = None
    recorded_at: datetime | None = None
    reference: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


T = TypeVar("T")


class Provenanced(CanonicalModel, Generic[T]):
    """A value paired with its provenance label.

    Used to give individual fields their own provenance (for example, the
    rated voltage of a transformer may be NAMEPLATE while its measured load
    loss is MEASURED).
    """

    value: T
    provenance: Provenance = Field(default_factory=Provenance)
