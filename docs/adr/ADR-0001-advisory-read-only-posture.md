# ADR-0001: Advisory, read-only posture

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

S3M ElectricalTwin builds a digital twin of facility electrical infrastructure
and produces engineering insight for the people who operate that infrastructure.
Electrical systems are safety-critical: an incorrect or unauthorised write to a
breaker, drive, relay, PLC or field device can injure people and destroy
equipment. Automated control of such systems is a separately regulated activity
with its own certification, governance and liability regime.

We must decide, at the foundation of the platform, whether the twin is permitted
to act on the systems it observes.

## Decision

S3M ElectricalTwin is **advisory and read-only**. It observes and analyses; it
never writes to, commands, or actuates any control system, PLC, breaker, drive,
relay, or field device. Every recommendation it produces is directed at a human
operator and requires human approval.

This is a **hard platform invariant**, not a configuration option:

- `CONTROL_WRITE_ENABLED` is a module-level constant, permanently `False`, in
  `packages/canonical_electrical_model/safety.py`, with `assert_read_only()`
  to fail loudly if it were ever made truthy.
- A CI job (`scripts/check_safety_invariant.sh`) scans the repository for any
  control-write or actuation code path and fails the build on a hit.
- The canonical models carry no setpoint, command, or write-target field; a
  structural test enforces this, and `ControlBoundary` encodes the boundary
  explicitly.
- The API service is entirely read-only (`GET` endpoints only) and asserts the
  invariant at startup, failing closed.

## Consequences

- The platform cannot, by construction, take a control action. A future control
  tier, if one were ever built, would be a separately authorised and
  safety-certified product with its own lifecycle; it would never be this
  product and would never live behind a flag in this repository.
- Recommendations must always be phrased to a human operator. The grounding gate
  rejects imperative control language directed at equipment (ADR-0007).
- Some analyses that would be trivial with actuation (e.g. confirmation by test
  operation) are out of scope; they remain licensed-engineer activities.
