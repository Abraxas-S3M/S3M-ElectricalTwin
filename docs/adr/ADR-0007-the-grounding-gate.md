# ADR-0007: The Grounding Gate

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

A reasoning engine, however good, can hallucinate: invent numbers, cite evidence
that does not exist, assert causes without alternatives, or drift into control
language or forbidden engineering assertions. We cannot rely on the engine to
police itself, and we cannot show an operator an ungrounded card.

## Decision

A deterministic **Grounding Gate** sits between the reasoning engine and the
operator (`packages/s3m_engine_contract/grounding.py`). It contains **no language
model**. `verify_grounding(card, packet)` runs eight named checks, each producing
a named violation:

- `EVIDENCE_RESOLUTION` — every referenced evidence id exists in the packet.
- `UNCITED_CLAIM` — no numeric/categorical/causal claim lacks evidence.
- `NUMERIC_PROVENANCE` — every numeric value resolves to a packet value within
  tolerance; an invented number is a violation.
- `ALTERNATIVES_REQUIRED` — a causal claim carries ≥2 ranked alternatives and ≥1
  item of refuting evidence considered.
- `FORBIDDEN_ASSERTION` — no calibration, validation, code-compliance,
  protection-coordination, selectivity or arc-flash result is asserted.
- `CONTROL_LANGUAGE` — no imperative control language directed at equipment;
  human-directed recommendations are permitted.
- `SUFFICIENCY_FLOOR` — below the configured data-sufficiency floor the card must
  be `INSUFFICIENT_DATA`.
- `SYNTHETIC_LABEL` — synthetic cards must be `PRELIMINARY` with a demonstration
  marker.

`enforce(card, packet)` strips violating claims, downgrades structurally
defective cards to `INSUFFICIENT_DATA`, corrects synthetic labelling, and
attaches the report. It **never silently passes a violation.**

## Consequences

- The gate is deterministic and independently testable; its behaviour does not
  depend on the reasoning engine.
- Enforcement is conservative: when in doubt the card degrades toward honesty
  (`INSUFFICIENT_DATA`) rather than toward a confident but ungrounded finding.
- The control-language check is heuristic and deliberately conservative; it
  errs toward flagging rather than passing ambiguous equipment-directed text.
