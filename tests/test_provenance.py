"""Tests for the provenance and validation vocabularies."""

from __future__ import annotations

from packages.canonical_electrical_model.provenance import (
    DATA_PROVENANCE_DEFINITIONS,
    VALIDATION_STATE_DEFINITIONS,
    DataProvenance,
    ValidationState,
    provenance_vocabulary,
)


def test_every_data_provenance_has_a_definition():
    for member in DataProvenance:
        assert member.value in DATA_PROVENANCE_DEFINITIONS
        assert DATA_PROVENANCE_DEFINITIONS[member.value].strip()


def test_every_validation_state_has_a_definition():
    for member in ValidationState:
        assert member.value in VALIDATION_STATE_DEFINITIONS
        assert VALIDATION_STATE_DEFINITIONS[member.value].strip()


def test_provenance_and_validation_are_disjoint_axes():
    assert set(DataProvenance) != set(ValidationState)


def test_synthetic_provenance_exists():
    assert DataProvenance.SYNTHETIC.value == "synthetic"


def test_disputed_validation_state_exists():
    assert ValidationState.DISPUTED.value == "disputed"


def test_provenance_vocabulary_shape():
    vocab = provenance_vocabulary()
    assert set(vocab.keys()) == {"data_provenance", "validation_state"}
    assert vocab["data_provenance"]["synthetic"]


def test_provenance_vocabulary_is_a_copy():
    vocab = provenance_vocabulary()
    vocab["data_provenance"]["synthetic"] = "mutated"
    assert DATA_PROVENANCE_DEFINITIONS["synthetic"] != "mutated"
