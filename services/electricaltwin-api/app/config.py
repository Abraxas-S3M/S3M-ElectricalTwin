"""Environment-driven configuration and startup safety assertions.

The service is advisory and read-only. Two deployment profiles are supported:

``standard``
    The service exposes read-only advisory endpoints.
``one_way_diode``
    The service is deployed behind a one-way (data-diode) boundary. The
    platform must **never initiate a connection toward the OT side**. This is
    asserted at startup and the service fails closed if the configuration would
    permit an outbound OT connection.

:func:`assert_read_only` from the canonical safety module is invoked at startup
so the hard platform read-only invariant is checked before the service serves
any request.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from packages.canonical_electrical_model import assert_read_only

__all__ = [
    "DeploymentProfile",
    "AppConfig",
    "load_config",
    "assert_startup_invariants",
]


class DeploymentProfile(str, Enum):
    """Supported deployment profiles."""

    STANDARD = "standard"
    ONE_WAY_DIODE = "one_way_diode"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    """Immutable, environment-derived service configuration."""

    service_name: str = "electricaltwin-api"
    deployment_profile: DeploymentProfile = DeploymentProfile.STANDARD
    # Whether the platform is permitted to initiate a connection toward the OT
    # side. This is always False for an advisory, read-only platform; under the
    # one_way_diode profile it is enforced as a hard, fail-closed invariant.
    allow_ot_outbound: bool = False


def load_config() -> AppConfig:
    """Build the :class:`AppConfig` from environment variables."""

    profile_raw = os.environ.get("S3M_DEPLOYMENT_PROFILE", "standard").strip().lower()
    try:
        profile = DeploymentProfile(profile_raw)
    except ValueError as exc:
        raise ValueError(
            f"Unknown S3M_DEPLOYMENT_PROFILE {profile_raw!r}; supported profiles "
            f"are: {', '.join(p.value for p in DeploymentProfile)}."
        ) from exc

    return AppConfig(
        service_name=os.environ.get("S3M_SERVICE_NAME", "electricaltwin-api"),
        deployment_profile=profile,
        allow_ot_outbound=_env_bool("S3M_ALLOW_OT_OUTBOUND", default=False),
    )


def assert_startup_invariants(config: AppConfig) -> None:
    """Assert every hard safety invariant at startup; fail closed otherwise.

    Raises:
        RuntimeError: if the read-only invariant is violated, or if the
            configuration would permit the platform to initiate a connection
            toward the OT side under the one_way_diode profile.
    """

    # Hard platform read-only invariant.
    assert_read_only()

    # The platform never initiates a connection toward the OT side. Under the
    # one_way_diode profile this is a fail-closed invariant.
    if config.allow_ot_outbound:
        raise RuntimeError(
            "Fail-closed: the platform must never initiate a connection toward "
            "the OT side. S3M ElectricalTwin is advisory and read-only."
        )
