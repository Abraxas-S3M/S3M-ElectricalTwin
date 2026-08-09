"""Tests for the frozen, read-only ControlBoundary invariant."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from packages.canonical_electrical_model import ControlBoundary


def test_default_construction_is_read_only():
    cb = ControlBoundary(rationale="canonical model is observe-only")
    assert cb.requires_human_approval is True
    assert cb.control_write_enabled is False


def test_control_write_enabled_true_raises():
    with pytest.raises(ValidationError):
        ControlBoundary(control_write_enabled=True, rationale="x")


def test_requires_human_approval_false_raises():
    with pytest.raises(ValidationError):
        ControlBoundary(requires_human_approval=False, rationale="x")


def test_boolean_fields_are_frozen():
    cb = ControlBoundary(rationale="frozen")
    with pytest.raises(ValidationError):
        cb.control_write_enabled = True
    with pytest.raises(ValidationError):
        cb.requires_human_approval = False
