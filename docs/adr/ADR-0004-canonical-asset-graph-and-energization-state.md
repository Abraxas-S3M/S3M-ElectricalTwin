# ADR-0004: Canonical electrical asset graph and energization state

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

Every analysis in the platform depends on a shared, unambiguous model of *what
is connected to what* and *what is currently live*. Real electrical networks are
not trees: tie breakers, dual feeds and backfeed paths create genuine cycles.
Switching state is frequently uncertain, and guessing it is dangerous.

## Decision

The canonical topology is a **directed graph with live switching state**:

- **Nodes** are addressable assets (`AssetType`): intakes, switchgear,
  transformers, boards, breakers, buses, loads, sources, meters, and so on.
- **Edges** are directed connections carrying an independent, *observed*
  `switch_state` (`OPEN` / `CLOSED` / `INTERMEDIATE` / `TRIPPED` / `RACKED_OUT`
  / `UNKNOWN`). There is no structural constraint forbidding cycles.
- **Sources** carry a type and a priority; energization semantics derive the
  reported state of downstream nodes.

Energization is a first-class, conservative computation (`EnergizationState`):

- A node reachable from a source over exclusively `CLOSED` edges is definitely
  energized (primary/backup/UPS depending on the source).
- **`UNKNOWN` switch state is never resolved by assumption.** A node reachable
  only by traversing an `UNKNOWN` switch is `INDETERMINATE` — never guessed in
  either direction.
- A node reachable in neither the closed-only nor the closed-or-unknown graph is
  `DE_ENERGIZED`.

## Consequences

- Cycles (tie breakers, ring buses, backfeed) are representable and terminate in
  traversal via a visited set.
- Uncertainty is preserved end-to-end: "we do not know" is a valid, common, and
  safe answer, consistent with the refusal path (ADR-0006) and the grounding
  gate's insufficiency floor (ADR-0007).
- Downstream-impact / N-1 analysis is a reusable primitive over this graph,
  partitioned by criticality.
