# ADR-0008: Determinism and reproducibility of reasoning

- Status: Accepted
- Date: 2026-08-07
- Work Package: WP0

## Context

An advisory used in an engineering context must be auditable: given the same
inputs, the platform must be able to explain and reproduce the same output. A
reasoning engine run with sampling enabled, or with unpinned model or prompt
versions, cannot make that guarantee.

## Decision

Reasoning invocations must be provably deterministic
(`packages/s3m_engine_contract/determinism.py`):

- `assert_deterministic_config(config)` raises unless `temperature == 0`,
  `top_p == 1`, and both `model_version` and `prompt_template_version` are
  non-empty pinned strings.
- `invocation_fingerprint(packet_hash, prompt_template_version, model_version,
  engine_class)` produces a stable SHA-256 fingerprint tying an output to the
  exact inputs and versions that produced it.
- The audit chain (`audit.py`) records the fingerprint, the packet hash, the
  output hash and the grounding outcome for every invocation, hash-linked so
  tampering and reordering are detectable.

## Consequences

- Every reasoning result can be reproduced and independently re-verified.
- Model and prompt upgrades are explicit, versioned events, visible in the audit
  trail.
- The audit chain in WP0 is **in-memory only** and must be replaced by a durable
  PostgreSQL-backed service before any pilot (see `audit.py` and the README).
