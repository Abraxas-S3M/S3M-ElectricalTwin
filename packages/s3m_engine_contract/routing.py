"""The packet-to-engine routing table.

Routing is deterministic and declarative: a :class:`PacketClass` maps to exactly
one :class:`RoutingEntry`, which names the validated calculator responsible for
the physics and whether a validated topology is a precondition. The S3M reasoner
consumes the calculator's output and composes the card; it never substitutes for
the calculation.
"""

from __future__ import annotations

from pydantic import BaseModel

from packages.s3m_engine_contract.packets import EngineClass, EnginePacket, PacketClass


class RoutingEntry(BaseModel):
    """One row of the routing table."""

    model_config = {"frozen": True}

    packet_class: PacketClass
    engine_class: EngineClass
    requires_validated_topology: bool
    rationale: str


ROUTING_TABLE: dict[PacketClass, RoutingEntry] = {
    PacketClass.STEADY_STATE_LOADING: RoutingEntry(
        packet_class=PacketClass.STEADY_STATE_LOADING,
        engine_class=EngineClass.LOAD_FLOW_BALANCED,
        requires_validated_topology=True,
        rationale=(
            "Balanced steady-state loading is a load-flow problem solved by the "
            "pandapower engine; it is only meaningful over a validated topology."
        ),
    ),
    PacketClass.FAULT_LEVEL: RoutingEntry(
        packet_class=PacketClass.FAULT_LEVEL,
        engine_class=EngineClass.SHORT_CIRCUIT_IEC60909,
        requires_validated_topology=True,
        rationale=(
            "Fault-level assessment uses the IEC 60909 short-circuit calculation "
            "provided by pandapower. Protection settings are treated as data only."
        ),
    ),
    PacketClass.CONTINGENCY_N1: RoutingEntry(
        packet_class=PacketClass.CONTINGENCY_N1,
        engine_class=EngineClass.CONTINGENCY_N1,
        requires_validated_topology=True,
        rationale=(
            "N-1 contingency screening iterates load flow over single-element "
            "outages using pandapower."
        ),
    ),
    PacketClass.POWER_QUALITY: RoutingEntry(
        packet_class=PacketClass.POWER_QUALITY,
        engine_class=EngineClass.UNBALANCED_HARMONICS,
        requires_validated_topology=True,
        rationale=(
            "Unbalance and harmonics require a phase-explicit solver; OpenDSS via "
            "dss-python is used."
        ),
    ),
    PacketClass.DISPATCH_ECONOMICS: RoutingEntry(
        packet_class=PacketClass.DISPATCH_ECONOMICS,
        engine_class=EngineClass.DISPATCH_STORAGE,
        requires_validated_topology=False,
        rationale=(
            "Dispatch and storage economics are an optimisation problem handled "
            "by PyPSA."
        ),
    ),
    PacketClass.ASSET_HEALTH: RoutingEntry(
        packet_class=PacketClass.ASSET_HEALTH,
        engine_class=EngineClass.S3M_REASONER,
        requires_validated_topology=False,
        rationale=(
            "Asset-health triage weighs heterogeneous evidence; the S3M reasoner "
            "frames the question and cites evidence but calculates nothing."
        ),
    ),
    PacketClass.ANOMALY_TRIAGE: RoutingEntry(
        packet_class=PacketClass.ANOMALY_TRIAGE,
        engine_class=EngineClass.S3M_REASONER,
        requires_validated_topology=False,
        rationale=(
            "Anomaly triage is a reasoning task: the S3M reasoner correlates "
            "signals and proposes ranked hypotheses for a human to adjudicate."
        ),
    ),
}


def route(packet: EnginePacket) -> RoutingEntry:
    """Return the routing entry for ``packet`` based on its packet class."""

    try:
        return ROUTING_TABLE[packet.packet_class]
    except KeyError as exc:  # pragma: no cover - guarded by the enum
        raise KeyError(f"no routing entry for packet class {packet.packet_class}") from exc


def routing_table_as_dicts() -> list[dict[str, object]]:
    """Return the routing table as plain dictionaries for API serialisation."""

    return [
        {
            "packet_class": entry.packet_class.value,
            "engine_class": entry.engine_class.value,
            "requires_validated_topology": entry.requires_validated_topology,
            "rationale": entry.rationale,
        }
        for entry in ROUTING_TABLE.values()
    ]
