# Shared Library Extraction Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move duplicated functionality from amplifier-cli and amplifierd into amplifier-lib so both apps share a single implementation.

**Architecture:** Extract five areas of shared logic into new amplifier-lib modules: env-var expansion, known source registries, provider config loading/injection, session persistence hooks, and core spawn sequence. Each extraction follows the same pattern: add to lib with tests, then update both apps to import from lib and delete their local copies.

**Tech Stack:** Python 3.12+, pytest, pyyaml

---

## File Structure

### New files in amplifier-lib

| File | Responsibility |
|------|----------------|
| `amplifier_lib/config.py` | `expand_env_vars()`, `load_provider_config()`, `merge_settings_providers()`, `inject_providers()` |
| `amplifier_lib/known_sources.py` | `WELL_KNOWN_BUNDLES`, `DEFAULT_PROVIDER_SOURCES`, `PROVIDER_DEPENDENCIES` |
| `amplifier_lib/session/persistence.py` | `TranscriptSaveHook`, `MetadataSaveHook`, `write_transcript()`, `load_transcript()`, `write_metadata()`, `load_metadata()` |
| `amplifier-lib/tests/test_config.py` | Tests for config.py |
| `amplifier-lib/tests/test_known_sources.py` | Tests for known_sources.py |
| `amplifier-lib/tests/test_session_persistence.py` | Tests for session/persistence.py |

### Modified files

| File | Change |
|------|--------|
| `amplifier_lib/__init__.py` | Add new public exports |
| `amplifierd/src/amplifierd/providers.py` | Remove `expand_env_vars`, `_deep_merge`, `load_provider_config`, `merge_settings_providers`, `inject_providers`; import from `amplifier_lib` |
| `amplifierd/src/amplifierd/config.py` | Remove `WELL_KNOWN_BUNDLES`; import from `amplifier_lib` |
| `amplifierd/src/amplifierd/persistence.py` | Replace with thin wrapper around `amplifier_lib.session.persistence` |
| `amplifier-cli/amplifier_cli/runtime/config.py` | Remove `expand_env_vars`; import from `amplifier_lib` |
| `amplifier-cli/amplifier_cli/provider_sources.py` | Remove `DEFAULT_PROVIDER_SOURCES`, `PROVIDER_DEPENDENCIES`; import from `amplifier_lib` |
| `amplifier-cli/amplifier_cli/lib/bundle_loader/discovery.py` | Remove `WELL_KNOWN_BUNDLES`; import from `amplifier_lib` |

---

## Chunk 1: expand_env_vars and _deep_merge cleanup

### Task 1: Add expand_env_vars to amplifier-lib

**Files:**
- Create: `amplifier-lib/amplifier_lib/config.py`
- Create: `amplifier-lib/tests/test_config.py`
- Modify: `amplifier-lib/amplifier_lib/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `amplifier-lib/tests/test_config.py` with tests ported from `amplifierd/tests/test_providers.py::TestExpandEnvVars`. The function signature matches the daemon's version (accepts `Any`, not just `dict`):

```python
"""Tests for amplifier_lib.config."""

from __future__ import annotations

import os
from typing import Any

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd amplifier-lib && python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amplifier_lib.config'`

- [ ] **Step 3: Implement expand_env_vars in amplifier_lib/config.py**

Create `amplifier-lib/amplifier_lib/config.py`. Port the implementation from `amplifierd/src/amplifierd/providers.py:55-72` (the daemon's version handles `Any` input, which is more general than the CLI's `dict`-only version):

