# S3M-ElectricalTwin

Canonical data models for an electrical digital twin.

## `packages/canonical_electrical_model`

Pydantic v2 models describing the **observed** and **rated** reality of an
electrical network. The package is **observe-only by design**: no model carries
a setpoint, command, write target, or control action, and `ControlBoundary`
encodes that invariant explicitly (it is a frozen assertion that control writes
are disabled and human approval is required).

Highlights:

- **Topology is a directed graph with live switching state**, not a tree. Edges
  are directed and carry an independent `switch_state` (`OPEN` / `CLOSED` /
  `INTERMEDIATE` / `UNKNOWN`), so tie breakers and backfeed paths can form
  genuine cycles.
- **Everything is provenance-labelled.** `RatedData` fields are individually
  wrapped in `Provenanced[T]`; nodes, edges, and readings carry a `Provenance`.
- **Facility frequency defaults to 60 Hz but is configurable** (adjacent 50 Hz
  markets are supported).
- **Analytic contracts** (`Evidence`, `HealthScore`, `AnomalyResult`,
  `PowerQualityEvent`, `RankedCause`, ...) are defined now and populated by
  later work packages.

## Development

```bash
pip install -e ".[test]"   # pydantic>=2, pytest
pytest -q
```
