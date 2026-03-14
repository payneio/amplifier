# Upstream-to-Monorepo Mapping Reference

## Repo Mapping Table

| Upstream Repo | Monorepo Location(s) | Notes |
|---------------|----------------------|-------|
| `microsoft/amplifier` | `docs/` (docs), `bundles/amplifier/` (bundle assets) | Simplest mapping |
| `microsoft/amplifier-core` | `amplifier-lib/amplifier_lib/core/` (~420 lines survived) | ~95% was eliminated (Rust, WASM, gRPC, coordinator, loader, session, validation) |
| `microsoft/amplifier-foundation` | `amplifier-lib/` (Python library) + `bundles/amplifier-bundle-foundation/` (bundle config) | Split into two halves |
| `microsoft/amplifier-app-cli` | `amplifier-cli/` | All `amplifier_core` imports rewritten to `amplifier_lib` |
| `microsoft/amplifierd` | `amplifierd/` | Still partially depends on PyPI `amplifier-core` (4 files not yet migrated) |

## Processing Order (dependency-first)

1. amplifier-core
2. amplifier-foundation
3. amplifier-app-cli
4. amplifierd
5. amplifier

## amplifier-core: What Was Eliminated vs Kept

### ELIMINATED (skip changes touching these)
- `coordinator.py` -- replaced by `amplifier_lib.runtime.Coordinator` (a dict with methods)
- `loader.py` (original 728-line version) -- replaced by 60-line loader in `runtime.py`
- `session.py` -- replaced by `amplifier_lib.runtime.Session`
- `interfaces.py` -- replaced by `typing.Protocol` declarations
- `_rust_wrappers.py`, `_session_init.py`, `_session_exec.py` -- Rust artifacts, eliminated
- `loader_grpc.py`, `_grpc_gen/` -- gRPC, eliminated
- `validation/` (~2,438 lines) -- simplified to ~206 lines in `amplifier_lib/core/validation/`
- `pytest_plugin.py`, `testing.py` -- test utilities, eliminated
- `module_sources.py`, `cli.py` -- eliminated
- All Rust (`crates/`), WASM (`wit/`), Node bindings (`bindings/`) -- eliminated entirely
- `pyproject.toml` version bumps, CI, release tooling -- not applicable

### KEPT (changes here may be relevant)
- `models.py` (~130 lines) -> `amplifier-lib/amplifier_lib/core/models.py` -- ToolResult, HookResult, ModelInfo
- `hooks.py` (~190 lines) -> `amplifier-lib/amplifier_lib/core/hooks.py` -- HookRegistry, emit semantics
- `events.py` (~90 lines) -> `amplifier-lib/amplifier_lib/core/events.py` -- 35 event constants

### ADDED (built during migration, not in upstream core)
- `amplifier_lib/core/llm_errors.py` -- LLMError hierarchy (76 lines)
- `amplifier_lib/core/approval.py` -- ApprovalRequest/Response (31 lines)
- `amplifier_lib/core/message_models.py` -- Message/ChatRequest (89 lines)
- `amplifier_lib/core/loader.py` -- simplified ModuleLoader (157 lines)
- `amplifier_lib/core/validation/` -- simplified validators (206 lines)

## amplifier-foundation: The Split

### Python code -> `amplifier-lib/amplifier_lib/`
- `bundle.py` -- bundle loading, frontmatter parsing
- `cache/` -- disk cache
- `discovery/` -- module/bundle discovery
- `mentions/` -- @mention resolution
- `modules/` -- module activator
- `paths/` -- path utilities
- `session/` -- session capabilities
- `sources/` -- source resolution (git, file, http, zip)
- `io/` -- file I/O, YAML
- `dicts/` -- dict helpers
- `updates/` -- update checking
- `runtime.py` -- Session, Coordinator, module loader (absorbed from core)

### Bundle config -> `bundles/amplifier-bundle-foundation/`
- `agents/` (16 files) -- agent definitions
- `behaviors/` (12 files) -- behavior configs
- `bundles/` (4 files) -- bundle presets
- `context/` (19 files) -- philosophy docs, delegation instructions
- `modules/` (5 dirs) -- standalone hook/tool modules with own pyproject.toml
- `providers/` (5 files) -- provider configs
- `recipes/` (4 files) -- validation recipes
- `bundle.md` -- root manifest

## amplifier-app-cli: Import Translation

| Old Import | New Import |
|------------|-----------|
| `from amplifier_core import AmplifierSession` | `from amplifier_lib.runtime import Session as AmplifierSession` |
| `from amplifier_core.llm_errors import *` | `from amplifier_lib.core.llm_errors import *` |
| `from amplifier_core.events import *` | `from amplifier_lib.core.events import *` |
| `from amplifier_core.hooks import HookResult` | `from amplifier_lib.core import HookResult` |
| `from amplifier_core.loader import ModuleLoader` | `from amplifier_lib.core.loader import ModuleLoader` |
| `from amplifier_core.validation import *Validator` | `from amplifier_lib.core.validation import *Validator` |
| `from amplifier_core.approval import *` | `from amplifier_lib.core.approval import *` |
| `from amplifier_core.message_models import Message` | `from amplifier_lib.core.message_models import Message` |

## amplifierd: Partial Migration

Still imports from PyPI `amplifier_core` in 4 files:
- `persistence.py`
- `errors.py`
- `routes/health.py`
- `state/session_handle.py`

Also uses `amplifier_lib` for other functionality. Dual-dependency situation.
