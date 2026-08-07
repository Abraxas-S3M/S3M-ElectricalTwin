"""The S3M engine contract: packets in, recommendation cards out.

This package defines the boundary between the S3M reasoning engine and the
operator. It contains:

* :mod:`~packages.s3m_engine_contract.cards` — the recommendation card, its
  claims, evidence and confidence model.
* :mod:`~packages.s3m_engine_contract.packets` — the input packet vocabulary,
  engine classes and urgency levels.
* :mod:`~packages.s3m_engine_contract.routing` — the packet-to-engine routing
  table.
* :mod:`~packages.s3m_engine_contract.grounding` — the deterministic grounding
  gate that sits between the engine and the operator.
* :mod:`~packages.s3m_engine_contract.determinism` — reproducibility guarantees.
* :mod:`~packages.s3m_engine_contract.refusal` — the insufficient-data card.
* :mod:`~packages.s3m_engine_contract.audit` — the append-only audit chain.

Work Package 0 contains **no LLM invocation**. It fixes the contract and the
guardrails only.
"""
