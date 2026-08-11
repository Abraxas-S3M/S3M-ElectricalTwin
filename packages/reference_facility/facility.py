"""Reference-facility electrical model (single-line + engineering parameters).

This module defines the *synthetic* reference facility that the telemetry
generator drives. It is a generic hot-climate light-industrial site fed from a
single medium-voltage utility service through a step-down transformer to a
480 V main switchboard. No real site, city, or country is named; every value
here is synthetic and for modelling only.

The model is a **radial tree** rooted at the utility service. Each node records
the resistance/reactance of the feeder connecting it to its parent so that the
telemetry generator can model cable losses and enforce a parent-child power
balance (parent power == sum of children + modelled losses). The tree shape and
the per-node driver coefficients are the sole source of truth shared by
:mod:`packages.reference_facility.topology` (which projects it onto the canonical
:class:`~packages.canonical_electrical_model.TopologySnapshot`) and
:mod:`packages.reference_facility.telemetry` (which generates readings).

Nothing in this module is a setpoint, command, or control action: it is a
static description of rated reality only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from packages.canonical_electrical_model import AssetType, SourceType

LV_VOLTAGE_V: float = 480.0
"""Nominal line-to-line voltage of the low-voltage network (V)."""

MV_VOLTAGE_V: float = 13800.0
"""Nominal line-to-line voltage of the medium-voltage service (V)."""

NOMINAL_FREQUENCY_HZ: float = 60.0
"""Nominal system frequency (Hz) for the target market."""


class NodeRole(str, Enum):
    """Electrical role a node plays in the generation model.

    The role selects which driver equations and telemetry channels apply. It is
    an internal modelling concept and is distinct from the canonical
    :class:`~packages.canonical_electrical_model.AssetType`.
    """

    SOURCE = "SOURCE"
    TRANSFORMER = "TRANSFORMER"
    BUS = "BUS"
    VFD_LOAD = "VFD_LOAD"
    LOAD = "LOAD"
    SOLAR_PV = "SOLAR_PV"
    CAPACITOR_BANK = "CAPACITOR_BANK"


@dataclass(frozen=True)
class FacilityNode:
    """One node of the reference facility plus its engineering parameters.

    All power figures are in kilowatts / kilovars; impedances in ohms; voltages
    in volts. Fields default to neutral values so a node only sets what applies
    to its :class:`NodeRole`.
    """

    node_id: str
    name: str
    role: NodeRole
    asset_type: AssetType
    nominal_v_ll: float
    parent_id: str | None = None
    feeder_r_ohm: float = 0.0
    feeder_x_ohm: float = 0.0
    rated_kva: float = 0.0

    # Additive load drivers (see telemetry.P_node): base + shift + thermal + occ.
    base_kw: float = 0.0
    production_coefficient_kw: float = 0.0
    thermal_coefficient_kw: float = 0.0
    occupancy_coefficient_kw: float = 0.0
    load_power_factor: float = 0.90
    rated_kw: float = 0.0

    # Transformer loss model: no_load_loss_kw + load_loss_kw * loading**2.
    no_load_loss_kw: float = 0.0
    load_loss_kw: float = 0.0

    # Solar inverter nameplate (kW of DC-derived AC capacity at clear-sky peak).
    pv_capacity_kw: float = 0.0

    # Capacitor bank: kvar per switchable stage and the number of stages.
    cap_stage_kvar: float = 0.0
    cap_max_stages: int = 0


@dataclass(frozen=True)
class FacilitySource:
    """A supply source attached to a node."""

    node_id: str
    source_type: SourceType
    priority: int
    rated_kva: float


@dataclass(frozen=True)
class ReferenceFacility:
    """The complete reference facility for one topology variant."""

    facility_id: str
    variant: str
    nodes: tuple[FacilityNode, ...]
    sources: tuple[FacilitySource, ...]
    tie_edges: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def node(self, node_id: str) -> FacilityNode:
        for candidate in self.nodes:
            if candidate.node_id == node_id:
                return candidate
        raise KeyError(node_id)

    def children_of(self, node_id: str) -> tuple[FacilityNode, ...]:
        """Child nodes of ``node_id`` in stable declaration order."""
        return tuple(n for n in self.nodes if n.parent_id == node_id)

    def metered_balance_groups(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Parent -> children groups that must satisfy a power balance.

        Only buses/transformers with *complete* child metering are returned, so
        a caller can verify ``P_parent == sum(P_children) + losses`` at each.
        """
        groups: list[tuple[str, tuple[str, ...]]] = []
        for node in self.nodes:
            if node.role in (NodeRole.BUS, NodeRole.TRANSFORMER):
                children = self.children_of(node.node_id)
                if children:
                    groups.append(
                        (node.node_id, tuple(c.node_id for c in children))
                    )
        return tuple(groups)


