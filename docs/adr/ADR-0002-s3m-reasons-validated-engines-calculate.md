# ADR-0002: S3M reasons; validated engines calculate

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

The platform combines a reasoning layer (the S3M "brain") with quantitative
electrical engineering. There is a strong temptation to let a single, flexible
reasoning component both *decide what matters* and *compute the numbers*. For a
safety-relevant electrical domain that is unacceptable: physical quantities
(load flow, short-circuit duties, thermal limits) must come from auditable,
validated numerical methods, not from a language model's free-form generation.

## Decision

We separate the two responsibilities explicitly:

- **S3M reasons.** It selects the engine, assembles evidence, ranks causes,
  frames questions, weighs alternatives and produces operator-facing narrative.
- **Validated engines calculate.** All physical quantities are produced by
  established numerical methods (see ADR-0003) whose results are traceable to
  their inputs and to the standard or model they implement.

A number that appears on a recommendation card must resolve to a value that a
validated engine (or measured evidence) placed in the packet. The grounding gate
(ADR-0007) enforces this: an invented number is a `NUMERIC_PROVENANCE`
violation.

## Consequences

- The reasoning layer never fabricates quantities. Its job is to explain and
  prioritise numbers computed elsewhere, and to say so with citations.
- Engine outputs and reasoning outputs are separately auditable. The audit chain
  records which engine produced a card and the fingerprint of the invocation.
- WP0 contains no engine calculations and no language-model calls; it pins the
  *contract* (packet in, grounded card out) so later work packages can slot in
  validated engines without changing the safety envelope.
