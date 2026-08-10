"""Environment-driven configuration and fail-closed startup checks.

Configuration is read from the environment so the same image can run in
different postures. The two supported deployment profiles are:

* ``standard`` — the ordinary advisory posture.
* ``one_way_diode`` — the platform sits behind a unidirectional gateway and must
  **never** initiate a connection toward the operational-technology (OT) side.

Both profiles are read-only. :func:`assert_safe_startup` is called at
application startup and fails closed if any safety invariant is not satisfied.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from packages.canonical_electrical_model.safety import assert_read_only


class DeploymentProfile(str, Enum):
    """Supported deployment postures."""

    STANDARD = "standard"
    ONE_WAY_DIODE = "one_way_diode"


class UnsafeConfigurationError(RuntimeError):
    """Raised when the configuration would violate a safety invariant."""


@dataclass(frozen=True)
class Settings:
    """Resolved, immutable settings for a running service instance."""

    deployment_profile: DeploymentProfile
    log_level: str
    service_name: str
    #: Whether the platform is permitted to open a connection toward the OT
    #: side. This is fixed to ``False`` — there is no code path that sets it
    #: ``True`` — and it is asserted explicitly under the one-way-diode profile.
    ot_outbound_connections_allowed: bool = False


def _read_profile(raw: str | None) -> DeploymentProfile:
    value = (raw or DeploymentProfile.STANDARD.value).strip().lower()
    try:
        return DeploymentProfile(value)
    except ValueError as exc:
        supported = ", ".join(profile.value for profile in DeploymentProfile)
        raise UnsafeConfigurationError(
            f"unsupported DEPLOYMENT_PROFILE {value!r}; supported: {supported}"
        ) from exc


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from the environment (or a supplied mapping)."""

    env = environ if environ is not None else dict(os.environ)
    return Settings(
        deployment_profile=_read_profile(env.get("DEPLOYMENT_PROFILE")),
        log_level=(env.get("LOG_LEVEL") or "INFO").strip().upper(),
        service_name=(env.get("SERVICE_NAME") or "electricaltwin-api").strip(),
    )


def assert_safe_startup(settings: Settings) -> None:
    """Fail closed unless every safety invariant holds for ``settings``.

    * The platform must be read-only (:func:`assert_read_only`).
    * Under the one-way-diode profile the platform must never be permitted to
      initiate a connection toward the OT side.
    """

    assert_read_only()

    if (
        settings.deployment_profile is DeploymentProfile.ONE_WAY_DIODE
        and settings.ot_outbound_connections_allowed
    ):
        raise UnsafeConfigurationError(
            "one_way_diode profile forbids the platform from initiating any "
            "connection toward the OT side, but ot_outbound_connections_allowed "
            "is True"
        )
