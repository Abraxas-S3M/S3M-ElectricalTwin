"""Tests for the immutable safety posture."""

from __future__ import annotations

from typing import Final, get_type_hints

from packages.canonical_electrical_model import safety
from packages.canonical_electrical_model.safety import (
    ADVISORY_STATEMENT,
    CONTROL_WRITE_ENABLED,
    EQUIPMENT_CONTROL_VERBS,
    ControlBoundary,
    assert_read_only,
    control_boundary,
)


def test_control_write_is_disabled():
    assert CONTROL_WRITE_ENABLED is False


def test_control_write_is_typed_final():
    hints = get_type_hints(safety, include_extras=True)
    assert hints["CONTROL_WRITE_ENABLED"] is Final[bool]


def test_assert_read_only_does_not_raise():
    assert assert_read_only() is None


def test_control_boundary_is_read_only():
    boundary = control_boundary()
    assert isinstance(boundary, ControlBoundary)
    assert boundary.control_write_enabled is False
    assert boundary.posture == "advisory-read-only"


def test_control_boundary_has_advisory_statement():
    assert control_boundary().advisory_statement == ADVISORY_STATEMENT


def test_control_boundary_lists_prohibited_and_permitted():
    boundary = control_boundary()
    assert boundary.prohibited_actions
    assert boundary.permitted_actions


def test_equipment_control_verbs_cover_required_set():
    for verb in ("open", "close", "trip", "start", "stop", "set", "write", "adjust"):
        assert verb in EQUIPMENT_CONTROL_VERBS


def test_advisory_statement_mentions_read_only():
    assert "read-only" in ADVISORY_STATEMENT
