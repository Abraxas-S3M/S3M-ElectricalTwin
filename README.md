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
