# Energy-balance residual (design intent for a later work package)

> **Status: design intent.** This capability is **not** implemented in Work
> Package 0. This document records the intent so later work is built against a
> considered design rather than an ad-hoc one.

## The residual

For any metered boundary in the network, define the energy-balance residual over
an interval as:

```
residual = E_parent_meter − ( Σ E_children + E_modelled_losses )
```

where `E_parent_meter` is the energy measured at the parent (upstream) meter,
`Σ E_children` is the sum of energy measured at the child (downstream) meters,
and `E_modelled_losses` is the losses predicted by the validated topology and
physics engines (ADR-0003) for that interval.

In a perfectly metered, perfectly modelled, physically consistent system the
residual is zero (within measurement uncertainty). A persistent non-zero
residual is information.

## One residual, four interpretations

The same residual signal is simultaneously:

1. **A data-quality signal.** Meter gaps, clock skew, unit errors or bad scaling
   inflate the residual without any physical cause.
2. **An unmetered-load detector.** A load tapped downstream of the parent but not
   represented by a child meter shows up as a persistent positive residual.
3. **A meter-drift detector.** A gradually miscalibrating meter (parent or child)
   produces a slowly trending residual even when topology and load are stable.
4. **A cyber-physical consistency check.** If reported meter values are being
   manipulated, or telemetry no longer matches physical reality, the residual
   diverges from its expected band — a signal that the physical and the reported
   world disagree.

Distinguishing these interpretations is itself a reasoning task and a natural fit
for the S3M reasoner: the residual is evidence, and competing explanations are
ranked alternatives with refuting evidence.

## Why it is only meaningful given a validated topology

Every term except the meters depends on the model. `E_modelled_losses` is only
trustworthy if the topology, ratings and connectivity are correct (ADR-0004), and
the parent/child meter assignment is only correct if the topology says which
meters bound which region. Over an **unvalidated** topology the residual conflates
model error with the four signals above and cannot be attributed. Therefore this
capability is gated on a validated topology and is deferred to a later work
package, after topology validation exists.
