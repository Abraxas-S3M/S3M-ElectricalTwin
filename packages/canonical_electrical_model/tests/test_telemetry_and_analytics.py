"""Tests for telemetry and the analytic contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.canonical_electrical_model import (
    AnomalyDomain,
    AnomalyResult,
    ContributionDirection,
    ElectricalReading,
    Evidence,
    HealthBand,
    HealthContribution,
    HealthScore,
    ITICRegion,
    PhaseTag,
    PowerQualityEvent,
    PowerQualityEventType,
    Quality,
    RankedCause,
    Severity,
    ValidationState,
)

_T0 = datetime(2026, 3, 1, tzinfo=UTC)
_T1 = datetime(2026, 3, 1, 0, 5, tzinfo=UTC)


def test_reading_confidence_bounds():
    r = ElectricalReading(
        node_id="n1",
        channel="voltage",
        phase=PhaseTag.A,
        value=277.1,
        unit="V",
        timestamp=_T0,
        quality=Quality.GOOD,
        sensor_confidence=0.92,
    )
    assert 0.0 <= r.sensor_confidence <= 1.0
    with pytest.raises(ValidationError):
        ElectricalReading(
            node_id="n1", channel="voltage", value=1.0, unit="V",
            timestamp=_T0, sensor_confidence=1.5,
        )


def test_analytic_contracts_instantiate():
    ev = Evidence(
        kind="voltage_deviation",
        node_id="n1",
        channel="voltage",
        window_start=_T0,
        window_end=_T1,
        observed=250.0,
        expected=277.0,
        unit="V",
    )
    score = HealthScore(
        node_id="n1",
        score=82.5,
        band=HealthBand.DEGRADED,
        contributions=[
            HealthContribution(
                factor_name="thermal_margin",
                weight=0.4,
                contribution=-5.0,
                direction=ContributionDirection.DEGRADES,
                explanation="synthetic",
            )
        ],
        validation_state=ValidationState.PROVISIONAL,
        computed_at=_T1,
    )
    anomaly = AnomalyResult(
        node_id="n1",
        domain=AnomalyDomain.ELECTRICAL,
        severity=Severity.HIGH,
        confidence=0.8,
        residual=27.0,
        evidence=[ev],
    )
    pqe = PowerQualityEvent(
        node_id="n1",
        event_type=PowerQualityEventType.SAG,
        started_at=_T0,
        ended_at=_T1,
        magnitude_pu=0.85,
        duration_ms=120.0,
        affected_phases=[PhaseTag.A, PhaseTag.B],
        itic_region=ITICRegion.NO_DAMAGE,
        evidence=[ev],
    )
    cause = RankedCause(
        hypothesis="upstream tap change",
        rank=1,
        likelihood=0.7,
        supporting_evidence=[ev],
    )

    assert score.score == 82.5
    assert anomaly.severity is Severity.HIGH
    assert pqe.itic_region is ITICRegion.NO_DAMAGE
    assert cause.rank == 1


def test_analytic_result_round_trips_through_json():
    anomaly = AnomalyResult(
        node_id="n1",
        domain=AnomalyDomain.THERMAL,
        severity=Severity.MEDIUM,
        confidence=0.6,
    )
    assert AnomalyResult.model_validate_json(anomaly.model_dump_json()) == anomaly
