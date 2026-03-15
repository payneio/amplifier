# Spawn Extraction Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the common spawn sequence into `PreparedBundle.create_child_session()` and move tool/hook filtering into amplifier-lib so both apps share the logic.

**Architecture:** Split `PreparedBundle.spawn()` into create (returns initialized session) and execute phases. Move `filter_tools`/`filter_hooks` to `spawn_utils.py`. Update amplifierd to use `create_child_session()`. Update CLI to use lib's filter functions.

**Tech Stack:** Python 3.12+, pytest, amplifier-lib/amplifier-core

**Spec:** `docs/superpowers/specs/2025-07-17-spawn-extraction-design.md`

---

## File Structure

### Modified files

| File | Change |
|------|--------|
| `amplifier-lib/amplifier_lib/bundle.py` | Add `create_child_session()`, refactor `spawn()` to call it |
| `amplifier-lib/amplifier_lib/spawn_utils.py` | Add `filter_tools()`, `filter_hooks()` |
| `amplifier-lib/amplifier_lib/__init__.py` | Export `filter_tools`, `filter_hooks` |
| `amplifier-lib/tests/test_spawn_utils.py` | Add tests for filter_tools/filter_hooks |
| `amplifierd/src/amplifierd/spawn.py` | Replace manual session setup with `create_child_session()` |
| `amplifier-cli/amplifier_cli/session_spawner.py` | Import filter_tools/filter_hooks from lib |

---

## Task 1: Add filter_tools and filter_hooks to amplifier-lib

**Files:**
- Modify: `amplifier-lib/amplifier_lib/spawn_utils.py`
- Modify: `amplifier-lib/tests/test_spawn_utils.py`
- Modify: `amplifier-lib/amplifier_lib/__init__.py`

- [ ] **Step 1: Write failing tests**

Append to `amplifier-lib/tests/test_spawn_utils.py`:

