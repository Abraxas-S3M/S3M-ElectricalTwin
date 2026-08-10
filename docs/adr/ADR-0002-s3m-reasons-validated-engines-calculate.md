# ADR-0002: S3M reasons, validated engines calculate

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

Two very different kinds of work are needed to produce a useful electrical
finding: numerical calculation (load flow, short circuit, contingency,
harmonics, dispatch) and judgement (which question to ask, which evidence
matters, how confident to be, what to recommend). Calculation must be exact and
reproducible; judgement must weigh incomplete and conflicting evidence. Conflating
the two — for example, asking a language model to compute a fault level — is both
inaccurate and unauditable.

## Decision

Responsibilities are split cleanly:

- **Validated engines calculate.** Numerical results come only from validated,
  established solvers (see ADR-0003). Their inputs and outputs are data.
- **S3M reasons.** The S3M reasoning engine frames the question, selects and
  weighs evidence, ranks hypotheses, quantifies confidence and composes the
  recommendation card. It never invents a numerical result.

The routing table (`packages/s3m_engine_contract/routing.py`) encodes which
packet class is calculated by which engine, and which classes are pure reasoning
tasks routed to the S3M reasoner.

## Consequences

- Any number that appears in a card must trace to an engine result carried in
  the packet; the grounding gate's `NUMERIC_PROVENANCE` check enforces this.
- The reasoning engine can be improved or replaced without touching the
  numerical guarantees, and vice versa.
- Work Package 0 contains no reasoning-engine (LLM) invocation; it fixes the
  contract and the guardrails only.
