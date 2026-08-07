#!/usr/bin/env bash
#
# check_safety_invariant.sh — fail-closed verification of the read-only posture.
#
# This script is the executable form of the platform's core safety promise: the
# platform is advisory and read-only and exposes no control-write path. It is
# safe to run in CI and locally. It exits non-zero the moment any invariant is
# violated.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "== S3M ElectricalTwin :: safety invariant check =="

# 1. No Python source may enable the control-write path.
echo "-- checking for control-write enable assignments --"
if grep -rn \
  --include='*.py' \
  -E 'control_write_enabled[[:space:]]*=[[:space:]]*True|CONTROL_WRITE_ENABLED[[:space:]]*=[[:space:]]*True' \
  packages services scripts ; then
  echo "SAFETY INVARIANT FAILED: a control-write enable assignment exists" >&2
  exit 1
fi
echo "   no control-write enable assignments found: OK"

# 2. The constant must resolve to False and the read-only assertion must hold.
echo "-- checking CONTROL_WRITE_ENABLED and assert_read_only() --"
PYTHONPATH="${REPO_ROOT}" "${PYTHON_BIN}" - <<'PY'
from packages.canonical_electrical_model.safety import (
    CONTROL_WRITE_ENABLED,
    assert_read_only,
    control_boundary,
)

assert CONTROL_WRITE_ENABLED is False, "CONTROL_WRITE_ENABLED must be False"
assert_read_only()

boundary = control_boundary()
assert boundary.control_write_enabled is False, "control boundary must be read-only"
assert boundary.posture == "advisory-read-only", "posture must be advisory-read-only"
print("   CONTROL_WRITE_ENABLED =", CONTROL_WRITE_ENABLED)
print("   assert_read_only(): OK")
print("   control boundary posture:", boundary.posture)
PY

# 3. The one-way-diode profile must fail closed against OT-outbound connections.
echo "-- checking one_way_diode fail-closed posture --"
PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/services/electricaltwin-api" "${PYTHON_BIN}" - <<'PY'
from app.config import (
    DeploymentProfile,
    Settings,
    UnsafeConfigurationError,
    assert_safe_startup,
)

# The supported, safe configuration must start.
safe = Settings(
    deployment_profile=DeploymentProfile.ONE_WAY_DIODE,
    log_level="INFO",
    service_name="electricaltwin-api",
)
assert_safe_startup(safe)

# A configuration that would allow OT-outbound connections must be rejected.
unsafe = Settings(
    deployment_profile=DeploymentProfile.ONE_WAY_DIODE,
    log_level="INFO",
    service_name="electricaltwin-api",
    ot_outbound_connections_allowed=True,
)
try:
    assert_safe_startup(unsafe)
except UnsafeConfigurationError:
    print("   one_way_diode rejects OT-outbound connections: OK")
else:
    raise SystemExit("SAFETY INVARIANT FAILED: one_way_diode did not fail closed")
PY

echo "== ALL SAFETY INVARIANTS HOLD: OK =="
