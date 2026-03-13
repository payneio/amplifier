# amplifier-lib

Core Python library for the Amplifier ecosystem: bundle composition, session runtime, module management, and utilities.

amplifier-lib provides:
- **Bundle System** - Load, compose, validate, and resolve bundles from local and remote sources
- **Session Runtime** - Session lifecycle, coordinator, and module mounting
- **Module Activation** - Download, install, and import modules from git/file/HTTP URIs at runtime
- **@Mention System** - Parse and resolve `@namespace:path` references in instructions
- **Source Resolution** - Pluggable handlers for git, file, HTTP, and zip sources with update detection
- **Session Utilities** - Fork, slice, repair, and inspect conversation history
- **Core Types** - Domain models, hook registry, LLM error hierarchy, approval system, module validation
- **Utilities** - YAML/frontmatter I/O, dict merging, path handling, caching, serialization, tracing

## Quick Start

```bash
pip install git+https://github.com/microsoft/amplifier-foundation
```

### Load, Compose, and Execute

```python
import asyncio
from amplifier_lib import load_bundle

async def main():
    # Load a bundle and a provider
    base = await load_bundle("git+https://github.com/microsoft/amplifier-foundation@main")
    provider = await load_bundle("./providers/anthropic.yaml")

    # Compose bundles (later overrides earlier)
    composed = base.compose(provider)

    # Prepare: resolves module sources, downloads if needed
    prepared = await composed.prepare()

    # Create session and execute
    async with await prepared.create_session() as session:
        response = await session.execute("Hello! What can you help me with?")
        print(response)

asyncio.run(main())
```

### Use Utilities Directly

```python
from amplifier_lib import (
    # I/O
    read_yaml, write_yaml, parse_frontmatter, read_with_retry, write_with_retry,
    # Dict operations
    deep_merge, merge_module_lists, get_nested, set_nested,
    # Path handling
    parse_uri, normalize_path, find_files, find_bundle_root,
    # @Mentions
    parse_mentions, load_mentions,
    # Caching
    SimpleCache, DiskCache,
    # Session capabilities
    get_working_dir, set_working_dir, WORKING_DIR_CAPABILITY,
)

# Parse git URIs
parsed = parse_uri("git+https://github.com/org/repo@main#subdirectory=bundles/dev")
# -> ParsedURI(scheme='git+https', host='github.com', path='/org/repo', ref='main', subpath='bundles/dev')

# Deep merge dicts (later wins)
result = deep_merge(base_config, overlay_config)

# Parse markdown frontmatter
frontmatter, body = parse_frontmatter(markdown_content)

# Find files recursively
md_files = find_files(Path("docs"), "**/*.md")
```

## What's Included

### Bundle System (`bundle.py`, `registry.py`, `validator.py`)

The central concept. Bundles are composable configuration packages (YAML/Markdown with frontmatter) that declare providers, tools, agents, hooks, and context.

| Export | Purpose |
|--------|---------|
| `Bundle` | Core class - load, compose, validate, prepare bundles |
| `load_bundle(uri)` | Load bundle from local path, git URL, HTTP, or zip |
| `BundleRegistry` | Track loaded bundles, manage state and updates |
| `validate_bundle()` | Validate bundle structure and references |
| `BundleValidator` | Configurable validation with `ValidationResult` |

### Session Runtime (`runtime.py`)

The session lifecycle engine that modules mount into.

| Export | Purpose |
|--------|---------|
| `AmplifierSession` | Session lifecycle: initialize, execute, cleanup (async context manager) |
| `Coordinator` | Module registry with mount points for providers, tools, hooks, orchestrators, context |
| `CancellationToken` | Cooperative cancellation for sessions and tools |

### Core Types (`core/`)

Domain-specific types used across the ecosystem.

| Category | Exports | Purpose |
|----------|---------|---------|
| Models | `HookResult`, `ToolResult`, `ModelInfo`, `Message`, `ChatRequest` | Data contracts for modules |
| Hooks | `HookRegistry` | Event emission with action precedence |
| LLM Errors | `RateLimitError`, `AuthenticationError`, `ContextLengthError`, `ContentFilterError`, `QuotaExceededError`, `StreamError`, etc. | Typed error hierarchy for provider failures |
| Approval | `ApprovalRequest`, `ApprovalResponse`, `ApprovalTimeoutError` | Human-in-the-loop gates |
| Loader | `ModuleLoader`, `ModuleInfo`, `ModuleValidationError` | Module discovery and loading |
| Validation | `ProviderValidator`, `ToolValidator`, `HookValidator`, `OrchestratorValidator`, `ContextValidator` | Per-module-type validation |

### Module Activation (`modules/`)

Download and import modules at runtime.

| Export | Purpose |
|--------|---------|
| `ModuleActivator` | Download modules from URIs, install dependencies (via uv/pip), add to `sys.path` |
| `InstallStateManager` | Track installed modules to avoid redundant work |

### Source Resolution (`sources/`)

Pluggable system for resolving URIs to local paths with update detection.

| Export | Purpose |
|--------|---------|
| `SimpleSourceResolver` | Default resolver with built-in handlers |
| `GitSourceHandler` | Clone/shallow-fetch git repos, update detection via `git ls-remote` |
| `FileSourceHandler` | Resolve `file://` and local paths |
| `HttpSourceHandler` | Download from HTTP/HTTPS URLs |
| `ZipSourceHandler` | Extract zip archives |
| `SourceStatus` | Rich status: cached commit, remote commit, pinned detection |
| `SourceResolverProtocol` | Protocol for custom resolver implementations |

### Session Utilities (`session/`)

Fork, slice, and inspect conversation history.

