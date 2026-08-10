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
# check_safety_invariant.sh
#
# Enforces the hard platform invariant of S3M ElectricalTwin: the product is
# advisory and read-only, so no code path may enable a control-write flag or
# call a control-write / actuation operation.
#
# The scan looks for:
#   * enablement of the safety flag:
#       "CONTROL_WRITE_ENABLED = True"
#       "control_write_enabled=True"
#       "control_write_enabled = True"
#   * control-write / actuation operation tokens used as calls:
#       write_register, write_coil, write_value, writeAttribute,
#       setpoint_write, send_command, actuate
#
# Any hit outside a test that asserts these tokens are absent causes a
# non-zero exit. Otherwise the script prints "SAFETY INVARIANT: OK" and
# exits 0.
#
# This script is itself excluded from the scan: it necessarily contains the
# very tokens it searches for.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

COMMON_EXCLUDES=(
  --exclude-dir=.git
  --exclude-dir=__pycache__
  --exclude-dir=.mypy_cache
  --exclude-dir=.pytest_cache
  --exclude-dir=.ruff_cache
  --exclude-dir=.venv
  --exclude-dir=node_modules
  --exclude="check_safety_invariant.sh"
)

# Matches lines inside a test that asserts these tokens are ABSENT, which are
# explicitly permitted by the invariant.
TEST_PATH_RE='(^|/)(tests/|test_[^/]*$|conftest\.py$)'

# Pattern 1: the safety flag being switched on.
ENABLE_RE='(CONTROL_WRITE_ENABLED|control_write_enabled)[[:space:]]*=[[:space:]]*True'

# Pattern 2: control-write / actuation operations used as calls.
OP_RE='(write_register|write_coil|write_value|writeAttribute|setpoint_write|send_command|actuate)[[:space:]]*\('

hits=""

enable_hits="$(grep -rnIE "$ENABLE_RE" . "${COMMON_EXCLUDES[@]}" 2>/dev/null \
  | grep -vE "$TEST_PATH_RE" || true)"
op_hits="$(grep -rnIE "$OP_RE" . "${COMMON_EXCLUDES[@]}" 2>/dev/null \
  | grep -vE "$TEST_PATH_RE" || true)"

if [ -n "$enable_hits" ]; then
  hits+="$enable_hits"$'\n'
fi
if [ -n "$op_hits" ]; then
  hits+="$op_hits"$'\n'
fi

if [ -n "${hits//[$'\n']/}" ]; then
  echo "SAFETY INVARIANT: FAILED" >&2
  echo "Forbidden control-write / actuation usage detected:" >&2
  printf '%s\n' "$hits" | sed '/^$/d' >&2
  exit 1
fi

echo "SAFETY INVARIANT: OK"
exit 0