```python
class TestFilterTools:
    def test_exclude_removes_tools(self) -> None:
        from amplifier_lib.spawn_utils import filter_tools
        tools = [{"module": "tool-bash"}, {"module": "tool-web"}, {"module": "tool-fs"}]
        result = filter_tools(tools, {"exclude_tools": ["tool-web"]})
        assert [t["module"] for t in result] == ["tool-bash", "tool-fs"]

    def test_inherit_allowlist(self) -> None:
        from amplifier_lib.spawn_utils import filter_tools
        tools = [{"module": "tool-bash"}, {"module": "tool-web"}, {"module": "tool-fs"}]
        result = filter_tools(tools, {"inherit_tools": ["tool-bash"]})
        assert [t["module"] for t in result] == ["tool-bash"]

    def test_explicit_preserved_despite_exclude(self) -> None:
        from amplifier_lib.spawn_utils import filter_tools
        tools = [{"module": "tool-bash"}, {"module": "tool-web"}]
        result = filter_tools(tools, {"exclude_tools": ["tool-bash"]}, agent_explicit_tools=["tool-bash"])
        assert [t["module"] for t in result] == ["tool-bash", "tool-web"]

    def test_empty_inheritance_returns_all(self) -> None:
        from amplifier_lib.spawn_utils import filter_tools
        tools = [{"module": "tool-bash"}]
        result = filter_tools(tools, {})
        assert result == tools

    def test_empty_tools_returns_empty(self) -> None:
        from amplifier_lib.spawn_utils import filter_tools
        result = filter_tools([], {"exclude_tools": ["tool-bash"]})
        assert result == []


class TestFilterHooks:
    def test_exclude_removes_hooks(self) -> None:
        from amplifier_lib.spawn_utils import filter_hooks
        hooks = [{"module": "hooks-logging"}, {"module": "hooks-approval"}]
        result = filter_hooks(hooks, {"exclude_hooks": ["hooks-logging"]})
        assert [h["module"] for h in result] == ["hooks-approval"]

    def test_inherit_allowlist(self) -> None:
        from amplifier_lib.spawn_utils import filter_hooks
        hooks = [{"module": "hooks-logging"}, {"module": "hooks-approval"}]
        result = filter_hooks(hooks, {"inherit_hooks": ["hooks-approval"]})
        assert [h["module"] for h in result] == ["hooks-approval"]

    def test_explicit_preserved_despite_exclude(self) -> None:
        from amplifier_lib.spawn_utils import filter_hooks
        hooks = [{"module": "hooks-logging"}, {"module": "hooks-approval"}]
        result = filter_hooks(hooks, {"exclude_hooks": ["hooks-logging"]}, agent_explicit_hooks=["hooks-logging"])
        assert [h["module"] for h in result] == ["hooks-logging", "hooks-approval"]
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/test_spawn_utils.py::TestFilterTools -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement filter_tools and filter_hooks**

Add to the end of `amplifier-lib/amplifier_lib/spawn_utils.py`:

```python
def filter_tools(
    tools: list[dict[str, Any]],
    tool_inheritance: dict[str, list[str]],
    agent_explicit_tools: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter tools based on inheritance policy.

    Supports two modes:
    - ``exclude_tools``: inherit all EXCEPT listed modules (blocklist)
    - ``inherit_tools``: inherit ONLY listed modules (allowlist)

    Agent explicitly-declared tools are always preserved regardless of filtering.
    """
    if not tools:
        return []

    exclude = tool_inheritance.get("exclude_tools", [])
    inherit = tool_inheritance.get("inherit_tools")
    explicit = set(agent_explicit_tools or [])

    if inherit is not None:
        return [t for t in tools if t.get("module") in inherit or t.get("module") in explicit]
    if exclude:
        return [t for t in tools if t.get("module") not in exclude or t.get("module") in explicit]
    return list(tools)


def filter_hooks(
    hooks: list[dict[str, Any]],
    hook_inheritance: dict[str, list[str]],
    agent_explicit_hooks: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter hooks based on inheritance policy.

    Same semantics as :func:`filter_tools` but for hooks.
    Uses ``exclude_hooks`` / ``inherit_hooks`` keys.
    """
    if not hooks:
        return []

    exclude = hook_inheritance.get("exclude_hooks", [])
    inherit = hook_inheritance.get("inherit_hooks")
    explicit = set(agent_explicit_hooks or [])

    if inherit is not None:
        return [h for h in hooks if h.get("module") in inherit or h.get("module") in explicit]
    if exclude:
        return [h for h in hooks if h.get("module") not in exclude or h.get("module") in explicit]
    return list(hooks)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/test_spawn_utils.py -v -k "Filter"`
Expected: All 8 new tests PASS

- [ ] **Step 5: Add exports to __init__.py**

Add to `amplifier-lib/amplifier_lib/__init__.py`:
```python
from amplifier_lib.spawn_utils import filter_hooks
from amplifier_lib.spawn_utils import filter_tools
```
And add `"filter_tools"`, `"filter_hooks"` to `__all__`.

- [ ] **Step 6: Run full lib test suite, commit**

Run: `cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/ -v`

```
feat(lib): add filter_tools and filter_hooks to spawn_utils
```

---

## Task 2: Extract create_child_session from PreparedBundle.spawn

**Files:**
- Modify: `amplifier-lib/amplifier_lib/bundle.py` (lines 1173-1390)

- [ ] **Step 1: Run existing spawn tests to establish baseline**

Run: `cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/test_spawn_contract.py tests/test_spawn_enrichment.py -v`
Expected: All PASS (baseline)

- [ ] **Step 2: Extract create_child_session**

In `amplifier-lib/amplifier_lib/bundle.py`, in class `PreparedBundle`:

Add new method `create_child_session()` containing lines 1255-1354 of current `spawn()` (everything from "Compose with parent" through "system prompt factory"). The method signature matches `spawn()` minus `instruction`.

- [ ] **Step 3: Refactor spawn to use create_child_session**

Rewrite `spawn()` to:
1. Call `self.create_child_session(child_bundle, **kwargs)` to get the initialized session
2. Register the completion-capture hook (lines 1356-1373)
3. Execute instruction (line 1377)
4. Cleanup (line 1381)
5. Return result dict (lines 1383-1390)

The `spawn()` method should be ~30 lines after refactoring.

- [ ] **Step 4: Run existing spawn tests to verify no regressions**

Run: `cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/test_spawn_contract.py tests/test_spawn_enrichment.py -v`
Expected: All PASS (identical behavior)

- [ ] **Step 5: Run full lib test suite**

Run: `cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```
refactor(lib): extract create_child_session from PreparedBundle.spawn
```

---

## Task 3: Update amplifierd to use create_child_session

**Files:**
- Modify: `amplifierd/src/amplifierd/spawn.py`

- [ ] **Step 1: Run amplifierd tests to establish baseline**

Run: `cd /data/labs/a/amplifier/amplifierd && python -m pytest tests/ -v`
Expected: All 556 PASS

- [ ] **Step 2: Replace manual session setup in _spawn_with_event_forwarding**

In `amplifierd/src/amplifierd/spawn.py`, replace the manual steps 1-11 in `_spawn_with_event_forwarding()` (lines 190-291) with:

```python
child_session = await prepared.create_child_session(
    child_bundle=child_bundle,
    parent_session=parent_session,
    session_id=sub_session_id,
    orchestrator_config=orchestrator_config,
    parent_messages=parent_messages,
    provider_preferences=provider_preferences,
    self_delegation_depth=self_delegation_depth,
)
```

Keep everything after (steps 12-17): persistence hooks, SessionManager registration, EventBus wiring, recursive spawn, completion capture, execute, cleanup.

Remove the now-unused imports: `AmplifierSession`, `HookResult` (only if no longer needed after the change -- `HookResult` is still used for the completion capture hook).

- [ ] **Step 3: Run amplifierd tests**

Run: `cd /data/labs/a/amplifier/amplifierd && python -m pytest tests/ -v`
Expected: All 556 PASS

- [ ] **Step 4: Commit**

```
refactor(amplifierd): use create_child_session in spawn
```

---

## Task 4: Update CLI to use lib's filter functions

**Files:**
- Modify: `amplifier-cli/amplifier_cli/session_spawner.py`

- [ ] **Step 1: Run CLI tests to establish baseline**

Run: `cd /data/labs/a/amplifier/amplifier-cli && python -m pytest tests/ -v`
Expected: All 520 PASS

- [ ] **Step 2: Replace local _filter_tools and _filter_hooks**

In `amplifier-cli/amplifier_cli/session_spawner.py`:

1. Remove `_filter_tools()` function (lines 63-123)
2. Remove `_filter_hooks()` function (lines 126-186)
3. Add import: `from amplifier_lib.spawn_utils import filter_tools, filter_hooks`
4. Update call sites in `spawn_sub_session()`:
   - Change `merged_config = _filter_tools(merged_config, tool_inheritance, agent_tool_modules)` to:
     ```python
     merged_config["tools"] = filter_tools(
         merged_config.get("tools", []), tool_inheritance, agent_tool_modules
     )
     ```
   - Same pattern for hooks:
     ```python
     merged_config["hooks"] = filter_hooks(
         merged_config.get("hooks", []), hook_inheritance, agent_hook_modules
     )
     ```

- [ ] **Step 3: Run CLI tests**

Run: `cd /data/labs/a/amplifier/amplifier-cli && python -m pytest tests/ -v`
Expected: All 520 PASS

- [ ] **Step 4: Commit**

```
refactor(cli): use lib's filter_tools and filter_hooks
```

---

## Task 5: Cross-project verification

- [ ] **Step 1: Run all three test suites**

```bash
cd /data/labs/a/amplifier/amplifier-lib && python -m pytest tests/ -q
cd /data/labs/a/amplifier/amplifier-cli && python -m pytest tests/ -q
cd /data/labs/a/amplifier/amplifierd && python -m pytest tests/ -q
```

All must PASS with zero failures.

- [ ] **Step 2: Run python_check on modified files**

Check: `amplifier-lib/amplifier_lib/bundle.py`, `amplifier-lib/amplifier_lib/spawn_utils.py`, `amplifierd/src/amplifierd/spawn.py`

- [ ] **Step 3: Verify no stale references**

```bash
grep -rn "_filter_tools\|_filter_hooks" amplifier-cli/amplifier_cli/
grep -rn "from amplifier_lib.runtime import AmplifierSession" amplifierd/src/amplifierd/spawn.py
```

Expected: Zero matches for _filter_tools/_filter_hooks in CLI. The AmplifierSession import in daemon spawn.py should be gone (now handled inside create_child_session).

- [ ] **Step 4: Commit**

```
chore: verify cross-project integration after spawn extraction
```