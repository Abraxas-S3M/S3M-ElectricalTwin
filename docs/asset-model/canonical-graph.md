# The canonical electrical asset graph

This document describes the canonical asset graph defined in
`packages/canonical_electrical_model/assets.py`. It is the shared model every
packet, engine and card reasons over (ADR-0004).

## Nodes: assets

An asset is a typed node with a stable `asset_id`. The `AssetType` vocabulary is:

| Type | Meaning |
| --- | --- |
| `source` | An upstream supply / grid connection point. |
| `busbar` | A common connection node at a voltage level. |
| `transformer` | A voltage-transforming element. |
| `circuit_breaker` | A switching device capable of interrupting fault current. |
| `disconnector` | An isolating switch (not for fault interruption). |
| `feeder` | A distribution feeder. |
| `line` | A conductor / cable segment. |
| `load` | A consuming element. |
| `generator` | A generating element. |
| `capacitor_bank` | A reactive-compensation element. |
| `meter` | A measurement point. |

Each asset carries an optional `nominal_voltage_kv` and an explicit
`EnergizationState`.

## Edges: connections

A `Connection` is a directed conductor from `from_asset_id` to `to_asset_id`.
The `AssetGraph` enforces referential integrity: connections may only reference
assets that exist, and asset ids must be unique. This guarantees that provenance
and grounding, which refer to assets by id, always resolve.

## Energization state

`EnergizationState` is one of:

- `energized` — carrying, or capable of carrying, energy.
- `de_energized` — confirmed not energized.
- `grounded` — de-energized and grounded.
- `unknown` — **the default.** Energization has not been evidenced.

`unknown` is a first-class value on purpose. The platform must never silently
assume a de-energization it cannot evidence; safe-by-default reasoning depends on
representing the absence of evidence rather than assuming a convenient state.

## What WP0 fixes and what it defers

Work Package 0 fixes the vocabulary, the graph invariants and energization
semantics. Electrical parameters required by the physics engines (impedances,
ratings, tap positions, protection settings modelled as data) are layered on in
later work packages, on top of this stable core.
