"""Well-known bundle and provider source registries.

Single source of truth for canonical bundle names, provider git URLs,
and provider dependency ordering. Apps import these rather than
maintaining their own copies.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Well-known bundles
# ---------------------------------------------------------------------------
# Each entry maps bundle name -> info dict with:
#   - package: Python package name (for local editable install check)
#   - remote: Git URL (fallback when package not installed)
#   - show_in_list: Whether to show in default `bundle list` output

WELL_KNOWN_BUNDLES: dict[str, dict[str, str | bool]] = {
    "foundation": {
        "package": "amplifier_lib",
        "remote": "git+https://github.com/microsoft/amplifier-foundation@main",
        "show_in_list": True,
    },
    "recipes": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-bundle-recipes@main",
        "show_in_list": False,
    },
    "design-intelligence": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-bundle-design-intelligence@main",
        "show_in_list": False,
    },
    "exp-delegation": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=experiments/delegation-only",
        "show_in_list": True,
    },
    "amplifier-dev": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/amplifier-dev.yaml",
        "show_in_list": True,
    },
    "notify": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-bundle-notify@main",
        "show_in_list": False,
    },
    "modes": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-bundle-modes@main",
        "show_in_list": False,
    },
    "distro": {
        "package": "",
        "remote": "git+https://github.com/microsoft/amplifier-bundle-distro@main",
        "show_in_list": False,
    },
}

# ---------------------------------------------------------------------------
# Well-known provider module sources
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER_SOURCES: dict[str, str] = {
    "provider-anthropic": "git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
    "provider-azure-openai": "git+https://github.com/microsoft/amplifier-module-provider-azure-openai@main",
    "provider-gemini": "git+https://github.com/microsoft/amplifier-module-provider-gemini@main",
    "provider-github-copilot": "git+https://github.com/microsoft/amplifier-module-provider-github-copilot@main",
    "provider-ollama": "git+https://github.com/microsoft/amplifier-module-provider-ollama@main",
    "provider-openai": "git+https://github.com/microsoft/amplifier-module-provider-openai@main",
    "provider-vllm": "git+https://github.com/microsoft/amplifier-module-provider-vllm@main",
}

# Runtime dependencies between providers (topological ordering for install).
PROVIDER_DEPENDENCIES: dict[str, list[str]] = {
    "provider-azure-openai": ["provider-openai"],
}