| Export | Purpose |
|--------|---------|
| `fork_session`, `fork_session_in_memory` | Create new sessions from existing ones at a specific turn |
| `get_fork_preview`, `list_session_forks`, `get_session_lineage` | Inspect fork relationships |
| `slice_to_turn`, `get_turn_boundaries`, `count_turns` | Slice conversation history by turn |
| `find_orphaned_tool_calls`, `add_synthetic_tool_results` | Repair corrupted transcripts |
| `slice_events_to_timestamp`, `count_events`, `get_event_summary` | Work with `events.jsonl` logs |
| `get_working_dir`, `set_working_dir` | Session capability helpers for modules |

### @Mention System (`mentions/`)

| Export | Purpose |
|--------|---------|
| `parse_mentions(text)` | Extract `@namespace:path` references |
| `load_mentions(text, resolver)` | Resolve and load mentioned files |
| `BaseMentionResolver` | Base class for custom resolvers |
| `ContentDeduplicator` | Prevent duplicate content loading |

### Bundle Updates (`updates/`)

| Export | Purpose |
|--------|---------|
| `check_bundle_status(bundle)` | Non-destructive check for available updates across all sources |
| `update_bundle(bundle)` | Re-download and reinstall updated sources |
| `BundleStatus` | Aggregate update information |

### Spawn Utilities (`spawn_utils.py`)

| Export | Purpose |
|--------|---------|
| `apply_provider_preferences` | Resolve provider/model preferences with glob pattern matching |
| `resolve_model_pattern` | Match model names against glob patterns |
| `ProviderPreference`, `ModelResolutionResult` | Data types for preference resolution |

### Utilities

| Module | Exports | Purpose |
|--------|---------|---------|
| `io/` | `read_yaml`, `write_yaml`, `parse_frontmatter`, `read_with_retry`, `write_with_retry`, `write_with_backup` | File I/O with cloud sync retry |
| `dicts/` | `deep_merge`, `merge_module_lists`, `get_nested`, `set_nested` | Dict manipulation |
| `paths/` | `parse_uri`, `normalize_path`, `find_files`, `find_bundle_root`, `construct_agent_path`, `construct_context_path` | Path and URI handling |
| `cache/` | `SimpleCache`, `DiskCache`, `CacheProviderProtocol` | In-memory and disk caching (apps can extend) |
| `serialization.py` | `sanitize_for_json`, `sanitize_message` | Safe JSON serialization |
| `tracing.py` | `generate_sub_session_id` | Correlated tracing across parent/child sessions |

### Developer Tooling (`scripts/`)

| Script | Purpose |
|--------|---------|
| `session-repair.py` | Repair corrupted session transcripts (orphaned tool calls, ordering violations) |
| `lint_observability.py` | Lint modules for observability issues (unregistered events, fire-and-forget) |
| `generate_event_dot.py` | Generate Graphviz DOT diagrams of event flows |

## Examples

| Example | Description |
|---------|-------------|
| `01_hello_world.py` | Minimal working example |
| `03_custom_tool.py` | Building custom tools |
| `04_load_and_inspect.py` | Loading bundles from various sources |
| `05_composition.py` | Bundle composition and merge rules |
| `06_sources_and_registry.py` | Git URLs and BundleRegistry |
| `07_full_workflow.py` | Complete: prepare -> create_session -> execute |
| `09_multi_agent_system.py` | Multi-agent orchestration |
| `12_approval_gates.py` | Human-in-the-loop approval |
| `14_session_persistence.py` | Session save and resume |
| `17_multi_model_ensemble.py` | Multi-provider ensembles |
| `18_custom_hooks.py` | Hook implementation patterns |
| `22_custom_orchestrator_routing.py` | Custom orchestrator routing |

See [`examples/README.md`](examples/README.md) for the full catalog of 20+ examples.

Jupyter notebooks covering the same topics are in [`notebooks/`](notebooks/).

## Documentation

| Document | Description |
|----------|-------------|
| [BUNDLE_GUIDE.md](docs/BUNDLE_GUIDE.md) | Complete bundle authoring guide |
| [AGENT_AUTHORING.md](docs/AGENT_AUTHORING.md) | Agent creation and context sink pattern |
| [CONCEPTS.md](docs/CONCEPTS.md) | Mental model: bundles, composition, mount plans |
| [PATTERNS.md](docs/PATTERNS.md) | Common patterns with code examples |
| [URI_FORMATS.md](docs/URI_FORMATS.md) | Source URI quick reference |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API index pointing to source files |
| [DOMAIN_VALIDATOR_GUIDE.md](docs/DOMAIN_VALIDATOR_GUIDE.md) | Domain-specific validation |
| [POLICY_BEHAVIORS.md](docs/POLICY_BEHAVIORS.md) | Policy behavior patterns |
| [APPLICATION_INTEGRATION_GUIDE.md](docs/APPLICATION_INTEGRATION_GUIDE.md) | Embedding amplifier-lib in your own app |

**Code is authoritative**: Each source file has comprehensive docstrings. Use `help(ClassName)` or read source directly.

## Philosophy

This library follows Amplifier's core principles:

- **Mechanism, not policy**: Provides loading, composition, and runtime mechanisms. Apps decide which bundles to use, where settings live, and how users interact.
- **Ruthless simplicity**: One concept (bundle), one composition mechanism (`includes:` + `compose()`). Only one dependency (`pyyaml`).
- **Text-first**: YAML/Markdown formats are human-readable, diffable, versionable.
- **Composable**: Small bundles compose into larger configurations. Small modules plug into coordinators.

This library is pure mechanism. It doesn't know about specific bundles, user preferences, or filesystem conventions. Apps (like amplifier-cli) layer policy on top.

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
