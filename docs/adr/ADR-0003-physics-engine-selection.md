# ADR-0003: Physics engine selection

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0 (decision recorded; engines integrated in later work packages)

## Context

Per ADR-0002, all physical quantities must come from validated numerical
methods. We need to choose the open-source engines the platform will rely on for
each analysis class, with licences compatible with a commercial product and with
enough standing in the field to be defensible.

## Decision

We select the following open-source engines, by analysis class:

- **Balanced load flow, IEC 60909 short circuit, and N-1 contingency** —
  **pandapower** (BSD-3-Clause). A mature, well-documented power-system analysis
  library suitable for balanced three-phase networks and standardised
  short-circuit calculation.
- **Unbalanced load flow and harmonics** — **OpenDSS** via **dss-python**
  (BSD-3-Clause). Distribution-system analysis with native unbalanced and
  harmonic capability.
- **Dispatch and storage economics** — **PyPSA** (MIT). Energy-system
  optimisation for dispatch, storage sizing and economic studies.

All three licences are permissive and compatible with a commercial deliverable.

## The gap (stated explicitly)

**There is no credible open-source protection-coordination engine.** Protection
settings — relay curves, pickup and time-dial settings, fuse selection,
breaker interrupting duties as applied to a coordination study — cannot be
computed by any open-source tool we would stake a safety claim on.

Consequently:

- Protection settings are modelled **as data** in the canonical model
  (nameplate/rated values, provenance-labelled), never as a computed result.
- **Time-current-curve (TCC) coordination and selectivity remain a
  licensed-engineer deliverable.** The platform may display and organise
  protection data, but it must not assert coordination, selectivity, or
  arc-flash results. The grounding gate enforces this as a `FORBIDDEN_ASSERTION`
  (ADR-0007).

## Consequences

- Each analysis class has a defensible, permissively-licensed engine.
- The protection gap is explicit and enforced in code, not left to convention.
  No card may claim a coordination or arc-flash outcome.
- Engine selection can evolve; the packet/card contract (ADR-0006) insulates the
  rest of the platform from the choice of any particular engine.