def _base_nodes() -> list[FacilityNode]:
    """The shared node set common to every variant, in stable order."""

    return [
        FacilityNode(
            node_id="UTIL-001",
            name="Utility service",
            role=NodeRole.SOURCE,
            asset_type=AssetType.UTILITY_SERVICE,
            nominal_v_ll=MV_VOLTAGE_V,
            parent_id=None,
            rated_kva=4000.0,
        ),
        FacilityNode(
            node_id="TX-001",
            name="Main transformer 13.8kV/480V",
            role=NodeRole.TRANSFORMER,
            asset_type=AssetType.TRANSFORMER,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="UTIL-001",
            rated_kva=2500.0,
            no_load_loss_kw=3.1,
            load_loss_kw=21.0,
        ),
        FacilityNode(
            node_id="MSB-001",
            name="Main 480V switchboard",
            role=NodeRole.BUS,
            asset_type=AssetType.SWITCHGEAR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="TX-001",
            feeder_r_ohm=0.0009,
            feeder_x_ohm=0.0006,
        ),
        FacilityNode(
            node_id="MCC-001",
            name="Motor control centre",
            role=NodeRole.BUS,
            asset_type=AssetType.SWITCHBOARD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0080,
            feeder_x_ohm=0.0050,
        ),
        FacilityNode(
            node_id="PP-001",
            name="Distribution panelboard",
            role=NodeRole.BUS,
            asset_type=AssetType.PANELBOARD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0120,
            feeder_x_ohm=0.0070,
        ),
        FacilityNode(
            node_id="CAP-001",
            name="Power-factor correction capacitor bank",
            role=NodeRole.CAPACITOR_BANK,
            asset_type=AssetType.CAPACITOR_BANK,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0100,
            feeder_x_ohm=0.0060,
            cap_stage_kvar=50.0,
            cap_max_stages=4,
        ),
        FacilityNode(
            node_id="PV-001",
            name="Rooftop solar PV inverter",
            role=NodeRole.SOLAR_PV,
            asset_type=AssetType.OTHER,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0100,
            feeder_x_ohm=0.0060,
            pv_capacity_kw=300.0,
        ),
        FacilityNode(
            node_id="MTR-001",
            name="Process motor A (VFD)",
            role=NodeRole.VFD_LOAD,
            asset_type=AssetType.MOTOR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MCC-001",
            feeder_r_ohm=0.0200,
            feeder_x_ohm=0.0120,
            base_kw=120.0,
            production_coefficient_kw=260.0,
            load_power_factor=0.84,
            rated_kw=420.0,
        ),
        FacilityNode(
            node_id="MTR-002",
            name="Process motor B (VFD)",
            role=NodeRole.VFD_LOAD,
            asset_type=AssetType.MOTOR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MCC-001",
            feeder_r_ohm=0.0250,
            feeder_x_ohm=0.0150,
            base_kw=90.0,
            production_coefficient_kw=200.0,
            load_power_factor=0.83,
            rated_kw=320.0,
        ),
        FacilityNode(
            node_id="MTR-003",
            name="Process motor C (VFD)",
            role=NodeRole.VFD_LOAD,
            asset_type=AssetType.MOTOR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MCC-001",
            feeder_r_ohm=0.0300,
            feeder_x_ohm=0.0180,
            base_kw=60.0,
            production_coefficient_kw=140.0,
            load_power_factor=0.82,
            rated_kw=220.0,
        ),
        FacilityNode(
            node_id="LIGHT-001",
            name="Lighting load",
            role=NodeRole.LOAD,
            asset_type=AssetType.LOAD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="PP-001",
            feeder_r_ohm=0.0500,
            feeder_x_ohm=0.0250,
            base_kw=15.0,
            occupancy_coefficient_kw=40.0,
            load_power_factor=0.95,
            rated_kw=70.0,
        ),
        FacilityNode(
            node_id="HVAC-001",
            name="HVAC / chiller auxiliary load",
            role=NodeRole.LOAD,
            asset_type=AssetType.LOAD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="PP-001",
            feeder_r_ohm=0.0400,
            feeder_x_ohm=0.0220,
            base_kw=40.0,
            thermal_coefficient_kw=120.0,
            occupancy_coefficient_kw=30.0,
            load_power_factor=0.88,
            rated_kw=220.0,
        ),
        FacilityNode(
            node_id="PLUG-001",
            name="Small-power / plug load",
            role=NodeRole.LOAD,
            asset_type=AssetType.LOAD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="PP-001",
            feeder_r_ohm=0.0600,
            feeder_x_ohm=0.0300,
            base_kw=20.0,
            occupancy_coefficient_kw=35.0,
            load_power_factor=0.90,
            rated_kw=70.0,
        ),
    ]


def reference_facility(variant: str = "base") -> ReferenceFacility:
    """Return the reference facility for a topology ``variant``.

    Variants share the same node set and driver coefficients and differ only in
    their supply arrangement / tie configuration:

    * ``base`` -- single utility service, no tie.
    * ``gen_backup`` -- adds a standby diesel generator source at ``MSB-001``.
    * ``tie_alt`` -- adds a (normally-open) tie between ``MCC-001`` and
      ``PP-001`` recording an alternate feed path.

    Any unrecognised variant falls back to ``base``.
    """

    resolved_variant = variant if variant in ("base", "gen_backup", "tie_alt") else "base"

    nodes = tuple(_base_nodes())
    sources: list[FacilitySource] = [
        FacilitySource(
            node_id="UTIL-001",
            source_type=SourceType.UTILITY,
            priority=0,
            rated_kva=4000.0,
        )
    ]
    tie_edges: tuple[tuple[str, str], ...] = ()

    if resolved_variant == "gen_backup":
        sources.append(
            FacilitySource(
                node_id="MSB-001",
                source_type=SourceType.GENERATOR,
                priority=1,
                rated_kva=1500.0,
            )
        )
    elif resolved_variant == "tie_alt":
        tie_edges = (("MCC-001", "PP-001"),)

    return ReferenceFacility(
        facility_id="FAC-REF-001",
        variant=resolved_variant,
        nodes=nodes,
        sources=tuple(sources),
        tie_edges=tie_edges,
    )


VARIANTS: tuple[str, ...] = ("base", "gen_backup", "tie_alt")
"""The topology variants understood by :func:`reference_facility`."""
