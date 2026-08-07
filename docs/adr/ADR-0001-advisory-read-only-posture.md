# ADR-0001: Advisory, read-only posture

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

The platform reasons over electrical power systems. Systems that can actuate
primary or protection equipment carry safety-of-life risk and demand a wholly
different assurance regime (functional safety, independent verification,
regulatory approval) than an analytics and reasoning platform. We must decide,
at the architectural root, whether this platform is ever permitted to act on the
plant.

## Decision

The platform is **advisory and read-only**. It observes, models and reasons; it
never actuates equipment and it exposes no control-write path.

- The single source of truth is the constant `CONTROL_WRITE_ENABLED`, a `Final`
  fixed to `False` in `packages/canonical_electrical_model/safety.py`. There is
  no environment variable, feature flag or configuration key that can flip it.
- `assert_read_only()` is called at service startup and fails closed.
- `scripts/check_safety_invariant.sh` verifies the invariant in CI and locally,
  including scanning the source for any assignment that would enable a
  control-write path.
- Every output is a recommendation directed at a qualified human. The grounding
  gate (ADR-0007) rejects imperative control language directed at equipment.

## Consequences

- Enabling actuation is not a configuration change; it would require a separate,
  independently reviewed control system living outside this platform, and a new
  ADR superseding this one.
- Some latency-sensitive automation use cases are explicitly out of scope. This
  is accepted: the value of the platform is trustworthy reasoning, not speed of
  actuation.
- The read-only posture is testable and enforced at three layers (a constant, a
  startup assertion, and a CI script), so a regression cannot ship silently.
