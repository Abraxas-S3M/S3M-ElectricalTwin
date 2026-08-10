# S3M ElectricalTwin

S3M ElectricalTwin is an **advisory, read-only AI digital twin** for facility
electrical infrastructure. It builds a canonical model of the electrical
system, reasons over synthetic telemetry and asset data, and surfaces
observations, analyses and preliminary insights to human engineers.

## Advisory, read-only posture

**This product only observes and analyses. It never controls.**

There is no control-write path anywhere in this repository, and there never
will be in this product. No code path may write to, command or actuate any
control system, PLC, breaker, drive, relay or field device. This is a hard
platform invariant encoded in
[`packages/canonical_electrical_model/safety.py`](packages/canonical_electrical_model/safety.py)
(where the control-write flag is permanently disabled) and enforced in CI by
[`scripts/check_safety_invariant.sh`](scripts/check_safety_invariant.sh).

A control tier, were one ever to exist, would be a **separately authorised and
safety-certified product** with its own governance, review and certification
lifecycle — never this one.

## Canonical layout

```
packages/canonical_electrical_model/   # canonical, vendor-neutral electrical model + safety invariant
packages/electrical_engineering/       # electrical engineering constants, ranges and topology
packages/s3m_engine_contract/          # S3M reasoning-engine contract
packages/tests/                        # tests for the packages above
services/electricaltwin-api/app/       # advisory read-only API service
services/electricaltwin-api/tests/     # tests for the API service
docs/adr/                              # architecture decision records
docs/architecture/                     # architecture notes
docs/asset-model/                      # asset-model documentation
docs/security/                         # security documentation
scripts/                               # tooling, incl. the safety-invariant check
.github/workflows/                     # continuous integration
```

Tests live in `packages/tests/` and `services/electricaltwin-api/tests/` only;
there is intentionally no top-level `tests/` directory.

## Running the tests

Requires Python 3.11. From the repository root:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```

Other checks mirrored in CI:

```bash
ruff check .                                   # lint
mypy packages services                         # type-check
python -m compileall -q packages services scripts   # compile
bash scripts/check_safety_invariant.sh         # safety invariant
```

## Data and analytics

All bundled data is **synthetic**. Nothing in this repository represents a real
facility, asset, measurement or party, and no secrets are committed. All
analytics produced by the twin are **preliminary** and advisory, intended to
support — never replace — the judgement of a qualified human engineer.

## Continuous integration and merging

CI runs five blocking checks on every pull request: **lint**, **typecheck**,
**test**, **safety-invariant** and **compile**. Once all five checks pass, the
pull request is **squash-merged automatically** by CI (squash only, so a merge
commit is never produced).
