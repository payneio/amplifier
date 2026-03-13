"""Tests for amplifier_lib.config."""

from __future__ import annotations

import pytest


class TestExpandEnvVars:
    """Tests for expand_env_vars()."""

    def test_string_expansion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from amplifier_lib.config import expand_env_vars

        monkeypatch.setenv("TEST_KEY", "my-secret")
        assert expand_env_vars("${TEST_KEY}") == "my-secret"

    def test_default_value(self) -> None:
        from amplifier_lib.config import expand_env_vars

        result = expand_env_vars("${DEFINITELY_NOT_SET:fallback}")
        assert result == "fallback"

    def test_missing_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from amplifier_lib.config import expand_env_vars

        monkeypatch.delenv("DEFINITELY_NOT_SET", raising=False)
        assert expand_env_vars("${DEFINITELY_NOT_SET}") == ""

    def test_nested_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from amplifier_lib.config import expand_env_vars

        monkeypatch.setenv("MY_KEY", "secret123")
        result = expand_env_vars({"config": {"api_key": "${MY_KEY}", "model": "gpt-4"}})
        assert result == {"config": {"api_key": "secret123", "model": "gpt-4"}}

    def test_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from amplifier_lib.config import expand_env_vars

        monkeypatch.setenv("A", "1")
        monkeypatch.setenv("B", "2")
        assert expand_env_vars(["${A}", "${B}", "literal"]) == ["1", "2", "literal"]

    def test_empty_env_var_stripped_from_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from amplifier_lib.config import expand_env_vars

        monkeypatch.setenv("GOOD_KEY", "value")
        monkeypatch.setenv("EMPTY_KEY", "")
        monkeypatch.delenv("MISSING_KEY", raising=False)
        result = expand_env_vars({
            "good": "${GOOD_KEY}",
            "empty": "${EMPTY_KEY}",
            "missing": "${MISSING_KEY}",
            "literal": "keep",
        })
        assert result == {"good": "value", "literal": "keep"}

    def test_non_string_passthrough(self) -> None:
        from amplifier_lib.config import expand_env_vars

        assert expand_env_vars(42) == 42
        assert expand_env_vars(True) is True
        assert expand_env_vars(None) is None


class TestLoadProviderConfig:
    def test_missing_file(self, tmp_path) -> None:
        from amplifier_lib.config import load_provider_config

        assert load_provider_config(home=tmp_path) == []

    def test_reads_providers(self, tmp_path) -> None:
        from amplifier_lib.config import load_provider_config

        (tmp_path / "settings.yaml").write_text(
            "config:\n  providers:\n  - module: provider-anthropic\n    config:\n      api_key: sk-test\n"
        )
        result = load_provider_config(home=tmp_path)
        assert len(result) == 1
        assert result[0]["module"] == "provider-anthropic"

    def test_invalid_yaml(self, tmp_path) -> None:
        from amplifier_lib.config import load_provider_config

        (tmp_path / "settings.yaml").write_text("{{invalid")
        assert load_provider_config(home=tmp_path) == []

    def test_providers_not_a_list(self, tmp_path) -> None:
        from amplifier_lib.config import load_provider_config

        (tmp_path / "settings.yaml").write_text("config:\n  providers: not-a-list\n")
        assert load_provider_config(home=tmp_path) == []


class TestMergeSettingsProviders:
    def test_no_settings_returns_existing(self) -> None:
        from amplifier_lib.config import merge_settings_providers

        existing = [{"module": "provider-anthropic", "config": {"model": "opus"}}]
        assert merge_settings_providers(existing, []) == existing

    def test_no_existing_uses_settings(self) -> None:
        from amplifier_lib.config import merge_settings_providers

        settings = [{"module": "provider-anthropic", "config": {"api_key": "sk-test"}}]
        assert merge_settings_providers([], settings) == settings

    def test_merges_matching_provider(self) -> None:
        from amplifier_lib.config import merge_settings_providers

        existing = [{"module": "provider-anthropic", "config": {"model": "opus"}}]
        settings = [{"module": "provider-anthropic", "config": {"api_key": "sk-test"}}]
        result = merge_settings_providers(existing, settings)
        assert len(result) == 1
        assert result[0]["config"]["model"] == "opus"
        assert result[0]["config"]["api_key"] == "sk-test"


class TestInjectProviders:
    def test_injects_into_bundle(self) -> None:
        from types import SimpleNamespace

        from amplifier_lib.config import inject_providers

        bundle = SimpleNamespace(providers=[{"module": "provider-anthropic", "config": {}}])
        inject_providers(bundle, [{"module": "provider-anthropic", "config": {"api_key": "sk-test"}}])
        assert bundle.providers[0]["config"]["api_key"] == "sk-test"

    def test_no_providers_noop(self) -> None:
        from types import SimpleNamespace

        from amplifier_lib.config import inject_providers

        bundle = SimpleNamespace(providers=[])
        inject_providers(bundle, [])
        assert bundle.providers == []