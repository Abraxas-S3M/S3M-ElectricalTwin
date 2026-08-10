# ADR-0004: Canonical electrical asset graph and energization state

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

Every engine, every packet and every card must reason over the same model of
the electrical network. Without one canonical representation, provenance,
routing and grounding cannot be reconciled, and energization assumptions become
implicit and dangerous.

## Decision

We define a single canonical electrical asset graph in
`packages/canonical_electrical_model/assets.py`:

- Assets are typed nodes (`AssetType`: source, busbar, transformer, circuit
  breaker, disconnector, feeder, line, load, generator, capacitor bank, meter).
- Conductors are directed `Connection` edges; the graph enforces referential
  integrity (no dangling connections, no duplicate asset ids).
- Every asset carries an explicit `EnergizationState`:
  `ENERGIZED`, `DE_ENERGIZED`, `GROUNDED` or `UNKNOWN`.

`UNKNOWN` is a first-class state. The platform must never silently assume a
de-energization it cannot evidence.

## Consequences

- All packets and cards refer to assets by canonical id, so provenance and
  grounding compose cleanly.
- Because energization is explicit and defaults to `UNKNOWN`, safe-by-default
  reasoning is possible: absence of evidence is represented, not assumed away.
- The graph is intentionally minimal in WP0 (vocabulary and invariants only);
  electrical parameters consumed by the physics engines are layered on later.
