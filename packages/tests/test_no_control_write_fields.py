"""Structural guard: no model may carry a setpoint / command / write / control field.

This enforces the standing rule that the canonical model is observe-only. The
only place the words "control" and "write" may appear as a field is
:class:`ControlBoundary`, whose sole purpose is to assert that control writes
are disabled.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

import packages.canonical_electrical_model as cem
from packages.canonical_electrical_model import ControlBoundary
from packages.canonical_electrical_model.common import CanonicalModel

# Substrings that would indicate a field capable of carrying an outbound
# instruction rather than an observation.
_FORBIDDEN_TOKENS = (
    "setpoint",
    "set_point",
    "command",
    "cmd",
    "actuate",
    "actuation",
    "write",
    "control",
    "dispatch",
    "manipulate",
    "target_value",
    "override",
)


def _all_models():
    for _name, obj in inspect.getmembers(cem, inspect.isclass):
        if issubclass(obj, CanonicalModel) and obj is not CanonicalModel:
            yield obj


def test_no_model_has_control_write_fields():
    offenders = []
    for model in _all_models():
        if model is ControlBoundary:
            # ControlBoundary intentionally names the boundary it disables.
            continue
        for field_name in model.model_fields:
            lowered = field_name.lower()
            if any(token in lowered for token in _FORBIDDEN_TOKENS):
                offenders.append(f"{model.__name__}.{field_name}")
    assert offenders == [], f"control-capable fields found: {offenders}"


def test_models_forbid_extra_fields():
    # extra="forbid" prevents smuggling an unexpected (e.g. control) field in.
    with pytest.raises(ValidationError):
        cem.Facility(id="f", name="n", secret_setpoint_kw=100.0)
