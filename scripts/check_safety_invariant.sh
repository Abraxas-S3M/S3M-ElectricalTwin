#!/usr/bin/env bash
#
# check_safety_invariant.sh
#
# Enforces the hard platform invariant of S3M ElectricalTwin: the product is
# advisory and read-only, so no code path may enable a control-write flag or
# call a control-write / actuation operation.
#
# The scan reports a violation for:
#   * enabling the safety flag, i.e. any of
#       "CONTROL_WRITE_ENABLED = True", "control_write_enabled=True",
#       "control_write_enabled = True"
#   * calling a control-write / actuation operation, i.e. any of the tokens
#       write_register, write_coil, write_value, writeAttribute,
#       setpoint_write, send_command, actuate
#     used as a call.
#
# Test files are excluded (paths matching */tests/* and test_*.py): tests must
# be able to assert that enabling the flag RAISES and that these tokens are
# absent from the source. This script is also excluded from the scan, since it
# necessarily contains the very patterns it searches for.
#
# On any hit outside those exclusions the script prints a report and exits
# non-zero. Otherwise it prints "SAFETY INVARIANT: OK" and exits 0.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

EXCLUDES=(
  --exclude-dir=.git
  --exclude-dir=__pycache__
  --exclude-dir=.mypy_cache
  --exclude-dir=.pytest_cache
  --exclude-dir=.ruff_cache
  --exclude-dir=.venv
  --exclude-dir=venv
  --exclude-dir=build
  --exclude-dir=dist
  --exclude-dir=node_modules
  --exclude-dir=htmlcov
  --exclude-dir=tests
  --exclude="test_*.py"
  --exclude="check_safety_invariant.sh"
)

# Enabling the control-write safety flag (any spacing, either case of the name).
ENABLE_RE='(CONTROL_WRITE_ENABLED|control_write_enabled)[[:space:]]*=[[:space:]]*True'

# Control-write / actuation operations, matched where they are used as calls so
# that documentation forbidding them (prose, without a call) is not flagged.
OP_RE='(write_register|write_coil|write_value|writeAttribute|setpoint_write|send_command|actuate)[[:space:]]*\('

enable_hits="$(grep -rnIE "${EXCLUDES[@]}" "$ENABLE_RE" . 2>/dev/null || true)"
op_hits="$(grep -rnIE "${EXCLUDES[@]}" "$OP_RE" . 2>/dev/null || true)"

hits="$(printf '%s\n%s' "$enable_hits" "$op_hits" | sed '/^$/d')"

if [ -n "$hits" ]; then
  echo "SAFETY INVARIANT: FAILED" >&2
  echo "Forbidden control-write / actuation usage detected:" >&2
  printf '%s\n' "$hits" >&2
  exit 1
fi

echo "SAFETY INVARIANT: OK"
exit 0
