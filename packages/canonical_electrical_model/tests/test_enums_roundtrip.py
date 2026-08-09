"""Round-trip and contract tests for every canonical enumeration."""

from __future__ import annotations

import inspect
from enum import Enum

import pytest

from packages.canonical_electrical_model import enums as enums_module
from packages.canonical_electrical_model.enums import _CanonicalStrEnum


def _all_canonical_enums() -> list[type[_CanonicalStrEnum]]:
    """Return every concrete canonical string enum defined in the module."""
    found: list[type[_CanonicalStrEnum]] = []
    for _, obj in inspect.getmembers(enums_module, inspect.isclass):
        if (
            issubclass(obj, _CanonicalStrEnum)
            and obj is not _CanonicalStrEnum
            and obj.__module__ == enums_module.__name__
        ):
            found.append(obj)
    return found


CANONICAL_ENUMS = _all_canonical_enums()
ALL_MEMBERS = [member for enum_cls in CANONICAL_ENUMS for member in enum_cls]


def test_discovered_enum_set_is_complete() -> None:
    names = {cls.__name__ for cls in CANONICAL_ENUMS}
    assert names == {
        "AssetType",
        "SwitchState",
        "EnergizationState",
        "SourceType",
        "Criticality",
        "PowerQualityEventType",
        "DataProvenance",
        "ValidationState",
        "HealthBand",
        "ApprovalStatus",
        "DataQuality",
        "PhaseTag",
        "TelemetryChannel",
    }


@pytest.mark.parametrize("member", ALL_MEMBERS, ids=lambda m: f"{type(m).__name__}.{m.name}")
def test_member_value_equals_name(member: _CanonicalStrEnum) -> None:
    assert member.value == member.name


@pytest.mark.parametrize("member", ALL_MEMBERS, ids=lambda m: f"{type(m).__name__}.{m.name}")
def test_member_roundtrips_through_string_value(member: _CanonicalStrEnum) -> None:
    enum_cls = type(member)
    # value -> member
    assert enum_cls(member.value) is member
    # member -> value -> member, and str behaviour is the bare token
    assert isinstance(member, str)
    assert str(member) == member.value
    assert enum_cls(str(member)) is member


@pytest.mark.parametrize("enum_cls", CANONICAL_ENUMS, ids=lambda c: c.__name__)
def test_member_values_are_unique_and_string(enum_cls: type[_CanonicalStrEnum]) -> None:
    values = [m.value for m in enum_cls]
    assert all(isinstance(v, str) for v in values)
    assert len(values) == len(set(values))


def test_expected_member_counts() -> None:
    from packages.canonical_electrical_model import AssetType, TelemetryChannel

    assert len(list(AssetType)) == 27
    assert len(list(TelemetryChannel)) == 35


def test_is_str_enum() -> None:
    for enum_cls in CANONICAL_ENUMS:
        assert issubclass(enum_cls, str)
        assert issubclass(enum_cls, Enum)


def test_pydantic_v2_roundtrip() -> None:
    """The enums must serialise/validate cleanly under pydantic v2."""
    import pydantic

    assert pydantic.VERSION.startswith("2.")

    from packages.canonical_electrical_model import AssetType, PhaseTag

    class _Sample(pydantic.BaseModel):
        asset: AssetType
        phase: PhaseTag

    parsed = _Sample.model_validate({"asset": "TRANSFORMER", "phase": "A"})
    assert parsed.asset is AssetType.TRANSFORMER
    assert parsed.phase is PhaseTag.A
    dumped = parsed.model_dump(mode="json")
    assert dumped == {"asset": "TRANSFORMER", "phase": "A"}
