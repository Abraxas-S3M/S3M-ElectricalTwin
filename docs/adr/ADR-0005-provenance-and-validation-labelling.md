# ADR-0005: Provenance and validation labelling

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

Trust in a recommendation depends on knowing where its supporting data came
from and how much a human has vouched for it. These are two different questions
and conflating them hides risk: measured telemetry can be unvalidated, and a
manual estimate can be field-verified.

## Decision

Every value carries two orthogonal labels, defined in
`packages/canonical_electrical_model/provenance.py`:

- **`DataProvenance`** — where the value came from: `measured_telemetry`,
  `nameplate`, `engineering_study`, `vendor_document`, `manual_entry`,
  `inferred`, `synthetic`.
- **`ValidationState`** — how thoroughly a human has vouched for it:
  `unvalidated`, `engineer_reviewed`, `field_verified`, `validated`, `disputed`.

Each term has a single canonical definition, exposed verbatim through the API
(`GET /meta/provenance`) so operators, engineers and auditors share one
vocabulary. `synthetic` provenance is special: it carries no claim about any real
installation and triggers the grounding gate's `SYNTHETIC_LABEL` rule.

## Consequences

- Cards can be filtered and audited by provenance and validation independently.
- Synthetic (demonstration) data can never masquerade as a real finding: it is
  labelled at the vocabulary level and enforced at the grounding gate.
- The two-axis model is a small ongoing cost at data-ingest time, accepted in
  exchange for auditable trust.
