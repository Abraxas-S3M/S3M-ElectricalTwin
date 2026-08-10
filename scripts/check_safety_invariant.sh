#!/usr/bin/env bash
#
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
