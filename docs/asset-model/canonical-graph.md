# The canonical electrical asset graph

This document describes the shape of the canonical asset model implemented in
`packages/canonical_electrical_model`. See ADR-0004 for the decision rationale.

## A directed graph with live switching state

The electrical network is modelled as a **directed graph**, not a tree:

- **Nodes** (`ElectricalNode`) are addressable assets classified by `AssetType`
  (utility intake, main switchgear, transformer, distribution board, MCC,
  circuit breaker, switch-disconnector, busbar, cable, capacitor bank, harmonic
  filter, generator, ATS, UPS, battery string, motor, VFD, pump, chiller, HVAC
  unit, solar array, inverter, energy storage, production line, lighting panel,
  generic load, meter). Nodes carry a nominal voltage, phase count, criticality,
  optional rated/nameplate data, a location and a provenance label.
- **Edges** (`ElectricalEdge`) are directed connections (`from_node_id ->
  to_node_id`) classified by `EdgeKind` (feeder, tie, transformer winding,
  source connection). Each edge carries an independent, *observed*
  `switch_state`; there is no structural constraint forbidding cycles, so tie
  breakers and backfeed paths form genuine loops.
- **Sources** (`SourceNode`) attach a supply of a given `SourceType` (utility,
  generator, UPS, solar, storage) and a priority (lower is more preferred).

A `TopologySnapshot` captures the nodes, edges and sources of a facility at an
instant.

## Live switching state

`SwitchState` is an **observed** condition, never a command:

`OPEN`, `CLOSED`, `INTERMEDIATE`, `TRIPPED`, `RACKED_OUT`, `UNKNOWN`.

`UNKNOWN` is a first-class value. Topology must validate even when a switch's
state cannot be determined, and it must never be resolved by assumption.

## Energization semantics

`EnergizationState` is derived conservatively (see the solver in
`packages/electrical_engineering`):

- Reachable from a source over exclusively `CLOSED` edges -> definitely energized
  (`ENERGIZED_PRIMARY` / `ENERGIZED_BACKUP` / `ENERGIZED_UPS`).
- Reachable only by traversing an `UNKNOWN` switch -> `INDETERMINATE`. Never a
  guess in either direction.
- Reachable in neither graph -> `DE_ENERGIZED`.

## Read-only by construction

No node, edge, source, rating, reading or analytic model carries a setpoint,
command, or write target. The base model forbids extra fields, a structural test
enforces the absence of control-capable fields, and `ControlBoundary` encodes
the read-only invariant explicitly (ADR-0001). Every substantive value is
provenance- and validation-labelled (ADR-0005). All data in this repository is
synthetic.
