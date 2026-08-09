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
