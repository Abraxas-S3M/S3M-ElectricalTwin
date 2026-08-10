"""Tests for the determinism and reproducibility guards."""

from __future__ import annotations

import pytest

from packages.s3m_engine_contract.determinism import (
    assert_deterministic_config,
    invocation_fingerprint,
)


def _valid_config(**overrides) -> dict:
    base = {
        "temperature": 0,
        "top_p": 1,
        "model_version": "reasoner-2026.01",
        "prompt_template_version": "grounded-advisory-v1",
    }
    base.update(overrides)
    return base


def test_deterministic_config_accepts_pinned_zero_temperature() -> None:
    # Returns None (raises on any violation); reaching the next line is success.
    assert_deterministic_config(_valid_config())


def test_temperature_0_7_raises() -> None:
    with pytest.raises(ValueError):
        assert_deterministic_config(_valid_config(temperature=0.7))


def test_top_p_other_than_one_raises() -> None:
    with pytest.raises(ValueError):
        assert_deterministic_config(_valid_config(top_p=0.9))


def test_empty_model_version_raises() -> None:
    with pytest.raises(ValueError):
        assert_deterministic_config(_valid_config(model_version=""))


def test_missing_prompt_template_version_raises() -> None:
    config = _valid_config()
    del config["prompt_template_version"]
    with pytest.raises(ValueError):
        assert_deterministic_config(config)


def test_fingerprint_is_stable_for_identical_inputs() -> None:
    a = invocation_fingerprint("h" * 64, "tmpl-1", "model-1", "REASONING")
    b = invocation_fingerprint("h" * 64, "tmpl-1", "model-1", "REASONING")
    assert a == b
    assert len(a) == 64


def test_fingerprint_changes_with_any_input() -> None:
    base = invocation_fingerprint("h" * 64, "tmpl-1", "model-1", "REASONING")
    assert base != invocation_fingerprint("g" * 64, "tmpl-1", "model-1", "REASONING")
    assert base != invocation_fingerprint("h" * 64, "tmpl-2", "model-1", "REASONING")
    assert base != invocation_fingerprint("h" * 64, "tmpl-1", "model-2", "REASONING")
    assert base != invocation_fingerprint("h" * 64, "tmpl-1", "model-1", "PLANNING")
