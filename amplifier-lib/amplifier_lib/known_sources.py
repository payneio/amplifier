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
#   - remote: Git URL for the bundle source
#   - show_in_list: Whether to show in default `bundle list` output

WELL_KNOWN_BUNDLES: dict[str, dict[str, str | bool]] = {
    "foundation": {
        "remote": "git+https://github.com/payneio/amplifier@main#subdirectory=bundles/foundation",
        "show_in_list": True,
    },
    "recipes": {
        "remote": "git+https://github.com/microsoft/amplifier-bundle-recipes@main",
        "show_in_list": False,
    },
    "design-intelligence": {
        "remote": "git+https://github.com/microsoft/amplifier-bundle-design-intelligence@main",
        "show_in_list": False,
    },
    "exp-delegation": {
        "remote": "git+https://github.com/payneio/amplifier@main#subdirectory=bundles/experiments/delegation-only",
        "show_in_list": True,
    },
    "amplifier-dev": {
        "remote": "git+https://github.com/payneio/amplifier@main#subdirectory=bundles/foundation/bundles/amplifier-dev.yaml",
        "show_in_list": True,
    },
    "notify": {
        "remote": "git+https://github.com/microsoft/amplifier-bundle-notify@main",
        "show_in_list": False,
    },
    "modes": {
        "remote": "git+https://github.com/microsoft/amplifier-bundle-modes@main",
        "show_in_list": False,
    },
    "distro": {
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
