# ADR-0005: Provenance and validation labelling

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

Advisory value depends on trust, and trust depends on knowing *where a number
came from* and *how far it has been validated*. Mixing a nameplate value, a
simulated estimate and a live meter reading without labelling them is how an
advisory system quietly becomes misleading.

## Decision

Every substantive value is labelled along two independent axes:

- **Provenance** (`DataProvenance`): where the value originated — `SYNTHETIC`,
  `SIMULATED`, `OPERATOR_ENTERED`, `NAMEPLATE`, `CUSTOMER_HISTORIAN`,
  `CUSTOMER_METER`, `CUSTOMER_LIMS`, `THIRD_PARTY`. A helper distinguishes
  customer-sourced data from everything else.
- **Validation state** (`ValidationState`): how far a modelled quantity has been
  validated — from `NOT_VALIDATED` / `PRELIMINARY` through `VALIDATED`, plus the
  explicit `INSUFFICIENT_DATA` refusal state.

`CALIBRATED` is a **reserved terminal validation state**. It documents that a
model has been formally calibrated against measurements, but it **must never be
assigned by any code path in this repository** — calibration is an out-of-band,
operator-governed act. A static guard test scans the whole code base and fails
if any assignment references `ValidationState.CALIBRATED`.

The API exposes both vocabularies with plain-language definitions at
`/meta/provenance`.

## Consequences

- A card can always be traced to the provenance and validation state of the
  evidence behind it.
- Synthetic data is unmistakable: an entirely-synthetic packet forces a
  preliminary, demonstration-marked card (grounding gate `SYNTHETIC_LABEL`,
  ADR-0007).
- No component can silently claim calibration; achieving `CALIBRATED` requires a
  deliberate, governed process outside these code paths.
