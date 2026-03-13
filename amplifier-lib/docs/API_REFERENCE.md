# API Reference

The amplifier-lib API is fully documented via Python docstrings and type hints. This overview lists what's exported; for details, read the source files directly.

**Why this approach?** Documentation that duplicates code becomes context poisoning when it drifts. The code IS the authoritative reference.

## Quick Import

```python
from amplifier_lib import Bundle, BundleRegistry, load_bundle
from amplifier_lib.runtime import AmplifierSession, Coordinator
from amplifier_lib.core import HookResult, ToolResult, HookRegistry
```

## Runtime (`amplifier_lib.runtime`)

Session lifecycle and module coordination.

| Export | Purpose |
|--------|---------|
| `AmplifierSession` | Session lifecycle: initialize, execute, cleanup |
| `Coordinator` | Module registry with mount points, capabilities, and hooks |
| `CancellationToken` | Cooperative cancellation flag for sessions |

## Core Types (`amplifier_lib.core`)

Domain-specific types for LLM agent orchestration.

| Export | Source | Purpose |
|--------|--------|---------|
| `HookResult` | `core/models.py` | Hook action protocol (inject_context, ask_user, deny, etc.) |
| `ToolResult` | `core/models.py` | Tool execution result with LLM-safe serialization |
| `ModelInfo` | `core/models.py` | Provider model metadata |
| `HookRegistry` | `core/hooks.py` | Event registry with action precedence (deny > ask_user > inject > continue) |
| `Message` | `core/message_models.py` | Chat message model |
| `ChatRequest` | `core/message_models.py` | Chat completion request model |
| `ApprovalRequest` | `core/approval.py` | Approval protocol request |
| `ApprovalResponse` | `core/approval.py` | Approval protocol response |
| `ApprovalTimeoutError` | `core/approval.py` | Approval timeout exception |
| `LLMError` | `core/llm_errors.py` | Base LLM error (12 subclasses: `RateLimitError`, `AuthenticationError`, etc.) |
| `ModuleLoader` | `core/loader.py` | Entry-point + filesystem module discovery |
| `ModuleValidationError` | `core/loader.py` | Module loading validation error |
| `ToolValidator` | `core/validation/` | Tool module contract validator |
| `ProviderValidator` | `core/validation/` | Provider module contract validator |
| `HookValidator` | `core/validation/` | Hook module contract validator |
| `OrchestratorValidator` | `core/validation/` | Orchestrator module contract validator |
| `ContextValidator` | `core/validation/` | Context module contract validator |

Event constants (35 named events) are in `amplifier_lib.core.events`.

## Bundle Classes

| Export | Source | Purpose |
|--------|--------|---------|
| `Bundle` | `bundle.py` | Composable unit with mount plan config |
| `BundleRegistry` | `registry.py` | Named bundle management and loading |
| `BundleValidator` | `validator.py` | Bundle structure validation |
| `ValidationResult` | `validator.py` | Validation result with errors/warnings |
| `BundleState` | `registry.py` | Tracked state for loaded bundles |
| `UpdateInfo` | `registry.py` | Available update information |

## Convenience Functions

| Export | Source | Purpose |
|--------|--------|---------|
| `load_bundle` | `registry.py` | Load bundle from URI |
| `validate_bundle` | `validator.py` | Validate bundle, return result |
| `validate_bundle_or_raise` | `validator.py` | Validate bundle, raise on error |

## Exceptions

| Export | Source | Purpose |
|--------|--------|---------|
| `BundleError` | `exceptions.py` | Base exception |
| `BundleNotFoundError` | `exceptions.py` | Bundle not found |
| `BundleLoadError` | `exceptions.py` | Bundle load/parse failed |
| `BundleValidationError` | `exceptions.py` | Validation failed |
| `BundleDependencyError` | `exceptions.py` | Dependency resolution failed |

## Protocols

| Export | Source | Purpose |
|--------|--------|---------|
| `MentionResolverProtocol` | `mentions/protocol.py` | @mention resolution contract |
| `SourceResolverProtocol` | `sources/protocol.py` | URI resolution contract |
| `SourceHandlerProtocol` | `sources/protocol.py` | Source type handler contract |
| `CacheProviderProtocol` | `cache/protocol.py` | Cache provider contract |

## Reference Implementations

