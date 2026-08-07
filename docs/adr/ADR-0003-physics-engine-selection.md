# ADR-0003: Physics engine selection

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

The platform delegates all numerical electrical calculation to validated
solvers (ADR-0002). We need to choose engines that are open-source under
permissive licences, well established, and appropriate to each analysis class.
We must also be honest about where no adequate open-source engine exists.

## Decision

The selected engines, by analysis class, are:

| Analysis | Engine | Licence |
| --- | --- | --- |
| Balanced load flow, IEC 60909 short circuit, N-1 contingency | **pandapower** | BSD-3-Clause |
| Unbalanced power flow and harmonics | **OpenDSS** via **dss-python** | BSD-3-Clause |
| Dispatch and storage economics | **PyPSA** | MIT |

All three are permissively licensed (BSD-3 / MIT), which is compatible with the
platform's distribution model.

## The gap (stated explicitly)

**There is no credible open-source protection-coordination engine.** As a
consequence:

- Protection settings are modelled as **data**, not computed by the platform.
- Time–current-curve (TCC) coordination, selectivity and grading remain a
  **licensed-engineer deliverable**. The platform will not compute, assert or
  validate coordination or selectivity results.
- The grounding gate's `FORBIDDEN_ASSERTION` check actively blocks any card that
  asserts a protection-coordination, selectivity, calibration, validation,
  code-compliance or arc-flash result.

## Consequences

- Users needing coordination studies must obtain them from a licensed engineer;
  the platform can carry those studies as evidence but not originate them.
- Engine choices are revisited if a credible, permissively licensed protection
  engine emerges; that would require a superseding ADR.
- Physics engines are not implemented in WP0; this ADR fixes the selection and
  the boundary so later work packages integrate against a settled decision.
