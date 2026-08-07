"""Tests for determinism and reproducibility guarantees."""

from __future__ import annotations

import pytest

from packages.s3m_engine_contract.determinism import (
    NonDeterministicConfigError,
    assert_deterministic_config,
    invocation_fingerprint,
)

VALID_CONFIG = {
    "temperature": 0,
    "top_p": 1,
    "model_version": "s3m-reasoner-2026.08.0",
    "prompt_template_version": "card-v1",
}


def test_valid_deterministic_config_passes():
    assert assert_deterministic_config(VALID_CONFIG) is None


def test_temperature_0_7_raises():
    config = {**VALID_CONFIG, "temperature": 0.7}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_missing_temperature_raises():
    config = {k: v for k, v in VALID_CONFIG.items() if k != "temperature"}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_top_p_not_one_raises():
    config = {**VALID_CONFIG, "top_p": 0.9}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_empty_model_version_raises():
    config = {**VALID_CONFIG, "model_version": ""}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_empty_prompt_template_version_raises():
    config = {**VALID_CONFIG, "prompt_template_version": "   "}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_boolean_temperature_rejected():
    config = {**VALID_CONFIG, "temperature": False}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_non_string_model_version_rejected():
    config = {**VALID_CONFIG, "model_version": 123}
    with pytest.raises(NonDeterministicConfigError):
        assert_deterministic_config(config)


def test_fingerprint_is_stable():
    a = invocation_fingerprint("ph", "pt", "mv", "s3m_reasoner")
    b = invocation_fingerprint("ph", "pt", "mv", "s3m_reasoner")
    assert a == b


def test_fingerprint_is_sensitive_to_each_component():
    base = invocation_fingerprint("ph", "pt", "mv", "s3m_reasoner")
    assert base != invocation_fingerprint("PH", "pt", "mv", "s3m_reasoner")
    assert base != invocation_fingerprint("ph", "PT", "mv", "s3m_reasoner")
    assert base != invocation_fingerprint("ph", "pt", "MV", "s3m_reasoner")
    assert base != invocation_fingerprint("ph", "pt", "mv", "load_flow_balanced")


def test_fingerprint_is_hex_sha256():
    fp = invocation_fingerprint("ph", "pt", "mv", "s3m_reasoner")
    assert len(fp) == 64
    int(fp, 16)  # must parse as hex


def test_fingerprint_no_delimiter_collision():
    # The delimiter cannot appear in components, so these must differ.
    assert invocation_fingerprint("a", "b", "c", "d") != invocation_fingerprint(
        "ab", "", "c", "d"
    )
