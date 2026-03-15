# Spawn Extraction Design

**Goal:** Eliminate duplicated spawn logic between amplifierd and amplifier-lib by extracting the common session-creation sequence into a reusable `PreparedBundle.create_child_session()` method, and move tool/hook filtering utilities into the lib.

## Problem

Three spawn implementations exist:

1. **`PreparedBundle.spawn()`** (lib) -- Does compose, mount plan, create session, initialize, execute, cleanup as one atomic operation.
2. **`amplifierd/spawn.py`** -- Reimplements steps 1-11 of `spawn()` to insert EventBus/SessionHandle wiring between initialize and execute. Has a comment: "Replicates the essential logic of PreparedBundle.spawn()".
3. **`amplifier-cli/session_spawner.py`** -- Uses a config-merge approach (not Bundle-based). Has `_filter_tools()` and `_filter_hooks()` utilities that are generic but trapped in the CLI.

The core issue: `PreparedBundle.spawn()` is atomic (create+execute+cleanup), so apps that need to insert wiring between create and execute must reimplement the entire creation sequence.

## Design

### 1. New method: `PreparedBundle.create_child_session()`

Split `spawn()` into two phases: **create** (returns initialized session) and **execute** (runs instruction).

```python
async def create_child_session(
    self,
    child_bundle: Bundle,
    *,
    compose: bool = True,
    parent_session: Any = None,
    session_id: str | None = None,
    orchestrator_config: dict[str, Any] | None = None,
    parent_messages: list[dict[str, Any]] | None = None,
    session_cwd: Path | None = None,
    provider_preferences: list[ProviderPreference] | None = None,
    self_delegation_depth: int = 0,
) -> AmplifierSession:
```

**The 11 common steps it performs:**
1. Compose child with parent bundle (if `compose=True`)
2. Create mount plan from composed bundle
3. Merge orchestrator config override
4. Apply provider preferences
5. Create `AmplifierSession` (with parent_id, approval_system, display_system)
6. Mount module-source-resolver from parent PreparedBundle
7. Set working directory capability
8. Call `initialize()` (mounts modules)
9. Register `self_delegation_depth` capability
10. Inject parent messages (if new session)
11. Set up system prompt factory

**Returns:** Initialized `AmplifierSession`, ready for app-specific wiring before `execute()`.

**`spawn()` becomes a thin wrapper:**
```python
async def spawn(self, child_bundle, instruction, **kwargs):
    child_session = await self.create_child_session(child_bundle, **kwargs)
    # capture hook, execute, cleanup (unchanged)
```

### 2. Utility functions: `filter_tools()` and `filter_hooks()`

Move from CLI's `session_spawner.py` into `amplifier_lib/spawn_utils.py`.

```python
def filter_tools(
    tools: list[dict[str, Any]],
    tool_inheritance: dict[str, list[str]],
    agent_explicit_tools: list[str] | None = None,
) -> list[dict[str, Any]]:

def filter_hooks(
    hooks: list[dict[str, Any]],
    hook_inheritance: dict[str, list[str]],
    agent_explicit_hooks: list[str] | None = None,
) -> list[dict[str, Any]]:
```

Signature change from CLI version: takes the tools/hooks list directly instead of the whole config dict.

Supports two modes each:
- Blocklist: `exclude_tools` / `exclude_hooks` -- inherit all EXCEPT these
- Allowlist: `inherit_tools` / `inherit_hooks` -- inherit ONLY these

Agent explicitly-declared items are always preserved regardless of filtering.

### 3. App changes

**amplifierd `spawn.py`:**
- `_spawn_with_event_forwarding()` replaces ~80 lines of duplicated session setup with a single `await prepared.create_child_session(...)` call
- Keeps daemon-specific wiring after: persistence hooks, SessionHandle, EventBus, recursive spawn capability
- Keeps daemon-specific execute path: `child_handle.execute()` + `session_manager.destroy()`

**amplifier-cli `session_spawner.py`:**
- Imports `filter_tools()` / `filter_hooks()` from `amplifier_lib.spawn_utils` (replaces local `_filter_tools` / `_filter_hooks`)
- Core spawn sequence stays config-merge based (different paradigm from Bundle-based `create_child_session`)
- Full CLI migration to `create_child_session()` deferred as future work

### 4. What stays in each app

**Stays in CLI:**
- Config-merge spawn sequence (different paradigm)
- sys.path sharing from parent loader
- Display system push_nesting
- Cancellation propagation
- SessionStore persistence
- Approval provider registration

**Stays in daemon:**
- EventBus / SessionHandle wiring
- Persistence hook registration
- SessionManager register/destroy

## File changes

| File | Change |
|------|--------|
| `amplifier-lib/amplifier_lib/bundle.py` | Add `create_child_session()`, refactor `spawn()` to use it |
| `amplifier-lib/amplifier_lib/spawn_utils.py` | Add `filter_tools()`, `filter_hooks()` |
| `amplifier-lib/amplifier_lib/__init__.py` | Export new functions |
| `amplifier-lib/tests/test_spawn_utils.py` | Tests for filter_tools/filter_hooks |
| `amplifier-lib/tests/test_bundle.py` or new test file | Tests for create_child_session |
| `amplifierd/src/amplifierd/spawn.py` | Use `create_child_session()` in `_spawn_with_event_forwarding` |
| `amplifier-cli/amplifier_cli/session_spawner.py` | Import filter_tools/filter_hooks from lib |

## Risk assessment

- **Low risk:** `filter_tools` / `filter_hooks` extraction -- pure functions, easy to test
- **Low risk:** `create_child_session()` -- extracted from existing `spawn()`, spawn becomes a wrapper calling it
- **Medium risk:** amplifierd spawn rewrite -- replacing ~80 lines with `create_child_session()` call; must verify EventBus wiring still works with the session returned by the lib
- **Low risk:** CLI filter import swap -- just changing import paths