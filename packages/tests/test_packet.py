"""Tests for the ElectricalTwinPacket and its content hash."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.s3m_engine_contract.packet import (
    DataSufficiency,
    ElectricalTwinPacket,
    compute_packet_hash,
)
from packages.s3m_engine_contract.routing import PacketClass, Urgency

_T0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
_T1 = datetime(2026, 5, 1, 1, 0, tzinfo=timezone.utc)


def _sufficiency() -> DataSufficiency:
    return DataSufficiency(
        channel_coverage=0.9,
        quality_ratio=0.85,
        history_depth_hours=336.0,
        metering_completeness=0.95,
    )


def _packet(**overrides) -> ElectricalTwinPacket:
    kwargs = dict(
        packet_id="pkt-1",
        packet_class=PacketClass.LIVE_STATE,
        urgency=Urgency.ROUTINE,
        created_at=_T0,
        facility_id="fac-1",
        node_ids=["n1", "n2"],
        window_start=_T0,
        window_end=_T1,
        data_sufficiency=_sufficiency(),
    )
    kwargs.update(overrides)
    return ElectricalTwinPacket(**kwargs)


def test_identical_packets_hash_identically():
    a = _packet()
    b = _packet()
    assert compute_packet_hash(a) == compute_packet_hash(b)


def test_single_value_change_alters_the_hash():
    base = _packet()
    changed = _packet(facility_id="fac-2")
    assert compute_packet_hash(base) != compute_packet_hash(changed)


def test_hash_excludes_the_hash_field_itself():
    base = _packet()
    digest = compute_packet_hash(base)
    stamped = _packet()
    stamped.packet_hash = digest
    # Stamping the computed hash into the field must not change the hash.
    assert compute_packet_hash(stamped) == digest


def test_data_sufficiency_composite_is_computed():
    ds = _sufficiency()
    history_score = min(1.0, ds.history_depth_hours / 168.0)
    expected = (
        ds.channel_coverage + ds.quality_ratio + ds.metering_completeness + history_score
    ) / 4.0
    assert abs(ds.composite - expected) < 1e-12


def test_provenance_summary_defaults_to_synthetic():
    assert _packet().provenance_summary.is_entirely_synthetic is True


def test_packet_carries_read_only_control_boundary():
    pkt = _packet()
    assert pkt.control_boundary.control_write_enabled is False
    assert pkt.control_boundary.requires_human_approval is True
