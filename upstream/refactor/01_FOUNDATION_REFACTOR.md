# Foundation Refactor: Replacing amplifier-core with core-lite

## Background

After establishing that ~95% of amplifier-core is reinventing Python packaging
(see VERDICT.md), we investigated what it would take for amplifier-foundation —
the primary consumer of core — to run against core-lite instead.

## What foundation actually imports from core

We grepped every Python file in amplifier-foundation for `amplifier_core` imports.
The results were surprising: foundation uses almost nothing from core.

| Symbol | Where used | How | In core-lite? |
|--------|-----------|-----|---------------|
| `HookResult` | 4 hook modules + bundle.py | Top-level + lazy | Yes |
| `ToolResult` | tool-delegate | Top-level | Yes |
| `HookRegistry` | 2 test files | Direct submodule import | Yes |
| `AmplifierSession` | bundle.py (2 call sites) | Lazy | No |
| `ModuleCoordinator` | tool-delegate | Type annotation only | No |
| `ChatRequest` + `Message` | hooks-session-naming | Lazy, one code path | No |

### What foundation does NOT import

Zero usage across the entire repo of:

- `interfaces.py` — the Protocol definitions (Orchestrator, Provider, Tool, ContextManager)
- `loader.py` — the entry_points wrapper (ModuleLoader)
- `events.py` — all 35 event name constants
- `llm_errors.py` — the error taxonomy
- `validation/` — 2,000 lines of module contract validators
- `coordinator.py` — as an implementation (only as a type annotation in one file)

The stuff we kept in core-lite for being "genuinely novel" (events.py) isn't
even used by the primary consumer.

## The blocker: AmplifierSession

`bundle.py` has two methods — `create_session()` and `spawn()` — that are the
entire point of the foundation library. Both instantiate `AmplifierSession` and
call its coordinator, initialize, execute, and cleanup methods.

But what does AmplifierSession actually do?

1. Generate a session_id
2. Create a coordinator (dict with named slots)
3. For-loop over config entries calling `loader.load()` for each module
4. Call `orchestrator.execute(prompt, context, providers, tools, hooks)`
5. Cleanup on exit

It's glue code over a dict and a plugin loader.

## The refactor: Option B

Rather than adding session glue to core-lite, we moved the session lifecycle
INTO foundation. This is the honest architecture: acknowledge that the "kernel"
is just glue code and let the application own it.

### New file: `amplifier_lib/runtime.py` (599 lines)

A single file that replaces three amplifier-core components:

| Replaced | With | Lines |
|----------|------|-------|
| `ModuleCoordinator` (Rust-backed, 247-line Python wrapper) | `Coordinator` — dict with mount/get/capabilities/hooks/cleanup | ~120 |
| `ModuleLoader` (728 lines, WASM/gRPC/validation) | 3 functions: `_load_entry_point`, `_load_filesystem`, `_load_module` | ~60 |
| `AmplifierSession` (259 lines + 257-line `_session_init.py`) | `Session` — initialize/execute/cleanup lifecycle | ~150 |
| `_rust_wrappers.process_hook_result` (187 lines) | `Coordinator.process_hook_result` — routes inject/approve/display | ~50 |

Depends only on core-lite:
- `amplifier_lib.core.hooks.HookRegistry` (emit with action precedence)
- `amplifier_lib.core.models.HookResult` (action protocol)

### Changes to existing files

**`amplifier_lib/bundle.py`** — 2 lines changed:

```python
# Before (2 call sites):
from amplifier_core import AmplifierSession
# After:
from amplifier_lib.runtime import Session
```

**`modules/tool-delegate/__init__.py`** — 3 lines changed:

```python
# Before:
from amplifier_core import ModuleCoordinator, ToolResult
# After:
from amplifier_lib.core import ToolResult
# ModuleCoordinator replaced with Any (was only a type annotation)
```

**`modules/hooks-session-naming/__init__.py`** — try/except fallback:

```python
# Now gracefully degrades if ChatRequest/Message aren't available
try:
    from amplifier_lib.core import ChatRequest, Message
    request = ChatRequest(messages=[Message(role="user", content=prompt)])
except ImportError:
    # Inline Pydantic fallback for core-lite environments
```

## Remaining amplifier_core imports

Every remaining import resolves to something in core-lite:

```
HookResult   — 4 hook modules + bundle.py + runtime.py    models.py
ToolResult   — tool-delegate + test                        models.py
HookRegistry — runtime.py                                  hooks.py
ChatRequest  — hooks-session-naming (with fallback)        graceful degradation
```

## The numbers

```
amplifier-core total:     ~9,800 lines Python + Rust + WASM + gRPC + Node
replacement total:        ~1,020 lines Python (599 runtime.py + 420 core-lite)

Reduction:                ~89%
Rust/WASM/gRPC/Node:      eliminated entirely
External dependencies:    pydantic (already required)
```

The Coordinator is still just a dict with methods. The module loader is still
`importlib.metadata.entry_points`. The session is still a for-loop. The
difference is that now nobody pretends otherwise.
