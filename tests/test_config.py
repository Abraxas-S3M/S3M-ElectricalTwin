"""Tests for environment-driven configuration and fail-closed startup."""

from __future__ import annotations

import pytest
from app.config import (
    DeploymentProfile,
    Settings,
    UnsafeConfigurationError,
    assert_safe_startup,
    load_settings,
)


def test_default_profile_is_standard():
    settings = load_settings({})
    assert settings.deployment_profile is DeploymentProfile.STANDARD


def test_profile_read_from_environment():
    settings = load_settings({"DEPLOYMENT_PROFILE": "one_way_diode"})
    assert settings.deployment_profile is DeploymentProfile.ONE_WAY_DIODE


def test_profile_is_case_insensitive():
    settings = load_settings({"DEPLOYMENT_PROFILE": "One_Way_Diode"})
    assert settings.deployment_profile is DeploymentProfile.ONE_WAY_DIODE


def test_unsupported_profile_rejected():
    with pytest.raises(UnsafeConfigurationError):
        load_settings({"DEPLOYMENT_PROFILE": "two_way"})


def test_log_level_read_from_environment():
    settings = load_settings({"LOG_LEVEL": "debug"})
    assert settings.log_level == "DEBUG"


def test_standard_profile_starts_safely():
    settings = load_settings({"DEPLOYMENT_PROFILE": "standard"})
    assert assert_safe_startup(settings) is None


def test_one_way_diode_starts_safely_by_default():
    settings = load_settings({"DEPLOYMENT_PROFILE": "one_way_diode"})
    assert assert_safe_startup(settings) is None


def test_one_way_diode_fails_closed_on_ot_outbound():
    unsafe = Settings(
        deployment_profile=DeploymentProfile.ONE_WAY_DIODE,
        log_level="INFO",
        service_name="electricaltwin-api",
        ot_outbound_connections_allowed=True,
    )
    with pytest.raises(UnsafeConfigurationError):
        assert_safe_startup(unsafe)


def test_ot_outbound_defaults_false():
    settings = load_settings({})
    assert settings.ot_outbound_connections_allowed is False
