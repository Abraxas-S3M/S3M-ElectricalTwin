"""Shared base model and value objects for the canonical electrical model.

The base model deliberately forbids extra fields. This is a structural guard
that supports one of the package's core invariants: models describe *observed*
and *rated* reality only, and callers cannot smuggle in an unexpected field
(for example, one that might carry a setpoint, command, or write target).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CanonicalModel(BaseModel):
    """Base for every canonical model.

    ``extra="forbid"`` rejects unknown fields at construction time, and
    ``validate_assignment=True`` ensures field-level constraints (including
    ``frozen``) are enforced on assignment as well as construction.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class Location(CanonicalModel):
    """Physical location of an asset. All fields optional and synthetic."""

    site: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    area: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    description: Optional[str] = None
