"""The canonical electrical asset graph and energization state.

The platform models an electrical network as a directed graph of typed assets
connected by conductors. This module defines the vocabulary of asset and
connection types and the :class:`EnergizationState` an asset can be in. It is
intentionally light: Work Package 0 fixes the vocabulary and the invariants; the
validated physics engines (see ``docs/adr/ADR-0003``) consume this graph but are
not implemented here.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class AssetType(str, Enum):
    """The kinds of node the canonical graph recognises."""

    SOURCE = "source"
    BUSBAR = "busbar"
    TRANSFORMER = "transformer"
    CIRCUIT_BREAKER = "circuit_breaker"
    DISCONNECTOR = "disconnector"
    FEEDER = "feeder"
    LINE = "line"
    LOAD = "load"
    GENERATOR = "generator"
    CAPACITOR_BANK = "capacitor_bank"
    METER = "meter"


class EnergizationState(str, Enum):
    """Whether an asset is currently carrying, or capable of carrying, energy.

    ``UNKNOWN`` is a first-class state: the platform must never silently assume
    a de-energization it cannot evidence.
    """

    ENERGIZED = "energized"
    DE_ENERGIZED = "de_energized"
    GROUNDED = "grounded"
    UNKNOWN = "unknown"


class Asset(BaseModel):
    """A single node in the canonical electrical graph."""

    model_config = {"frozen": True}

    asset_id: str = Field(..., min_length=1)
    asset_type: AssetType
    name: str = ""
    nominal_voltage_kv: float | None = None
    energization: EnergizationState = EnergizationState.UNKNOWN


class Connection(BaseModel):
    """A directed conductor between two assets."""

    model_config = {"frozen": True}

    connection_id: str = Field(..., min_length=1)
    from_asset_id: str = Field(..., min_length=1)
    to_asset_id: str = Field(..., min_length=1)


class AssetGraph(BaseModel):
    """A collection of assets and the connections between them."""

    assets: list[Asset] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_referential_integrity(self) -> AssetGraph:
        known = {asset.asset_id for asset in self.assets}
        if len(known) != len(self.assets):
            raise ValueError("duplicate asset_id in AssetGraph")
        for connection in self.connections:
            for endpoint in (connection.from_asset_id, connection.to_asset_id):
                if endpoint not in known:
                    raise ValueError(
                        f"connection {connection.connection_id} references "
                        f"unknown asset {endpoint}"
                    )
        return self

    def asset(self, asset_id: str) -> Asset | None:
        """Return the asset with ``asset_id`` or ``None`` if it is not present."""

        for candidate in self.assets:
            if candidate.asset_id == asset_id:
                return candidate
        return None
