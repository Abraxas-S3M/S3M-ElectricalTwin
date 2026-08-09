"""Rated / nameplate data and edge impedance.

These models describe *rated* characteristics (nameplate data, design values).
Nothing here is a setpoint or a command: a rated value is a static property of
an asset, not an instruction to it.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import Field

from .common import CanonicalModel
from .provenance import Provenanced


class RatedData(CanonicalModel):
    """Nameplate / rated characteristics of an asset.

    Every field is optional and individually provenance-labelled via
    :class:`Provenanced`.
    """

    voltage_v: Optional[Provenanced[float]] = None
    current_a: Optional[Provenanced[float]] = None
    kva: Optional[Provenanced[float]] = None
    kw: Optional[Provenanced[float]] = None
    power_factor: Optional[Provenanced[float]] = None
    frequency_hz: Optional[Provenanced[float]] = None
    impedance_percent: Optional[Provenanced[float]] = None
    vector_group: Optional[Provenanced[str]] = None
    insulation_class: Optional[Provenanced[str]] = None
    temperature_rise_k: Optional[Provenanced[float]] = None
    interrupting_kaic: Optional[Provenanced[float]] = None
    operations_rated: Optional[Provenanced[int]] = None
    no_load_loss_kw: Optional[Provenanced[float]] = None
    load_loss_kw: Optional[Provenanced[float]] = None
    manufacturer: Optional[Provenanced[str]] = None
    model: Optional[Provenanced[str]] = None
    serial: Optional[Provenanced[str]] = None
    commissioned_on: Optional[Provenanced[date]] = None


class EdgeImpedance(CanonicalModel):
    """Series impedance and physical length of an edge. All optional."""

    r_ohm: Optional[float] = Field(default=None)
    x_ohm: Optional[float] = Field(default=None)
    length_m: Optional[float] = Field(default=None, ge=0.0)
