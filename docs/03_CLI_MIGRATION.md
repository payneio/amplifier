# CLI Migration: Dropping amplifier-core

## The situation

`amplifier-app-cli` is a 28,000-line Click application that was the primary
consumer of `amplifier-core`. After absorbing core-lite into the library
(doc 01) and splitting the library from the bundle (doc 02), the CLI was
still importing from `amplifier_core` in 38 places across 14 files — a
hard dependency on a package that no longer needs to exist.

## What the CLI actually used from amplifier-core

We grepped every Python file. The CLI imported 18 distinct symbols from 8
submodules:

| Submodule | Symbols | How used |
|-----------|---------|----------|
| `amplifier_core` (top-level) | `AmplifierSession`, `ModuleValidationError`, `ApprovalRequest`, `ApprovalResponse`, `ModelInfo` | Session lifecycle, approval UI, provider introspection |
| `amplifier_core.llm_errors` | `LLMError`, `AuthenticationError`, `ContentFilterError`, `ContextLengthError`, `RateLimitError` | Error display formatting |
| `amplifier_core.events` | `PROMPT_COMPLETE`, `SESSION_END` | Event hooks in the REPL loop |
| `amplifier_core.hooks` | `HookResult` | Incremental save, trace collection |
| `amplifier_core.models` | `HookResult` | Same symbol, different import path |
| `amplifier_core.loader` | `ModuleLoader` | Module discovery and loading |
| `amplifier_core.validation` | `ToolValidator`, `HookValidator`, `ContextValidator`, `OrchestratorValidator`, `ProviderValidator` | `amplifier module validate` command |
| `amplifier_core.approval` | `ApprovalTimeoutError` | Approval UI timeout handling |
| `amplifier_core.message_models` | `Message` | Mention loading (context injection) |

Of these, only `HookResult` and the two event constants already existed
in core-lite. Everything else was missing from the library.

## What we built

Six new modules in `amplifier_foundation/core/`, totaling ~550 new lines:

| Module | Lines | What it provides |
|--------|-------|------------------|
| `llm_errors.py` | 76 | `LLMError` base + 12 subclasses. Plain exceptions, zero deps. |
| `approval.py` | 31 | `ApprovalRequest`/`ApprovalResponse` dataclasses + `ApprovalTimeoutError`. |
| `message_models.py` | 89 | `Message` and `ChatRequest` Pydantic models + 7 content block types. |
| `loader.py` | 157 | `ModuleLoader` (entry-point + filesystem discovery) + `ModuleValidationError`. |
| `validation/__init__.py` | 206 | `ValidationResult` + base validator + 5 typed subclasses. |
| `models.py` (edit) | +11 | `ModelInfo` Pydantic model appended to existing file. |

The core-lite `__init__.py` was updated to re-export all 30+ symbols so
consumers can use `from amplifier_foundation.core import X` for anything.

### Design decisions

**Dataclasses over Pydantic for approval types.** `ApprovalRequest` and
`ApprovalResponse` are internal protocol types, not serialization boundaries.
Dataclasses avoid the Pydantic dependency for modules that only need the
approval protocol.

**Pydantic for Message and ModelInfo.** These cross serialization boundaries
(JSON to/from providers). The CLI already depends on Pydantic, and the library's
existing `HookResult`/`ToolResult` use Pydantic, so there's no new dependency.

**Simplified ModuleLoader.** The original was 728 lines with WASM/gRPC dispatch,
coordinator-injected source resolution, and `sys.path` management. Ours is 157
lines that does `importlib.metadata.entry_points` + `importlib.import_module`.
The WASM and gRPC code paths were eliminated in doc 00. If they come back,
they can be added as methods on this class without changing the interface.

**Simplified validators.** The originals were 5 files, ~2,100 lines total, with
~300 lines of copy-pasted boilerplate per validator. Ours is a single file with
a shared `_BaseValidator` (importable + mount exists + mount callable) and 5
one-line subclasses. The per-type protocol checks (e.g. "tool must have
`execute`") can be added later without changing the public API.

## The import rewrite

38 import sites across 14 files, mechanically rewritten:

```python
# Before
from amplifier_core import AmplifierSession
from amplifier_core.llm_errors import LLMError
from amplifier_core.events import PROMPT_COMPLETE

# After
from amplifier_foundation.runtime import Session as AmplifierSession
from amplifier_foundation.core.llm_errors import LLMError
from amplifier_foundation.core.events import PROMPT_COMPLETE
```

`AmplifierSession` maps to `amplifier_foundation.runtime.Session`, aliased to
preserve the name at all 6 call sites. Everything else maps to
`amplifier_foundation.core.<submodule>`.

Two logger name strings (`logging.getLogger("amplifier_core")`) were left as-is.
Logger names are conventions, not import dependencies.

One bare `import amplifier_core` in `commands/module.py` (used for
`amplifier_core.__file__` path introspection) was rewritten to
`import amplifier_foundation.core as amplifier_core`.

## The workspace

To avoid stale-copy issues during development, the monorepo now uses a uv
workspace:

```toml
# amplifier-sdk/pyproject.toml
[tool.uv.workspace]
members = ["amplifier-lib", "amplifier-app-cli"]

# amplifier-app-cli/pyproject.toml
[tool.uv.sources]
amplifier-foundation = { workspace = true }
```

Edits to `amplifier-lib` are immediately visible to the CLI without rebuilding.
`uv sync --package amplifier-app-cli` installs both as editable workspace
members into a shared `.venv`.

## The result

```
Before:
  amplifier-app-cli → amplifier-core (9,800 lines, Rust/WASM/gRPC, PyPI)
                     → amplifier-foundation (library)

After:
  amplifier-app-cli → amplifier-foundation (library, ~1,100 lines in core/)
                     (zero external kernel dependency)
```

520 CLI tests pass. 505 library tests pass. The `uv.lock` contains zero
references to `amplifier-core`. The `amplifier` CLI entry point imports
cleanly and runs against the local workspace.
