"""Bundle loading utilities for CLI app layer.

Implements app-specific bundle discovery and loading policy.

This module bridges CLI-specific discovery (search paths, packaged bundles)
with foundation's bundle preparation workflow (load → compose → prepare → create_session).
"""

# Foundation imports (third-party) - sorted alphabetically
from amplifier_lib import Bundle
from amplifier_lib import BundleRegistry
from amplifier_lib import load_bundle
from amplifier_lib.bundle import BundleModuleResolver
from amplifier_lib.bundle import PreparedBundle

# Local imports
from amplifier_cli.lib.bundle_loader import user_registry
from amplifier_cli.lib.bundle_loader.discovery import AppBundleDiscovery
from amplifier_cli.lib.bundle_loader.prepare import load_and_prepare_bundle
from amplifier_cli.lib.bundle_loader.resolvers import AppModuleResolver

__all__ = [
    # CLI-specific
    "AppBundleDiscovery",
    "AppModuleResolver",
    "load_and_prepare_bundle",
    "user_registry",
    # Foundation re-exports
    "Bundle",
    "BundleModuleResolver",
    "BundleRegistry",
    "PreparedBundle",
    "load_bundle",
]
