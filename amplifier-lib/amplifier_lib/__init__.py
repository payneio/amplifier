"""Amplifier Foundation - Bundle composition and session runtime.

Provides bundle composition, session lifecycle, and the core types for
LLM agent orchestration.

Core concepts:
- Bundle = composable unit that produces mount plans
- AmplifierSession = session lifecycle (initialize, execute, cleanup)
- Coordinator = module registry with mount points, capabilities, and hooks
- core/ = domain-specific types (HookResult, ToolResult, HookRegistry, events)

Composition: `includes:` (declarative) + `compose()` (imperative)

Philosophy: Mechanism not policy, ruthless simplicity.

Note: This library is PURE MECHANISM. It loads bundles from URIs without
knowing about any specific bundle (including "foundation"). The foundation
bundle content co-located in this repo is just content - it's discovered
and loaded the same way any other bundle would be.
"""

from __future__ import annotations

# Core classes
from amplifier_lib.bundle import Bundle

# Config utilities
from amplifier_lib.config import expand_env_vars

# Reference implementations
from amplifier_lib.cache.disk import DiskCache

# Protocols
from amplifier_lib.cache.protocol import CacheProviderProtocol
from amplifier_lib.cache.simple import SimpleCache

# Dict utilities
from amplifier_lib.dicts.merge import deep_merge
from amplifier_lib.dicts.merge import merge_module_lists
from amplifier_lib.dicts.navigation import get_nested
from amplifier_lib.dicts.navigation import set_nested

# Exceptions
from amplifier_lib.exceptions import BundleDependencyError
from amplifier_lib.exceptions import BundleError
from amplifier_lib.exceptions import BundleLoadError
from amplifier_lib.exceptions import BundleNotFoundError
from amplifier_lib.exceptions import BundleValidationError

# I/O utilities
from amplifier_lib.io.files import read_with_retry
from amplifier_lib.io.files import write_with_backup
from amplifier_lib.io.files import write_with_retry
from amplifier_lib.io.frontmatter import parse_frontmatter
from amplifier_lib.io.yaml import read_yaml
from amplifier_lib.io.yaml import write_yaml

# Mention utilities
from amplifier_lib.mentions.deduplicator import ContentDeduplicator
from amplifier_lib.mentions.loader import load_mentions
from amplifier_lib.mentions.models import ContextFile
from amplifier_lib.mentions.models import MentionResult
from amplifier_lib.mentions.parser import parse_mentions
from amplifier_lib.mentions.protocol import MentionResolverProtocol
from amplifier_lib.mentions.resolver import BaseMentionResolver

# Path utilities
from amplifier_lib.paths.construction import construct_agent_path
from amplifier_lib.paths.construction import construct_context_path
from amplifier_lib.paths.discovery import find_bundle_root
from amplifier_lib.paths.discovery import find_files
from amplifier_lib.paths.resolution import ParsedURI
from amplifier_lib.paths.resolution import normalize_path
from amplifier_lib.paths.resolution import parse_uri
from amplifier_lib.registry import BundleRegistry
from amplifier_lib.registry import BundleState
from amplifier_lib.registry import UpdateInfo
from amplifier_lib.registry import load_bundle

# Serialization utilities
from amplifier_lib.serialization import sanitize_for_json
from amplifier_lib.serialization import sanitize_message

# Spawn utilities
from amplifier_lib.spawn_utils import ModelResolutionResult
from amplifier_lib.spawn_utils import ProviderPreference
from amplifier_lib.spawn_utils import apply_provider_preferences
from amplifier_lib.spawn_utils import apply_provider_preferences_with_resolution
from amplifier_lib.spawn_utils import is_glob_pattern
from amplifier_lib.spawn_utils import resolve_model_pattern
from amplifier_lib.sources.protocol import SourceHandlerProtocol
from amplifier_lib.sources.protocol import SourceHandlerWithStatusProtocol
from amplifier_lib.sources.protocol import SourceResolverProtocol
from amplifier_lib.sources.protocol import SourceStatus
from amplifier_lib.sources.resolver import SimpleSourceResolver

# Tracing utilities
from amplifier_lib.tracing import generate_sub_session_id

# Session capability helpers (for modules to access session context)
from amplifier_lib.session.capabilities import get_working_dir
from amplifier_lib.session.capabilities import set_working_dir
from amplifier_lib.session.capabilities import WORKING_DIR_CAPABILITY

# Updates - bundle update checking and updating
from amplifier_lib.updates import BundleStatus
from amplifier_lib.updates import check_bundle_status
from amplifier_lib.updates import update_bundle
from amplifier_lib.validator import BundleValidator
from amplifier_lib.validator import ValidationResult
from amplifier_lib.validator import validate_bundle
from amplifier_lib.validator import validate_bundle_or_raise

__all__ = [
    # Config
    "expand_env_vars",
    # Core
    "Bundle",
    "BundleRegistry",
    "BundleState",
    "UpdateInfo",
    "BundleValidator",
    "ValidationResult",
    "load_bundle",
    "validate_bundle",
    "validate_bundle_or_raise",
    # Exceptions
    "BundleError",
    "BundleNotFoundError",
    "BundleLoadError",
    "BundleValidationError",
    "BundleDependencyError",
    # Protocols
    "MentionResolverProtocol",
    "SourceResolverProtocol",
    "SourceHandlerProtocol",
    "SourceHandlerWithStatusProtocol",
    "SourceStatus",
    "CacheProviderProtocol",
    # Updates
    "BundleStatus",
    "check_bundle_status",
    "update_bundle",
    # Reference implementations
    "BaseMentionResolver",
    "SimpleSourceResolver",
    "SimpleCache",
    "DiskCache",
    # Mentions
    "parse_mentions",
    "load_mentions",
    "ContentDeduplicator",
    "ContextFile",
    "MentionResult",
    # I/O
    "read_yaml",
    "write_yaml",
    "parse_frontmatter",
    "read_with_retry",
    "write_with_retry",
    "write_with_backup",
    # Serialization
    "sanitize_for_json",
    "sanitize_message",
    # Tracing
    "generate_sub_session_id",
    # Dicts
    "deep_merge",
    "merge_module_lists",
    "get_nested",
    "set_nested",
    # Paths
    "parse_uri",
    "ParsedURI",
    "normalize_path",
    "construct_agent_path",
    "construct_context_path",
    "find_files",
    "find_bundle_root",
    # Session capabilities
    "get_working_dir",
    "set_working_dir",
    "WORKING_DIR_CAPABILITY",
    # Spawn utilities
    "ProviderPreference",
    "ModelResolutionResult",
    "apply_provider_preferences",
    "apply_provider_preferences_with_resolution",
    "is_glob_pattern",
    "resolve_model_pattern",
]
