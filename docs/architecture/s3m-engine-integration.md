# S3M engine integration: packet-in / card-out

> **Work Package 0 scope.** This document describes the contract and the data
> flow. WP0 **contains no LLM invocation.** The reasoning engine itself is a
> later work package; here we fix the shape of what goes in, what comes out and
> the gate in between.

## Overview

```
                 ┌──────────────────┐        ┌──────────────────┐
   EnginePacket  │  routing table   │        │  validated       │
  ─────────────► │  (packet class → │ ─────► │  physics engine  │ ──┐
   evidence pool │   engine class)  │        │  (ADR-0003)      │   │  engine
   provenance    └──────────────────┘        └──────────────────┘   │  results
   urgency                │                                          │  (as evidence)
                          │ reasoning packet classes                 ▼
                          ▼                                  ┌──────────────────┐
                 ┌──────────────────┐                        │  S3M reasoner    │
                 │  S3M reasoner    │ ◄──────────────────────│  composes a      │
                 │  (ADR-0006)      │                        │  RecommendationCard
                 └────────┬─────────┘                        └──────────────────┘
                          │ candidate card
                          ▼
                 ┌──────────────────┐        ┌──────────────────┐
                 │  Grounding Gate  │ ─────► │  audit chain     │
                 │  (ADR-0007)      │        │  (ADR-0008)      │
                 └────────┬─────────┘        └──────────────────┘
                          │ enforced card (never an ungrounded violation)
                          ▼
                     human operator
```

## The contract

- **In:** `EnginePacket` — `packet_id`, `packet_class`, `urgency`, an
  `evidence_pool` of `Evidence`, and a `provenance_summary`.
- **Out:** `RecommendationCard` — `health_band`, `status`, cited `claims`,
  human-directed `recommendations`, `alternatives`, `refuting_evidence_considered`,
  decomposed `confidence`, a `provenance_summary` and, once enforced, an attached
  `grounding_report`.

Everything the card asserts is a `Claim`. Numeric, categorical and causal claims
must cite evidence; causal claims additionally carry ranked alternatives and the
refuting evidence considered.

## Worked synthetic example

The packet below is **entirely synthetic** — it describes no real installation.

Packet:

```json
{
  "packet_id": "pkt-demo-0001",
  "packet_class": "asset_health",
  "urgency": "elevated",
  "evidence_pool": [
    {"evidence_id": "ev-top-oil-temp", "description": "Transformer TX-1 top-oil temperature", "value": 92.4, "unit": "degC", "provenance": "synthetic", "validation_state": "unvalidated"},
    {"evidence_id": "ev-load-pct", "description": "TX-1 loading", "value": 88.0, "unit": "percent", "provenance": "synthetic", "validation_state": "unvalidated"},
    {"evidence_id": "ev-ambient", "description": "Ambient temperature", "value": 34.0, "unit": "degC", "provenance": "synthetic", "validation_state": "unvalidated"}
  ],
  "provenance_summary": {"is_entirely_synthetic": true, "data_sufficiency": 0.62, "dominant_provenance": "synthetic", "dominant_validation_state": "unvalidated"}
}
```

Candidate card produced by the reasoner (before the gate):

```json
{
  "card_id": "card-demo-0001",
  "packet_id": "pkt-demo-0001",
  "health_band": "elevated_attention",
  "status": "preliminary",
  "headline": "TX-1 top-oil temperature is elevated relative to loading and ambient.",
  "claims": [
    {"claim_id": "cl-1", "claim_type": "numeric", "statement": "Top-oil temperature is 92.4 degC.", "evidence_ids": ["ev-top-oil-temp"], "numeric_value": 92.4, "numeric_unit": "degC"},
    {"claim_id": "cl-2", "claim_type": "causal", "statement": "The elevated top-oil temperature is most consistent with sustained high loading at high ambient.", "evidence_ids": ["ev-load-pct", "ev-ambient"]}
  ],
  "alternatives": [
    {"alternative_id": "alt-1", "description": "Sustained high loading at high ambient.", "rank": 1, "relative_likelihood": 0.6},
    {"alternative_id": "alt-2", "description": "Degraded cooling (fan/pump) reducing heat rejection.", "rank": 2, "relative_likelihood": 0.3}
  ],
  "refuting_evidence_considered": [
    {"evidence_id": "ev-ambient", "consideration": "Ambient is high but not extreme, so ambient alone does not fully explain the rise."}
  ],
  "recommendations": [
    {"recommendation_id": "rec-1", "text": "Recommend that the operator review TX-1 cooling-system status and recent loading history.", "audience": "human_operator"}
  ],
  "confidence": {"data_sufficiency": 0.62, "model_fidelity": 0.55, "corroboration": 0.5},
  "provenance_summary": {"is_entirely_synthetic": true, "data_sufficiency": 0.62, "dominant_provenance": "synthetic", "dominant_validation_state": "unvalidated"},
  "demonstration_marker": "DEMONSTRATION — synthetic data only; not a statement about any real installation."
}
```

The Grounding Gate then confirms: every evidence id resolves, no claim is
uncited, `92.4` resolves to `ev-top-oil-temp`, the causal claim carries two
ranked alternatives and one refuting item, no forbidden assertion or control
language is present, sufficiency `0.62` is above the floor, and the synthetic
card is `PRELIMINARY` with a demonstration marker. The card passes and an audit
record is appended.

Had the reasoner instead written "Open breaker BRK-12 to shed load" the
`CONTROL_LANGUAGE` check would have fired, and `enforce` would have downgraded
the card to `INSUFFICIENT_DATA` with the violation recorded — never silently
passed.