```python
"""Configuration utilities for Amplifier applications.

Provides shared mechanisms for environment variable expansion and
provider configuration loading/injection. Apps use these directly
rather than reimplementing the same logic.
"""

from __future__ import annotations

import os
import re
from typing import Any

_ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def expand_env_vars(value: Any) -> Any:
    """Recursively expand ${VAR} and ${VAR:default} references in config values.

    After expansion, dict entries whose values are empty strings are removed.
    This prevents empty env vars from overriding provider defaults with blanks.
    """
    if isinstance(value, str):
        return _ENV_PATTERN.sub(
            lambda m: os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else ""),
            value,
        )
    if isinstance(value, dict):
        expanded = {k: expand_env_vars(v) for k, v in value.items()}
        return {k: v for k, v in expanded.items() if v != ""}
    if isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd amplifier-lib && python -m pytest tests/test_config.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Add export to `__init__.py`**

Add to `amplifier-lib/amplifier_lib/__init__.py`:
```python
from amplifier_lib.config import expand_env_vars
```
And add `"expand_env_vars"` to the `__all__` list.

- [ ] **Step 6: Run full amplifier-lib test suite**

Run: `cd amplifier-lib && python -m pytest tests/ -v`
Expected: All tests PASS (no regressions)

- [ ] **Step 7: Commit**

```
feat(lib): add expand_env_vars to amplifier_lib.config
```

---

### Task 2: Update amplifierd to use lib's expand_env_vars and deep_merge

**Files:**
- Modify: `amplifierd/src/amplifierd/providers.py`
- Modify: `amplifierd/tests/test_providers.py`

- [ ] **Step 1: Run amplifierd tests to verify green baseline**

Run: `cd amplifierd && python -m pytest tests/test_providers.py -v`
Expected: All tests PASS

- [ ] **Step 2: Update providers.py**

In `amplifierd/src/amplifierd/providers.py`:

1. Remove `_ENV_PATTERN`, `expand_env_vars()` (lines 19, 55-72)
2. Remove `_deep_merge()` (lines 75-87)
3. Add imports at top:
   ```python
   from amplifier_lib.config import expand_env_vars
   from amplifier_lib.dicts import deep_merge
   ```
4. Replace `_deep_merge(` with `deep_merge(` in `_merge_provider_item()` (2 call sites)

- [ ] **Step 3: Update tests to import from new locations**

In `amplifierd/tests/test_providers.py`:

1. In `TestExpandEnvVars`: change `from amplifierd.providers import expand_env_vars` to `from amplifier_lib.config import expand_env_vars`
2. In `TestDeepMerge`: change `from amplifierd.providers import _deep_merge` to `from amplifier_lib.dicts import deep_merge` and rename references from `_deep_merge` to `deep_merge`

- [ ] **Step 4: Run amplifierd tests**

Run: `cd amplifierd && python -m pytest tests/test_providers.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run full amplifierd test suite**

Run: `cd amplifierd && python -m pytest tests/ -v`
Expected: All 556 tests PASS

- [ ] **Step 6: Commit**

```
refactor(amplifierd): use lib's expand_env_vars and deep_merge
```

---

### Task 3: Update amplifier-cli to use lib's expand_env_vars

**Files:**
- Modify: `amplifier-cli/amplifier_cli/runtime/config.py`

- [ ] **Step 1: Run CLI tests to verify green baseline**

Run: `cd amplifier-cli && python -m pytest tests/ -v`
Expected: Tests PASS

- [ ] **Step 2: Update runtime/config.py**

In `amplifier-cli/amplifier_cli/runtime/config.py`:

1. Remove the `ENV_PATTERN` constant (line 604) and the `expand_env_vars()` function (lines 607-624)
2. Add import: `from amplifier_lib.config import expand_env_vars`
3. Keep the existing call site at line 211 unchanged (it already calls `expand_env_vars(bundle_config)`)

- [ ] **Step 3: Run CLI tests**

Run: `cd amplifier-cli && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```
refactor(cli): use lib's expand_env_vars
```

---

## Chunk 2: Known source registries

### Task 4: Add known_sources.py to amplifier-lib

**Files:**
- Create: `amplifier-lib/amplifier_lib/known_sources.py`
- Create: `amplifier-lib/tests/test_known_sources.py`
- Modify: `amplifier-lib/amplifier_lib/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `amplifier-lib/tests/test_known_sources.py`:

```python
"""Tests for amplifier_lib.known_sources."""


class TestWellKnownBundles:
    def test_foundation_present(self) -> None:
        from amplifier_lib.known_sources import WELL_KNOWN_BUNDLES
        assert "foundation" in WELL_KNOWN_BUNDLES

    def test_each_entry_has_remote(self) -> None:
        from amplifier_lib.known_sources import WELL_KNOWN_BUNDLES
        for name, info in WELL_KNOWN_BUNDLES.items():
            assert "remote" in info, f"Bundle '{name}' missing 'remote' key"


class TestDefaultProviderSources:
    def test_anthropic_present(self) -> None:
        from amplifier_lib.known_sources import DEFAULT_PROVIDER_SOURCES
        assert "provider-anthropic" in DEFAULT_PROVIDER_SOURCES

    def test_all_values_are_git_uris(self) -> None:
        from amplifier_lib.known_sources import DEFAULT_PROVIDER_SOURCES
        for name, uri in DEFAULT_PROVIDER_SOURCES.items():
            assert uri.startswith("git+https://"), f"{name} URI doesn't start with git+https://"


class TestProviderDependencies:
    def test_azure_depends_on_openai(self) -> None:
        from amplifier_lib.known_sources import PROVIDER_DEPENDENCIES
        assert "provider-openai" in PROVIDER_DEPENDENCIES.get("provider-azure-openai", [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd amplifier-lib && python -m pytest tests/test_known_sources.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement known_sources.py**

Create `amplifier-lib/amplifier_lib/known_sources.py`. Merge the CLI's `WELL_KNOWN_BUNDLES` (richer format with `package`, `remote`, `show_in_list`) with the daemon's entries. Merge CLI's `DEFAULT_PROVIDER_SOURCES` and `PROVIDER_DEPENDENCIES`.

Source data from:
- `amplifier-cli/amplifier_cli/lib/bundle_loader/discovery.py:40-80` (WELL_KNOWN_BUNDLES)
- `amplifier-cli/amplifier_cli/provider_sources.py:21-40` (DEFAULT_PROVIDER_SOURCES, PROVIDER_DEPENDENCIES)
- `amplifierd/src/amplifierd/config.py:17-26` (daemon's WELL_KNOWN_BUNDLES - check for entries not in CLI's list)

The unified `WELL_KNOWN_BUNDLES` should use the CLI's richer format. Any daemon-only entries (like `distro`, `modes`, `notify`) should be added.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd amplifier-lib && python -m pytest tests/test_known_sources.py -v`
Expected: All tests PASS

- [ ] **Step 5: Add exports to `__init__.py`**

Add to `amplifier-lib/amplifier_lib/__init__.py`:
```python
from amplifier_lib.known_sources import DEFAULT_PROVIDER_SOURCES, PROVIDER_DEPENDENCIES, WELL_KNOWN_BUNDLES
```
And add to `__all__`.

- [ ] **Step 6: Commit**

```
feat(lib): add known_sources registry (bundles, providers, deps)
```

---

### Task 5: Update apps to use lib's known_sources

**Files:**
- Modify: `amplifierd/src/amplifierd/config.py`
- Modify: `amplifier-cli/amplifier_cli/lib/bundle_loader/discovery.py`
- Modify: `amplifier-cli/amplifier_cli/provider_sources.py`

- [ ] **Step 1: Update amplifierd/config.py**

Remove `WELL_KNOWN_BUNDLES` dict (lines 17-26). Add import:
```python
from amplifier_lib.known_sources import WELL_KNOWN_BUNDLES
```
Convert to simple `{name: info["remote"]}` dict in the `DaemonSettings.bundles` default factory since the daemon only uses the URI strings.

- [ ] **Step 2: Run amplifierd tests**

Run: `cd amplifierd && python -m pytest tests/ -v`
Expected: All 556 tests PASS

- [ ] **Step 3: Update amplifier-cli discovery.py**

In `amplifier-cli/amplifier_cli/lib/bundle_loader/discovery.py`:
Remove `WELL_KNOWN_BUNDLES` dict (lines 40-80). Add import:
```python
from amplifier_lib.known_sources import WELL_KNOWN_BUNDLES
```

- [ ] **Step 4: Update amplifier-cli provider_sources.py**

In `amplifier-cli/amplifier_cli/provider_sources.py`:
Remove `DEFAULT_PROVIDER_SOURCES` dict (lines 21-29) and `PROVIDER_DEPENDENCIES` dict (lines 36-40). Add imports:
```python
from amplifier_lib.known_sources import DEFAULT_PROVIDER_SOURCES, PROVIDER_DEPENDENCIES
```

- [ ] **Step 5: Run CLI tests**

Run: `cd amplifier-cli && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```
refactor: use lib's known_sources in both apps
```

---

## Chunk 3: Provider configuration functions

### Task 6: Add provider config functions to amplifier-lib

**Files:**
- Modify: `amplifier-lib/amplifier_lib/config.py`
- Modify: `amplifier-lib/tests/test_config.py`

- [ ] **Step 1: Write failing tests for load_provider_config**

Add to `amplifier-lib/tests/test_config.py`. Port from `amplifierd/tests/test_providers.py::TestLoadProviderConfig`:

```python
class TestLoadProviderConfig:
    def test_missing_file(self, tmp_path: Path) -> None:
        from amplifier_lib.config import load_provider_config
        assert load_provider_config(home=tmp_path) == []

    def test_reads_providers(self, tmp_path: Path) -> None:
        from amplifier_lib.config import load_provider_config
        (tmp_path / "settings.yaml").write_text(
            "config:\n  providers:\n  - module: provider-anthropic\n    config:\n      api_key: sk-test\n"
        )
        result = load_provider_config(home=tmp_path)
        assert len(result) == 1
        assert result[0]["module"] == "provider-anthropic"

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        from amplifier_lib.config import load_provider_config
        (tmp_path / "settings.yaml").write_text("{{invalid")
        assert load_provider_config(home=tmp_path) == []

    def test_providers_not_a_list(self, tmp_path: Path) -> None:
        from amplifier_lib.config import load_provider_config
        (tmp_path / "settings.yaml").write_text("config:\n  providers: not-a-list\n")
        assert load_provider_config(home=tmp_path) == []
```

- [ ] **Step 2: Write failing tests for merge_settings_providers and inject_providers**

Add to `amplifier-lib/tests/test_config.py`. Port from `amplifierd/tests/test_providers.py::TestMergeSettingsProviders` and `TestInjectProviders`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd amplifier-lib && python -m pytest tests/test_config.py -v`
Expected: FAIL for the new test classes

- [ ] **Step 4: Implement the functions**

Add `load_provider_config()`, `merge_settings_providers()`, `_merge_provider_item()`, and `inject_providers()` to `amplifier-lib/amplifier_lib/config.py`. Port directly from `amplifierd/src/amplifierd/providers.py:22-177`. Use `amplifier_lib.dicts.deep_merge` instead of the local `_deep_merge`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd amplifier-lib && python -m pytest tests/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 6: Add exports, run full suite, commit**

Add new exports to `__init__.py`. Run `cd amplifier-lib && python -m pytest tests/ -v`. Commit:
```
feat(lib): add provider config loading and injection
```

---

### Task 7: Update amplifierd to use lib's provider config functions

**Files:**
- Modify: `amplifierd/src/amplifierd/providers.py`
- Modify: `amplifierd/tests/test_providers.py`

- [ ] **Step 1: Gut amplifierd/providers.py**

Replace the entire file with thin re-exports:

```python
"""Provider configuration loading and injection.

Thin re-export layer. All logic lives in amplifier_lib.config.
"""
from amplifier_lib.config import (
    expand_env_vars,
    inject_providers,
    load_provider_config,
    merge_settings_providers,
)

__all__ = [
    "expand_env_vars",
    "inject_providers",
    "load_provider_config",
    "merge_settings_providers",
]
```

- [ ] **Step 2: Update test imports**

In `amplifierd/tests/test_providers.py`, update all `from amplifierd.providers import ...` to `from amplifier_lib.config import ...`. Keep the test logic unchanged.

- [ ] **Step 3: Run tests**

Run: `cd amplifierd && python -m pytest tests/ -v`
Expected: All 556 tests PASS

- [ ] **Step 4: Commit**

```
refactor(amplifierd): delegate provider config to amplifier_lib
```

---

## Chunk 4: Session persistence

### Task 8: Add session persistence to amplifier-lib

**Files:**
- Create: `amplifier-lib/amplifier_lib/session/persistence.py`
- Create: `amplifier-lib/tests/test_session_persistence.py`
- Modify: `amplifier-lib/amplifier_lib/session/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `amplifier-lib/tests/test_session_persistence.py` with tests for `write_transcript`, `load_transcript`, `write_metadata`, `load_metadata`. Port from `amplifierd/tests/test_persistence.py` and `amplifierd/tests/test_transcript.py`:

```python
"""Tests for amplifier_lib.session.persistence."""

import json
from pathlib import Path


class TestWriteTranscript:
    def test_writes_jsonl(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_transcript
        messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        write_transcript(tmp_path, messages)
        lines = (tmp_path / "transcript.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["content"] == "hello"

    def test_filters_system_roles(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_transcript
        messages = [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "hello"},
        ]
        write_transcript(tmp_path, messages)
        lines = (tmp_path / "transcript.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1


class TestLoadTranscript:
    def test_loads_messages(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import load_transcript
        (tmp_path / "transcript.jsonl").write_text(
            '{"role": "user", "content": "hello"}\n'
        )
        messages = load_transcript(tmp_path)
        assert len(messages) == 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import load_transcript
        import pytest
        with pytest.raises(FileNotFoundError):
            load_transcript(tmp_path)


class TestWriteMetadata:
    def test_writes_json(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_metadata
        tmp_path.mkdir(exist_ok=True)
        write_metadata(tmp_path, {"session_id": "abc", "turn_count": 1})
        data = json.loads((tmp_path / "metadata.json").read_text())
        assert data["session_id"] == "abc"

    def test_merges_with_existing(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_metadata
        tmp_path.mkdir(exist_ok=True)
        write_metadata(tmp_path, {"session_id": "abc", "name": "chat"})
        write_metadata(tmp_path, {"turn_count": 3})
        data = json.loads((tmp_path / "metadata.json").read_text())
        assert data["name"] == "chat"
        assert data["turn_count"] == 3


class TestLoadMetadata:
    def test_missing_returns_empty(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import load_metadata
        assert load_metadata(tmp_path) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd amplifier-lib && python -m pytest tests/test_session_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement session/persistence.py**

Create `amplifier-lib/amplifier_lib/session/persistence.py`. Port the pure-function persistence logic from `amplifierd/src/amplifierd/persistence.py`: `write_transcript`, `load_transcript`, `write_metadata`, `load_metadata`, and the `_sanitize` / `_atomic_write` helpers.

Do NOT port `TranscriptSaveHook` or `MetadataSaveHook` yet - those depend on `amplifier_core.models.HookResult` which amplifier-lib does not depend on. The hook classes stay in the apps for now; only the pure I/O functions move.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd amplifier-lib && python -m pytest tests/test_session_persistence.py -v`
Expected: All tests PASS

- [ ] **Step 5: Add exports to session/__init__.py**

Add to `amplifier-lib/amplifier_lib/session/__init__.py`:
```python
from .persistence import (
    load_metadata,
    load_transcript,
    write_metadata,
    write_transcript,
)
```

- [ ] **Step 6: Run full suite, commit**

Run: `cd amplifier-lib && python -m pytest tests/ -v`
Expected: All tests PASS

```
feat(lib): add session persistence I/O functions
```

---

### Task 9: Update amplifierd persistence to use lib functions

**Files:**
- Modify: `amplifierd/src/amplifierd/persistence.py`

- [ ] **Step 1: Update persistence.py to import from lib**

In `amplifierd/src/amplifierd/persistence.py`:
1. Remove `write_transcript`, `load_transcript`, `write_metadata`, `load_metadata`, `_sanitize`, `_atomic_write`
2. Add imports from lib:
   ```python
   from amplifier_lib.session.persistence import (
       load_metadata,
       load_transcript,
       write_metadata,
       write_transcript,
   )
   ```
3. Keep `TranscriptSaveHook`, `MetadataSaveHook`, and `register_persistence_hooks` in place (they use `amplifier_core` types).

- [ ] **Step 2: Run tests**

Run: `cd amplifierd && python -m pytest tests/ -v`
Expected: All 556 tests PASS

- [ ] **Step 3: Commit**

```
refactor(amplifierd): use lib's persistence I/O functions
```

---

## Chunk 5: Final verification

### Task 10: Cross-project verification

- [ ] **Step 1: Run all three test suites**

```bash
cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/ -v
cd /data/labs/a/amplifier/amplifierd && python -m pytest tests/ -v
cd /data/labs/a/amplifier/amplifier-cli && python -m pytest tests/ -v
```

All must PASS with zero failures.

- [ ] **Step 2: Run python_check on modified files**

```bash
python_check paths=["amplifier-lib/amplifier_lib/config.py", "amplifier-lib/amplifier_lib/known_sources.py", "amplifier-lib/amplifier_lib/session/persistence.py"]
```

- [ ] **Step 3: Verify no stale references remain**

```bash
grep -rn "from amplifierd.providers import expand_env_vars\|from amplifierd.providers import _deep_merge\|from amplifierd.providers import load_provider_config" amplifierd/src/
```

Expected: Zero matches (all imports should come from amplifier_lib now).

- [ ] **Step 4: Final commit**

```
chore: verify cross-project integration after lib extraction
```
