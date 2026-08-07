"""Determinism and reproducibility of reasoning.

For a reasoning result to be auditable it must be reproducible. This module
pins the knobs that make an invocation deterministic and produces a stable
fingerprint that ties an output back to the exact inputs and versions that
produced it (see ``docs/adr/ADR-0008``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any


class NonDeterministicConfigError(ValueError):
    """Raised when an invocation configuration is not provably deterministic."""


def invocation_fingerprint(
    packet_hash: str,
    prompt_template_version: str,
    model_version: str,
    engine_class: str,
) -> str:
    """Return a stable fingerprint for a single reasoning invocation.

    The fingerprint is the SHA-256 of the pinned inputs joined with a delimiter
    that cannot appear in the component strings, so two different component
    tuples can never collide onto the same joined string.
    """

    payload = "\x1f".join(
        (
            "s3m-invocation-v1",
            packet_hash,
            prompt_template_version,
            model_version,
            engine_class,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assert_deterministic_config(config: Mapping[str, Any]) -> None:
    """Raise unless ``config`` describes a provably deterministic invocation.

    The requirements are:

    * ``temperature`` is exactly ``0``,
    * ``top_p`` is exactly ``1``,
    * ``model_version`` is a non-empty pinned string,
    * ``prompt_template_version`` is a non-empty pinned string.
    """

    if "temperature" not in config:
        raise NonDeterministicConfigError("temperature is required and must be 0")
    temperature = config["temperature"]
    if not isinstance(temperature, (int, float)) or isinstance(temperature, bool) or temperature != 0:
        raise NonDeterministicConfigError(
            f"temperature must be exactly 0, got {temperature!r}"
        )

    if "top_p" not in config:
        raise NonDeterministicConfigError("top_p is required and must be 1")
    top_p = config["top_p"]
    if not isinstance(top_p, (int, float)) or isinstance(top_p, bool) or top_p != 1:
        raise NonDeterministicConfigError(f"top_p must be exactly 1, got {top_p!r}")

    for key in ("model_version", "prompt_template_version"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise NonDeterministicConfigError(
                f"{key} must be a non-empty pinned string, got {value!r}"
            )
