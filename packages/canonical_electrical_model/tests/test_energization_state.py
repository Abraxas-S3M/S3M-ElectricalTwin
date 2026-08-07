"""Tests documenting the EnergizationState / SwitchState contract."""

from __future__ import annotations

from packages.canonical_electrical_model import EnergizationState, SwitchState


def test_energization_state_members_and_order() -> None:
    assert [e.value for e in EnergizationState] == [
        "ENERGIZED_PRIMARY",
        "ENERGIZED_BACKUP",
        "ENERGIZED_UPS",
        "DE_ENERGIZED",
        "ISOLATED_FOR_MAINTENANCE",
        "INDETERMINATE",
    ]


def test_indeterminate_and_unknown_exist() -> None:
    # INDETERMINATE is the mandatory result whenever a switch on the path is
    # UNKNOWN. The resolution logic lives in a later chunk; here we assert the
    # vocabulary needed to express "never guess" is present.
    assert EnergizationState.INDETERMINATE.value == "INDETERMINATE"
    assert SwitchState.UNKNOWN.value == "UNKNOWN"
