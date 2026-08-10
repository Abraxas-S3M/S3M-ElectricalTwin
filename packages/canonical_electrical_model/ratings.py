"""Rated / nameplate data and edge impedance.

These models describe *rated* characteristics (nameplate data, design values).
Nothing here is a setpoint or a command: a rated value is a static property of
an asset, not an instruction to it.
"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from .common import CanonicalModel
from .provenance import Provenanced


class RatedData(CanonicalModel):
    """Nameplate / rated characteristics of an asset.

    Every field is optional and individually provenance-labelled via
    :class:`Provenanced`.
    """

    voltage_v: Provenanced[float] | None = None
    current_a: Provenanced[float] | None = None
    kva: Provenanced[float] | None = None
    kw: Provenanced[float] | None = None
    power_factor: Provenanced[float] | None = None
    frequency_hz: Provenanced[float] | None = None
    impedance_percent: Provenanced[float] | None = None
    vector_group: Provenanced[str] | None = None
    insulation_class: Provenanced[str] | None = None
    temperature_rise_k: Provenanced[float] | None = None
    interrupting_kaic: Provenanced[float] | None = None
    operations_rated: Provenanced[int] | None = None
    no_load_loss_kw: Provenanced[float] | None = None
    load_loss_kw: Provenanced[float] | None = None
    manufacturer: Provenanced[str] | None = None
    model: Provenanced[str] | None = None
    serial: Provenanced[str] | None = None
    commissioned_on: Provenanced[date] | None = None


class EdgeImpedance(CanonicalModel):
    """Series impedance and physical length of an edge. All optional."""

    r_ohm: float | None = Field(default=None)
    x_ohm: float | None = Field(default=None)
    length_m: float | None = Field(default=None, ge=0.0)
