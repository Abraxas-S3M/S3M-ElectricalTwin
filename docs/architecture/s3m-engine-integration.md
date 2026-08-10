# S3M engine integration: packet in, card out

This document describes how the S3M reasoning brain integrates with the rest of
the platform through the engine contract in `packages/s3m_engine_contract`.

> **WP0 contains no LLM invocation.** Work Package 0 pins the *contract* — the
> packet an engine consumes, the deterministic routing, the card it emits, and
> the grounding/determinism/refusal/audit machinery around them. No language
> model is called anywhere in WP0. Later work packages slot a reasoning engine
> into this contract without changing the safety envelope.

## The flow

```
                +------------------+
   telemetry -> |                  |
   topology  -> |  packet builder  | ---> ElectricalTwinPacket
   evidence  -> |                  |         (closed world)
                +------------------+
                          |
                          v
                 route(packet_class, urgency)      # pure, total, deterministic
                          |
                          v
                +------------------+
                |  reasoning engine|   (WP0: no LLM; later: pinned, temp=0)
                +------------------+
                          |
                          v
                   RecommendationCard  (draft, operator-facing)
                          |
                          v
                 verify_grounding(card, packet)    # deterministic gate, no LLM
                          |
                   +------+------+
                   |             |
              passed         violations
                   |             |
                   v             v
              enforce(...)   enforce(...) -> strip claims / downgrade to
                   |             INSUFFICIENT_DATA, attach GroundingReport
                   v
             audit chain append (fingerprint, output hash, grounding result)
                   |
                   v
             operator review  (human approval required; advisory only)
```

## The packet (in)

An `ElectricalTwinPacket` is a self-contained, closed-world bundle of everything
an engine is permitted to see for one unit of work:

- `readings`, `topology_snapshot`
- `evidence_pool` — the **only** set of facts an engine may cite
- `provenance_summary` and `data_sufficiency`
- a `control_boundary` asserting the advisory, read-only posture
- a `packet_hash` (sha256 over canonical content, excluding the hash field)

## The card (out)

A `RecommendationCard` is a grounded, operator-facing artefact. Every
numeric/categorical/causal claim cites evidence from the packet; the card model
itself rejects an uncited checkable claim at construction, and the grounding gate
(ADR-0007) audits the rest.

## Worked synthetic example

Synthetic packet (abbreviated): one node `n1`, one evidence item
`ev-1 = "Voltage at n1 is 11.0 kV"` with `value = 11.0`, entirely synthetic
provenance, healthy data sufficiency.

Draft card:

- claim `c1` (NUMERIC): "Voltage at n1 is 11.0 kV", `evidence_ids = ["ev-1"]`,
  `numeric_value = 11.0`
- `validation_state = PRELIMINARY`, `is_demonstration = True`
- no recommended equipment action; any recommendation is phrased to a human

`verify_grounding(card, packet)` returns `passed = True`:

- `EVIDENCE_RESOLUTION` — `ev-1` exists in the pool.
- `UNCITED_CLAIM` — the numeric claim cites `ev-1`.
- `NUMERIC_PROVENANCE` — `11.0` matches the packet within tolerance.
- `SYNTHETIC_LABEL` — the card is preliminary and demonstration-marked.

Now suppose the engine instead asserted "Current at n1 is 200 A" with no
supporting evidence and a value absent from the packet. The gate emits
`UNCITED_CLAIM` and `NUMERIC_PROVENANCE`; `enforce` strips that claim and
attaches the report. Nothing ungrounded reaches the operator.
