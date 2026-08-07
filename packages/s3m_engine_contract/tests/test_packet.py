"""Packet hashing is canonical, stable and value-sensitive."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.s3m_engine_contract.packet import (
    DataSufficiency,
    ElectricalTwinPacket,
    Evidence,
    HISTORY_TARGET_HOURS,
    PacketClass,
    ProvenanceSummary,
    Reading,
    TopologyNode,
    TopologySnapshot,
    Urgency,
    compute_packet_hash,
)


def _build_packet(**overrides) -> ElectricalTwinPacket:
    base = dict(
        packet_id="pkt-0001",
        packet_class=PacketClass.ALARM_TRIAGE,
        urgency=Urgency.IMMEDIATE,
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        facility_id="fac-synthetic-1",
        node_ids=["n1", "n2"],
        window_start=datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        readings=[
            Reading(
                node_id="n1",
                channel="voltage",
                timestamp=datetime(2026, 1, 1, 11, 30, 0, tzinfo=timezone.utc),
                value=11.0,
                unit="kV",
                quality=1.0,
            )
        ],
        topology_snapshot=TopologySnapshot(
            captured_at=datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            nodes=[TopologyNode(node_id="n1", node_type="bus")],
            edges=[],
        ),
        evidence_pool=[
            Evidence(
                evidence_id="ev-1",
                kind="measurement",
                statement="Voltage at n1 is 11.0 kV.",
                node_ids=["n1"],
                value=11.0,
                unit="kV",
            )
        ],
        provenance_summary=ProvenanceSummary(is_entirely_synthetic=True),
        data_sufficiency=DataSufficiency(
            channel_coverage=0.9,
            quality_ratio=0.95,
            history_depth_hours=84.0,
            metering_completeness=0.8,
        ),
    )
    base.update(overrides)
    return ElectricalTwinPacket(**base)


def test_identical_packets_hash_identically() -> None:
    assert compute_packet_hash(_build_packet()) == compute_packet_hash(_build_packet())


def test_one_value_change_alters_hash() -> None:
    baseline = compute_packet_hash(_build_packet())
    changed = compute_packet_hash(_build_packet(facility_id="fac-synthetic-2"))
    assert baseline != changed


def test_deep_value_change_alters_hash() -> None:
    baseline = compute_packet_hash(_build_packet())
    mutated_readings = [
        Reading(
            node_id="n1",
            channel="voltage",
            timestamp=datetime(2026, 1, 1, 11, 30, 0, tzinfo=timezone.utc),
            value=11.5,  # single value changed
            unit="kV",
            quality=1.0,
        )
    ]
    assert compute_packet_hash(_build_packet(readings=mutated_readings)) != baseline


def test_hash_excludes_the_hash_field_itself() -> None:
    packet = _build_packet()
    digest = compute_packet_hash(packet)
    stamped = _build_packet(packet_hash=digest)
    # Storing the digest on the packet must not change the computed hash.
    assert compute_packet_hash(stamped) == digest


def test_hash_is_timezone_normalised() -> None:
    utc_packet = _build_packet(
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    naive_packet = _build_packet(created_at=datetime(2026, 1, 1, 12, 0, 0))
    # Naive timestamps are treated as UTC, so these are the same instant.
    assert compute_packet_hash(utc_packet) == compute_packet_hash(naive_packet)


def test_data_sufficiency_composite_is_computed() -> None:
    ds = DataSufficiency(
        channel_coverage=1.0,
        quality_ratio=1.0,
        history_depth_hours=HISTORY_TARGET_HOURS,
        metering_completeness=1.0,
    )
    assert ds.composite == 1.0

    partial = DataSufficiency(
        channel_coverage=0.5,
        quality_ratio=0.5,
        history_depth_hours=HISTORY_TARGET_HOURS / 2,
        metering_completeness=0.5,
    )
    assert partial.composite == 0.5


def test_provenance_reports_synthetic() -> None:
    assert _build_packet().provenance_summary.is_entirely_synthetic is True


def test_wp0_derived_fields_default_empty() -> None:
    packet = _build_packet()
    assert packet.health_scores == []
    assert packet.anomalies == []
    assert packet.pq_events == []
