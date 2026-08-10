# ADR-0006: S3M as the reasoning brain, not the calculator

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

ADR-0002 separates reasoning from calculation. This ADR records how the
reasoning brain is wired into the platform: what it consumes, what it emits, and
how it is prevented from becoming a calculator or an actuator.

## Decision

The S3M brain speaks through a single, explicit contract
(`packages/s3m_engine_contract`):

- **Packet in.** An `ElectricalTwinPacket` is a closed-world bundle of
  everything an engine is permitted to see for one unit of work: readings,
  topology snapshot, an `evidence_pool`, provenance and data-sufficiency
  summaries, and a control boundary. The `evidence_pool` is the *only* set of
  facts an engine may cite.
- **Deterministic routing.** A packet is routed to exactly one engine class
  (`TACTICAL` / `REASONING` / `PLANNING` / `BILINGUAL`) by a pure, total
  function of `(PacketClass, Urgency)`. No heuristics, no randomness.
- **Card out.** The engine emits a `RecommendationCard`: a grounded,
  operator-facing artefact whose every checkable claim cites evidence from the
  packet.

The brain never computes physical quantities (ADR-0002) and never actuates
(ADR-0001). In WP0 there is **no language-model invocation at all**; the contract
is pinned so later work packages can add reasoning without changing the safety
envelope.

## Consequences

- Reasoning is bounded by the packet: an engine cannot cite facts that were not
  supplied to it, which makes grounding checkable (ADR-0007).
- Routing is auditable and reproducible (ADR-0008).
- When the packet cannot support a recommendation, the brain returns an explicit
  `INSUFFICIENT_DATA` refusal card rather than improvising.
