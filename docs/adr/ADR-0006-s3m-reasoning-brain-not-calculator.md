# ADR-0006: S3M as the reasoning brain, not the calculator

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

ADR-0002 split calculation from judgement. This ADR fixes the role of the S3M
engine specifically, so its interface can be built and tested before any model
is wired in.

## Decision

S3M is the **reasoning brain**. Its contract is packet-in / card-out:

- **Input:** an `EnginePacket` carrying an evidence pool, a provenance summary,
  an urgency level and routing context.
- **Output:** a single `RecommendationCard` whose every factual assertion is a
  cited claim, whose causal assertions carry ranked alternatives and refuting
  evidence, and whose confidence is decomposed into data-sufficiency,
  model-fidelity and corroboration.

S3M does not calculate physical quantities. When a packet needs a numerical
result, the routing table sends it to a validated engine (ADR-0003) and S3M
reasons over that engine's output, which arrives as evidence.

## Consequences

- The reasoning engine can be swapped or upgraded behind a stable contract.
- Because every numeric value must resolve to packet evidence, S3M cannot
  fabricate numbers; the grounding gate enforces this.
- WP0 implements the contract, the card/packet models and the guardrails, but
  **no LLM invocation**. The actual reasoning engine is a later work package.
