"""Provenance and validation vocabularies.

Every value the platform reasons over carries two orthogonal labels:

* :class:`DataProvenance` — *where the value came from*.
* :class:`ValidationState` — *how much a human has vouched for it*.

Keeping these separate is deliberate: a value can be measured telemetry
(high-quality provenance) yet still be unvalidated, and a value can be a manual
engineering estimate (weaker provenance) yet field-verified. The definitions are
exposed verbatim through the API so operators and auditors share one vocabulary.
"""

from __future__ import annotations

from enum import Enum


class DataProvenance(str, Enum):
    """Where a value originated."""

    MEASURED_TELEMETRY = "measured_telemetry"
    NAMEPLATE = "nameplate"
    ENGINEERING_STUDY = "engineering_study"
    VENDOR_DOCUMENT = "vendor_document"
    MANUAL_ENTRY = "manual_entry"
    INFERRED = "inferred"
    SYNTHETIC = "synthetic"


class ValidationState(str, Enum):
    """How thoroughly a value has been vouched for by a human."""

    UNVALIDATED = "unvalidated"
    ENGINEER_REVIEWED = "engineer_reviewed"
    FIELD_VERIFIED = "field_verified"
    VALIDATED = "validated"
    DISPUTED = "disputed"


DATA_PROVENANCE_DEFINITIONS: dict[str, str] = {
    DataProvenance.MEASURED_TELEMETRY.value: (
        "Sampled directly from an instrument, meter or sensor and delivered "
        "through a monitored data path."
    ),
    DataProvenance.NAMEPLATE.value: (
        "Transcribed from equipment nameplate ratings supplied by the "
        "manufacturer."
    ),
    DataProvenance.ENGINEERING_STUDY.value: (
        "Produced by a prior engineering study, load flow, short-circuit or "
        "coordination analysis performed by a qualified engineer."
    ),
    DataProvenance.VENDOR_DOCUMENT.value: (
        "Extracted from a vendor datasheet, test report or technical manual."
    ),
    DataProvenance.MANUAL_ENTRY.value: (
        "Entered by hand by a person; subject to transcription error until "
        "independently corroborated."
    ),
    DataProvenance.INFERRED.value: (
        "Derived by calculation or estimation from other values rather than "
        "measured directly."
    ),
    DataProvenance.SYNTHETIC.value: (
        "Fabricated for demonstration, testing or modelling. Carries no claim "
        "about any real installation and must never drive a real decision."
    ),
}

VALIDATION_STATE_DEFINITIONS: dict[str, str] = {
    ValidationState.UNVALIDATED.value: (
        "No human has confirmed the value; treat as provisional."
    ),
    ValidationState.ENGINEER_REVIEWED.value: (
        "An engineer has reviewed the value for plausibility but has not "
        "verified it against the field installation."
    ),
    ValidationState.FIELD_VERIFIED.value: (
        "The value has been checked against the physical installation in the "
        "field."
    ),
    ValidationState.VALIDATED.value: (
        "A licensed engineer has formally validated the value as fit for its "
        "intended engineering use."
    ),
    ValidationState.DISPUTED.value: (
        "The value is contested; conflicting evidence exists and it must not be "
        "relied upon until resolved."
    ),
}


def provenance_vocabulary() -> dict[str, dict[str, str]]:
    """Return the provenance and validation vocabularies with definitions."""

    return {
        "data_provenance": dict(DATA_PROVENANCE_DEFINITIONS),
        "validation_state": dict(VALIDATION_STATE_DEFINITIONS),
    }
