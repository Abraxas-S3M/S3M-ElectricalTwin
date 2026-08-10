"""Determinism and reproducibility guards for S3M reasoning invocations.

Reasoning must be reproducible: the same packet, prompt template and model
version must always yield the same routing and the same grounded card. Work
Package 0 invokes no language model, but the contract is pinned now so later
work packages inherit it.

``invocation_fingerprint`` derives a stable identifier for one reasoning
invocation from its inputs. ``assert_deterministic_config`` refuses any engine
configuration that is not fully deterministic and fully pinned.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

__all__ = [
    "invocation_fingerprint",
    "assert_deterministic_config",
]


def invocation_fingerprint(
    packet_hash: str,
    prompt_template_version: str,
    model_version: str,
    engine_class: str,
) -> str:
    """Return a stable sha256 fingerprint for one reasoning invocation.

    The fingerprint is a pure function of the four pinned inputs. Two
    invocations with identical inputs share a fingerprint; changing any single
    input changes it. The inputs are joined with a delimiter that cannot occur
    in a hex packet hash so distinct tuples cannot collide by concatenation.
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
    """Raise unless *config* describes a fully deterministic, pinned invocation.

    The configuration is acceptable only when ``temperature == 0``,
    ``top_p == 1`` and both ``model_version`` and ``prompt_template_version`` are
    non-empty pinned strings.

    Raises:
        ValueError: if any determinism requirement is not met.
    """

    temperature = config.get("temperature")
    if temperature != 0:
        raise ValueError(
            "Non-deterministic configuration: temperature must be 0, got "
            f"{temperature!r}."
        )

    top_p = config.get("top_p")
    if top_p != 1:
        raise ValueError(
            f"Non-deterministic configuration: top_p must be 1, got {top_p!r}."
        )

    for key in ("model_version", "prompt_template_version"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Non-reproducible configuration: {key} must be a non-empty "
                f"pinned string, got {value!r}."
            )
