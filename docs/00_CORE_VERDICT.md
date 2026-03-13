# core-lite: What's left after removing the reinvented parts

## The question

"Isn't amplifier-core just a reinvention of Python library management?"

## The answer

Mostly yes. Here's the accounting.

## What was dropped (reinventing Python)

| amplifier-core file | Lines | What it reinvents | Python equivalent |
|---------------------|-------|-------------------|-------------------|
| `coordinator.py` | 129 (original), 10 (current re-export) | A dict with named slots | `@dataclass` with 5 fields |
| `loader.py` | 267 (original), 728 (current) | Plugin discovery | `importlib.metadata.entry_points(group="amplifier.modules")` — one stdlib call |
| `interfaces.py` | 235 (original), 280 (current) | Interface contracts | `typing.Protocol` — just type declarations |
| `session.py` | 219 (original) | A for-loop that calls loader.load() then mount() | `async for module in config: await module.start()` |
| `loader_grpc.py` | 226 | Cross-language module loading | gRPC — a Google library, not a novel concept |
| `_grpc_gen/` | 1,761 | Generated protobuf stubs | `protoc` output |
| `_rust_wrappers.py` | 247 | Python shim over Rust reimplementation of coordinator | The coordinator was already 129 lines of Python |
| `_session_init.py` | 257 | Session init split out for Rust sharing | Artifact of the Rust rewrite |
| `_session_exec.py` | 98 | Thin bridge to Rust orchestrator.execute() | Artifact of the Rust rewrite |
| `validation/` | ~2,438 | Module contract validators | `isinstance()` checks or pytest |
| `pytest_plugin.py` | 594 | Test fixtures | Standard pytest plugin |
| `testing.py` | 194 | MockProvider, MockTool | Standard test mocks |
| `module_sources.py` | ~200 | Module source resolution | pip/uv already does this |
| `cli.py` | ~100 | CLI entry point | `argparse` / `click` |
| All Rust (`crates/`) | ~thousands | Rust reimplementation of the Python coordinator | The Python version was 129 lines |
| WASM (`wit/`) | ~hundreds | WASM interface types | A transport layer |
| Node bindings (`bindings/`) | ~hundreds | Node.js Napi-RS bindings | A language bridge |

**Total dropped: ~8,000+ lines of Python, plus all Rust/WASM/gRPC/Node.**

## What survived (3 files, ~420 lines)

### models.py (~130 lines) — Domain-specific data models

Two models with logic that Python's ecosystem doesn't hand you:

1. **`ToolResult`** — `_sanitize_for_llm()` strips control characters (\\x00-\\x1f)
   and lone UTF-16 surrogates that crash Anthropic's API with "Internal server
   error". `get_serialized_output()` serializes for LLM consumption.
   `model_post_init` auto-fills output from error when tool authors forget.
   These solve real operational bugs.

2. **`HookResult`** — A domain model for hooks participating in an LLM agent's
   cognitive loop. `inject_context` puts text into the agent's conversation.
   `ephemeral` makes it temporary. `ask_user` requests approval with timeout
   and safe defaults. `suppress_output` / `user_message` separate what the
   agent sees from what the user sees. No existing Python pub/sub library
   expresses this protocol.

### hooks.py (~190 lines) — Agent-specific emit semantics

The registry boilerplate is generic, but `emit()` has non-trivial semantics:

- **Action precedence**: `deny > ask_user > inject_context > modify > continue`.
  A security hook's deny must not be overridden by a later logging hook's continue.
- **Multi-inject merging**: Multiple hooks injecting context on the same event
  get concatenated, not clobbered.
- **Infrastructure fields**: session_id + timestamp stamped on every event for
  the session tree identity key.
- **CancelledError resilience**: Cancelled handlers don't skip remaining handlers
  on cleanup events.

### events.py (~90 lines) — Event vocabulary

35 named event constants. Not code — just strings. But the vocabulary IS the
contract that lets 15 modules from different authors interoperate without
coordinating on string literals.

## The ratio

```
amplifier-core total:  ~9,800 lines Python + Rust + WASM + gRPC + Node
core-lite total:       ~420 lines Python

Novel fraction:        ~4.3%
```

## The honest verdict

The original challenge was right. About 95% of amplifier-core is reimplementing
what Python already provides:

- Plugin discovery → `importlib.metadata.entry_points`
- Interface contracts → `typing.Protocol`
- Module registry → a dict (or dataclass)
- Session lifecycle → a for-loop over config entries
- Cross-language support → standard gRPC/WASM tooling

The ~5% that isn't reinventing Python is genuinely specific to LLM agent
orchestration:

- The hook result protocol (inject_context, ask_user, ephemeral, approval gates)
- The emit action precedence (deny > ask_user > inject_context > modify > continue)
- The LLM-safe serialization (control char stripping, surrogate removal)
- The event vocabulary as a cross-module contract

Whether that 5% justifies a standalone kernel is a design judgment call, not a
technical one. You could argue it belongs as a 400-line utility library rather
than a "kernel."
