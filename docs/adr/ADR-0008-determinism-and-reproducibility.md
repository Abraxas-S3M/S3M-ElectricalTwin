# ADR-0008: Determinism and reproducibility of reasoning

- Status: Accepted
- Date: 2026-08-10
- Work package: WP0

## Context

An advisory system that gives different answers to the same question is not
auditable and cannot be trusted in a safety-relevant setting. Reasoning must be
reproducible: the same inputs must always yield the same routing and the same
grounded card, and every invocation must be recorded tamper-evidently.

## Decision

Reasoning invocations are **deterministic, pinned, and audited**:

- **Deterministic configuration is mandatory.**
  `assert_deterministic_config` refuses any engine configuration unless
  `temperature == 0`, `top_p == 1`, and both `model_version` and
  `prompt_template_version` are non-empty pinned strings.
- **Every invocation has a fingerprint.** `invocation_fingerprint` derives a
  stable sha256 identifier from the packet hash, prompt-template version, model
  version and engine class. Identical inputs share a fingerprint; any change
  changes it.
- **Routing is a pure, total function** of `(PacketClass, Urgency)` (ADR-0006),
  so it is trivially reproducible.
- **Invocations are recorded in a tamper-evident audit chain**
  (`packages/s3m_engine_contract/audit.py`): each record commits to the previous
  record's hash, so any later edit or reordering breaks the chain and is
  detected by `verify_chain`.

## Consequences

- Any advisory output can be reproduced from its pinned inputs and checked
  against the recorded fingerprint and hash.
- Non-deterministic or unpinned configurations are rejected before they can
  produce an unreproducible result.
- **Limitation:** the WP0 audit chain is an in-memory implementation for pinning
  the contract and proving the semantics under test. It must be replaced by a
  durable, append-only, PostgreSQL-backed audit service before any pilot
  deployment (recorded as a known limitation in the README).
