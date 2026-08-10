# S3M-ElectricalTwin

An **advisory, read-only** electrical reasoning platform. It observes, models and
reasons over electrical power-system data to produce grounded, evidence-cited
recommendations for qualified human operators and licensed engineers. It never
actuates equipment and exposes no control-write path.

This repository is **Work Package 0 (WP0)**: it fixes the contract, the
vocabularies and the guardrails. **WP0 contains no LLM invocation** and no
physics-engine implementation; it establishes the stable core that later work
packages build on.

## Layout

```
packages/
  canonical_electrical_model/   safety posture, provenance vocabulary, asset graph
  s3m_engine_contract/          packets, cards, routing, grounding gate,
                                determinism, refusal, audit chain
services/
  electricaltwin-api/           read-only FastAPI service (structured JSON logging)
scripts/
  check_safety_invariant.sh     fail-closed verification of the read-only posture
docs/
  adr/                          architecture decision records (ADR-0001 … ADR-0008)
  architecture/                 engine integration, energy-balance residual
  asset-model/                  the canonical asset graph
tests/                          the WP0 test suite
```

## Core ideas

- **Advisory and read-only** (ADR-0001). `CONTROL_WRITE_ENABLED` is a `Final`
  `False`; there is no path to enable actuation.
- **S3M reasons, validated engines calculate** (ADR-0002, ADR-0003, ADR-0006).
- **The Grounding Gate** (ADR-0007) deterministically verifies every card
  against its packet before an operator ever sees it, and never silently passes a
  violation.
- **Determinism and auditability** (ADR-0008).

## Running

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'

# Verification
ruff check .
mypy packages services
pytest -q
bash scripts/check_safety_invariant.sh

# The API (read-only)
uvicorn app.main:app --app-dir services/electricaltwin-api
```

## Known limitations

- **The audit chain is in-memory and WP0-only.** The append-only audit chain in
  `packages/s3m_engine_contract/audit.py` keeps the entire chain in process
  memory and loses it on restart. It exists to fix the record shape and the
  hash-chaining semantics. **It must be replaced by a durable, PostgreSQL-backed
  append-only audit service before any pilot deployment.**
- **No reasoning engine is wired in.** WP0 defines the packet-in / card-out
  contract and the grounding gate but performs no LLM invocation.
- **No physics engines are integrated.** Engine selection is settled (ADR-0003)
  but the solvers are integrated in later work packages.
- **No open-source protection-coordination engine exists.** Protection settings
  are modelled as data; time–current-curve coordination and selectivity remain a
  licensed-engineer deliverable (ADR-0003).

All data in this repository (examples, tests, documentation) is **synthetic** and
describes no real installation.
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
# S3M ElectricalTwin

S3M ElectricalTwin is an **advisory, read-only AI digital twin** for facility
electrical infrastructure. It builds a canonical model of electrical assets,
ingests synthetic operational and nameplate data, and produces engineering
analytics and advisory insight to help engineers understand the state and
behaviour of an electrical system.

## Read-only posture (please read first)

> **S3M ElectricalTwin is advisory and read-only. It never writes to,
> commands, or actuates any control system, PLC, breaker, drive, relay, or
> field device.**

This is a **hard platform invariant**, not a configuration choice. It is
encoded in code as `CONTROL_WRITE_ENABLED = False`
(see `packages/canonical_electrical_model/safety.py`) and enforced in
continuous integration by a dedicated `safety-invariant` job that scans the
repository for any control-write or actuation code path.

A control tier, if one were ever built, would be a **separately authorised and
safety-certified product** with its own governance and certification lifecycle.
It would never be this product.

## Data and analytics disclaimer

**All data bundled in this repository is synthetic.** No real facility,
operational, or customer data is present. **All analytics produced by this
project are preliminary** and are intended for advisory purposes only; they are
not a substitute for professional engineering judgement or certified analysis.

## Canonical layout

The repository follows a fixed, canonical layout. This is the only permitted
structure:

```
packages/canonical_electrical_model/   # canonical electrical asset model + safety invariant
packages/electrical_engineering/       # electrical engineering analytics (advisory)
packages/s3m_engine_contract/          # read-only engine contract types
packages/tests/                        # package-level tests
services/electricaltwin-api/app/       # advisory read-only API service
services/electricaltwin-api/tests/     # API service tests
docs/adr/                              # architecture decision records
docs/architecture/                     # architecture documentation
docs/asset-model/                      # asset-model documentation
docs/security/                         # security documentation
scripts/                              # developer and CI scripts
.github/workflows/                     # CI workflows
```

## Requirements

- Python 3.11

## Setup

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

`packages/` and `services/electricaltwin-api/` are placed on the import path
via `pyproject.toml`, so the packages and the API service can be imported
directly in tests and tooling.

## Running the checks

```bash
# Lint
ruff check .

# Type-check
mypy packages services

# Tests (with coverage)
pytest -q

# Hard read-only safety invariant
bash scripts/check_safety_invariant.sh

# Byte-compile everything
python -m compileall -q packages services scripts
```

These are the same five blocking checks run in CI: `lint`, `typecheck`,
`test`, `safety-invariant`, and `compile`.

## License

See [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) for the licenses of
third-party dependencies.
