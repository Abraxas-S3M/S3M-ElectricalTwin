"""Tests for environment-driven configuration and startup safety invariants."""

from __future__ import annotations

import pytest
from app.config import (
    AppConfig,
    DeploymentProfile,
    assert_startup_invariants,
    load_config,
)


def test_default_profile_is_standard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S3M_DEPLOYMENT_PROFILE", raising=False)
    config = load_config()
    assert config.deployment_profile is DeploymentProfile.STANDARD
    assert config.allow_ot_outbound is False


def test_one_way_diode_profile_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3M_DEPLOYMENT_PROFILE", "one_way_diode")
    config = load_config()
    assert config.deployment_profile is DeploymentProfile.ONE_WAY_DIODE


def test_unknown_profile_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3M_DEPLOYMENT_PROFILE", "bidirectional")
    with pytest.raises(ValueError):
        load_config()


def test_startup_invariants_pass_for_read_only_standard() -> None:
    # Returns None (raises on any violation); reaching the next line is success.
    assert_startup_invariants(AppConfig())


def test_startup_fails_closed_when_ot_outbound_permitted() -> None:
    config = AppConfig(
        deployment_profile=DeploymentProfile.ONE_WAY_DIODE,
        allow_ot_outbound=True,
    )
    with pytest.raises(RuntimeError):
        assert_startup_invariants(config)


def test_standard_profile_also_forbids_ot_outbound() -> None:
    config = AppConfig(
        deployment_profile=DeploymentProfile.STANDARD,
        allow_ot_outbound=True,
    )
    with pytest.raises(RuntimeError):
        assert_startup_invariants(config)
