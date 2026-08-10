# Energy-balance residual (design intent for a later work package)

> **Status: design intent only.** No energy-balance residual is computed in
> WP0. This document records the intended design so the canonical model and the
> engine contract are shaped to support it later. Nothing here is implemented
> yet, and nothing here is an engineering claim.

## Idea

For any metered boundary in the network, compare the **parent meter** against
the **sum of its children plus modelled losses**:

```
residual = P_parent - ( sum(P_children) + P_losses_modelled )
```

Ideally the residual is zero. In practice it is not, and *the way it deviates*
is informative. A persistent, well-characterised residual is a signal; a
suddenly-changing residual is a different signal.

## Why one residual is four signals

The same quantity, interpreted against context, is simultaneously:

1. **A data-quality signal.** Missing, stale, or mis-scaled meter data inflates
   or destabilises the residual. Before trusting any downstream analysis, the
   residual flags where the measurement set is incoherent.
2. **An unmetered-load detector.** A stable positive residual (parent exceeds
   the metered children plus losses) suggests real load that is not being
   metered — a tap, an unmodelled feeder, an unaccounted circuit.
3. **A meter-drift detector.** A slowly growing residual, with topology and load
   otherwise unchanged, is consistent with a meter losing calibration over time.
4. **A cyber-physical consistency check.** A residual that moves in ways the
   physical model cannot explain — inconsistent with known switching, load, and
   losses — is a consistency-of-telemetry check: the reported numbers disagree
   with physics.

## Preconditions

The residual is **only meaningful given a validated topology.** You must know
which children belong to which parent, which switches are closed, and what the
modelled losses are, before the residual can be attributed to any of the four
causes above. Without that, the residual is just noise. This is why the design
depends on ADR-0004 (canonical asset graph and energization state) and ADR-0005
(provenance and validation labelling): the residual is trustworthy only to the
extent its inputs are.

## Interaction with the safety posture

The residual is a diagnostic, never a control input. Any action it motivates is
an advisory recommendation to a human (ADR-0001), and any number it surfaces is
subject to the grounding gate's numeric-provenance rule (ADR-0007).
