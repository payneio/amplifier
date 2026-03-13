# Splitting the Library from the Bundle

## The problem

`amplifier-foundation` was a monolith pretending to be two things at once:

1. A **Python library** — importable package (`amplifier_foundation/`) with
   bundle loading, session management, module discovery, caching, path
   resolution, and the absorbed core-lite.

2. A **bundle** — agent definitions, behavior configs, context documents,
   provider YAML, hook modules, and recipes that configure an Amplifier session
   at runtime.

These have different consumers, different change cadences, and different
dependency directions. The library is imported by Python code. The bundle is
loaded by the Amplifier runtime. Shipping them in one repo means every agent
description change drags along 10,000 lines of library code, and every library
bugfix risks touching bundle content that 15 downstream bundles compose.

## What's in each half

### Library: `amplifier-lib/` (53 Python files, ~10,000 lines)

The importable package. Everything here is `from amplifier_foundation import X`.

| Subpackage | Purpose | Lines |
|------------|---------|-------|
| `core/` | Absorbed core-lite: `HookResult`, `ToolResult`, `HookRegistry`, 35 event constants | ~485 |
| `runtime.py` | `Session`, `Coordinator`, module loader — the session lifecycle | ~576 |
| `bundle.py` | Bundle loading, frontmatter parsing, agent metadata extraction | — |
| `cache/` | Disk cache for cloned module sources | — |
| `discovery/` | Module and bundle discovery | — |
| `mentions/` | `@mention` parser, resolver, deduplicator | — |
| `modules/` | Module activator, install state tracking | — |
| `paths/` | Path construction, discovery, resolution | — |
| `session/` | Session capabilities, events, forking, slicing | — |
| `sources/` | Source resolution: git, file, http, zip | — |
| `io/` | File I/O, frontmatter, YAML utilities | — |
| `dicts/` | Dict merge and navigation helpers | — |
| `updates/` | Update checking | — |

Single external dependency: `pyyaml`. No `amplifier-core`.

505 tests pass. 22 test files. 508 test functions.

### Bundle: `amplifier-bundle-foundation/` (81 files, ~19,600 lines)

The runtime configuration. Nothing here is importable as a Python package.

| Directory | Contents | Count |
|-----------|----------|-------|
| `agents/` | Agent definitions (markdown + YAML frontmatter) | 16 |
| `behaviors/` | Behavior compositions (YAML) | 12 |
| `bundles/` | Bundle presets: minimal, with-anthropic, with-openai, amplifier-dev | 4 |
| `context/` | Philosophy docs, delegation instructions, ecosystem maps | 19 |
| `modules/` | Hook and tool modules (Python, but installed separately) | 5 |
| `providers/` | Provider configs: anthropic, openai variants | 5 |
| `recipes/` | Validation recipes | 4 |
| `bundle.md` | Root bundle manifest | 1 |

The 5 bundle modules (`hooks-deprecation`, `hooks-progress-monitor`,
`hooks-session-naming`, `hooks-todo-display`, `tool-delegate`) are Python, but
they're standalone packages with their own `pyproject.toml` — installed into the
runtime independently, not imported from the library. Their only library
dependency is `amplifier_foundation.core` (for `HookResult` and `ToolResult`).

## The dependency direction

```
amplifier-bundle-foundation
    │
    │  modules import from
    ▼
amplifier-lib (library)
    │
    │  uses
    ▼
pyyaml
```

The bundle depends on the library. The library knows nothing about the bundle.
This is the correct direction — configuration depends on infrastructure, not the
reverse.

## What changed in the split

### Removed from the library

Bundle artifacts that were sitting in the library's source tree:

- `agents/` (16 files) — agent definitions are bundle content
- `behaviors/` (12 files) — behavior configs are bundle content
- `bundles/` (4 files) — bundle presets are bundle content
- `context/` (19 files) — context documents are bundle content
- `modules/` (5 directories) — standalone module packages, not library code
- `providers/` (5 files) — provider configs are bundle content
- `recipes/` (4 files) — validation recipes are bundle content
- `bundle.md` — the bundle manifest itself

### Removed from the library's dependencies

```toml
# Before
dependencies = ["pyyaml>=6.0.3", "amplifier-core"]

# After
dependencies = ["pyyaml>=6.0.3"]
```

`amplifier-core` was dropped because core-lite (~485 lines) is absorbed into
`amplifier_foundation/core/`. There is no external kernel dependency.

### Removed from tests

Two test files tested bundle artifacts, not library code:

- `test_gpt54_provider_updates.py` — asserted provider YAML had correct
  `default_model` values. This is a bundle test, not a library test.
- `TestFoundationAgentModelRoles` in `test_agent_metadata.py` — loaded actual
  agent `.md` files from `agents/` and checked their `model_role` frontmatter.
  The unit tests for the metadata extraction function (using `tmp_path`) stayed.

One pre-existing bug was fixed: `test_install_state.py` was mocking
`os.path.getmtime` but the code uses `os.lstat`. The mock target was corrected.

### Fixed in amplifier-app-cli

```toml
# Before
dependencies = ["amplifier-core", "amplifier-foundation", ...]
amplifier-foundation = { git = "https://github.com/microsoft/amplifier-foundation", branch = "main" }

# After
dependencies = ["amplifier-foundation", ...]
amplifier-foundation = { path = "../amplifier-lib" }
```

Dropped `amplifier-core` (absorbed). Changed source from GitHub remote to local
monorepo path so local development changes are immediately visible.

## The result

```
amplifier-sdk/
├── amplifier-lib/                   Python library (importable)
│   ├── amplifier_foundation/          53 .py files, ~10,000 lines
│   ├── tests/                         505 passing, 3 skipped
│   └── pyproject.toml                 depends on: pyyaml
│
├── amplifier-bundle-foundation/     Bundle (runtime config)
│   ├── agents/                        16 agent definitions
│   ├── behaviors/                     12 behavior configs
│   ├── context/                       19 context documents
│   ├── modules/                       5 standalone module packages
│   └── bundle.md                      root manifest
│
├── amplifier-app-cli/               Reference CLI
│   └── pyproject.toml                 depends on: amplifier-foundation (local)
│
└── docs/                            Decision records (you are here)
```

The library has zero knowledge of what agents exist, what providers are
configured, or what context documents get injected. The bundle has zero
knowledge of how sessions are managed, how modules are loaded, or how sources
are resolved. Each can change without touching the other.
