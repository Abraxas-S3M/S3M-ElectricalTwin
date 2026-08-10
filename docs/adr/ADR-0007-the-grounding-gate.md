# ADR-0007: The Grounding Gate

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

A reasoning engine can produce fluent, confident, and wrong output. Between the
engine and the operator we need a deterministic checkpoint that refuses to pass
anything that is not grounded in the evidence the engine was given, that
oversteps the platform's authority, or that speaks to equipment instead of to a
person.

## Decision

We introduce a **deterministic grounding gate**
(`packages/s3m_engine_contract/grounding.py`). It contains **no language model**;
it is a pure, rule-based audit of a `RecommendationCard` against its
`ElectricalTwinPacket`. Each check emits a named violation:

- `EVIDENCE_RESOLUTION` — every referenced evidence id exists in the packet's
  evidence pool.
- `UNCITED_CLAIM` — no numeric/categorical/causal claim lacks evidence.
- `NUMERIC_PROVENANCE` — every numeric value a card asserts resolves to a value
  in the packet within tolerance; an invented number is a violation.
- `ALTERNATIVES_REQUIRED` — a card with a causal claim carries at least two
  ranked alternatives and at least one item of refuting evidence considered.
- `FORBIDDEN_ASSERTION` — the card does not assert calibration, validation, code
  compliance, protection coordination, selectivity or arc-flash results.
- `CONTROL_LANGUAGE` — no imperative control language directed at equipment;
  recommendations phrased to a human operator are permitted.
- `SUFFICIENCY_FLOOR` — below the configured data-sufficiency floor the card must
  be `INSUFFICIENT_DATA`.
- `SYNTHETIC_LABEL` — an entirely-synthetic packet forces a preliminary,
  demonstration-marked card.

`verify_grounding(card, packet)` returns a `GroundingReport`.
`enforce(card, packet)` applies it: it strips violating claims, downgrades a
structurally unsound card to `INSUFFICIENT_DATA`, and attaches the report. It
**never silently passes a violation**.

## Consequences

- Grounding is deterministic and testable; the same card and packet always
  yield the same report.
- The gate is defence-in-depth: even if a future engine misbehaves, an ungrounded
  or over-reaching card cannot reach the operator unmodified.
- The gate encodes the platform's authority limits (no calibration/validation/
  coordination claims, no equipment commands) in one enforceable place.