| Export | Source | Purpose |
|--------|--------|---------|
| `BaseMentionResolver` | `mentions/resolver.py` | Default @mention resolver |
| `SimpleSourceResolver` | `sources/resolver.py` | Git/file source resolver |
| `SimpleCache` | `cache/simple.py` | In-memory cache |
| `DiskCache` | `cache/disk.py` | Persistent disk cache |

## Mentions

| Export | Source | Purpose |
|--------|--------|---------|
| `parse_mentions` | `mentions/parser.py` | Extract @mentions from text |
| `load_mentions` | `mentions/loader.py` | Load @mention content (async) |
| `ContentDeduplicator` | `mentions/deduplicator.py` | SHA-256 content deduplication |
| `ContextFile` | `mentions/models.py` | Loaded context file data |
| `MentionResult` | `mentions/models.py` | @mention resolution result |

## I/O Utilities

| Export | Source | Purpose |
|--------|--------|---------|
| `read_yaml` | `io/yaml.py` | Read YAML file (async) |
| `write_yaml` | `io/yaml.py` | Write YAML file (async) |
| `parse_frontmatter` | `io/frontmatter.py` | Parse YAML frontmatter |
| `read_with_retry` | `io/files.py` | Read with cloud sync retry (async) |
| `write_with_retry` | `io/files.py` | Write with cloud sync retry (async) |

## Dict Utilities

| Export | Source | Purpose |
|--------|--------|---------|
| `deep_merge` | `dicts/merge.py` | Deep merge dictionaries |
| `merge_module_lists` | `dicts/merge.py` | Merge module lists by ID |
| `get_nested` | `dicts/navigation.py` | Get nested dict value by path |
| `set_nested` | `dicts/navigation.py` | Set nested dict value by path |

## Path Utilities

| Export | Source | Purpose |
|--------|--------|---------|
| `parse_uri` | `paths/resolution.py` | Parse source URI |
| `ParsedURI` | `paths/resolution.py` | Parsed URI dataclass |
| `normalize_path` | `paths/resolution.py` | Normalize/resolve path |
| `construct_agent_path` | `paths/construction.py` | Build agent file path |
| `construct_context_path` | `paths/construction.py` | Build context file path |
| `find_files` | `paths/discovery.py` | Find files by pattern (async) |
| `find_bundle_root` | `paths/discovery.py` | Find bundle root upward (async) |

## Session Capabilities

| Export | Source | Purpose |
|--------|--------|---------|
| `get_working_dir` | `session/capabilities.py` | Get session working directory from coordinator |
| `set_working_dir` | `session/capabilities.py` | Update session working directory dynamically |
| `WORKING_DIR_CAPABILITY` | `session/capabilities.py` | Capability name constant (`"session.working_dir"`) |

## Spawn Utilities

Utilities for spawning sub-sessions with provider/model preferences.

| Export | Source | Purpose |
|--------|--------|---------|
| `ProviderPreference` | `spawn_utils.py` | Dataclass for provider/model preference (supports glob patterns) |
| `apply_provider_preferences` | `spawn_utils.py` | Apply ordered preferences to mount plan |
| `resolve_model_pattern` | `spawn_utils.py` | Resolve glob patterns (e.g., `claude-haiku-*`) to concrete model names |
| `is_glob_pattern` | `spawn_utils.py` | Check if model string contains glob characters |

## Reading the Source

Each source file has comprehensive docstrings. To read them:

```bash
# In your editor
code amplifier_lib/bundle.py

# Or via Python
python -c "from amplifier_lib import Bundle; help(Bundle)"

# Or via pydoc
python -m pydoc amplifier_lib.Bundle
```

## Common Patterns

### Load and Use a Bundle

```python
from amplifier_lib import load_bundle

bundle = await load_bundle("git+https://github.com/org/my-bundle@main")
mount_plan = bundle.to_mount_plan()
```

### Compose Bundles

```python
from amplifier_lib import load_bundle

base = await load_bundle("foundation")
overlay = await load_bundle("./local-overlay.md")
composed = base.compose(overlay)
```

### Registry Management

```python
from amplifier_lib import BundleRegistry

registry = BundleRegistry()
registry.register({"my-bundle": "git+https://github.com/org/bundle@main"})
bundle = await registry.load("my-bundle")
```

### Load @Mentions

```python
from amplifier_lib import load_mentions, BaseMentionResolver

resolver = BaseMentionResolver(bundles={"foundation": foundation_bundle})
results = await load_mentions("See @foundation:context/guidelines.md", resolver)
```
