"""
Claude Code SDK Toolkit

A comprehensive toolkit for building robust applications with the Claude Code SDK.
Provides utilities, helpers, defensive patterns, and configuration management
for direct SDK usage.

Quick Start:
    >>> from claude_code_sdk import ClaudeSDKClient
    >>> from amplifier.ccsdk_toolkit.utilities import query_with_retry
    >>> from amplifier.ccsdk_toolkit.defensive import parse_llm_json, write_json_with_retry
    >>>
    >>> client = ClaudeSDKClient()
    >>> response = await query_with_retry(client, "Analyze this")
    >>> data = parse_llm_json(response.content)
    >>> write_json_with_retry(data, "results.json")

Modules:
    - utilities: Helper functions for direct SDK usage
    - helpers: High-level helpers using SDK via composition
    - context_managers: Context managers for common patterns
    - decorators: Useful decorators for SDK operations
    - defensive: Battle-tested utilities for LLM parsing and cloud-aware file I/O
    - config: Configuration management
    - sessions: Session state persistence
    - logger: Structured logging
    - cli: CLI tool builder
"""

# CLI building
from .cli import CliBuilder
from .cli import CliTemplate

# Configuration management
from .config import AgentConfig
from .config import AgentDefinition
from .config import ConfigLoader
from .config import EnvironmentConfig
from .config import MCPServerConfig
from .config import ToolConfig
from .config import ToolkitConfig
from .config import ToolPermissions

# Context managers for common patterns
from .context_managers import FileProcessor
from .context_managers import RetryContext
from .context_managers import RetryStrategy
from .context_managers import SessionContext
from .context_managers import StreamingQuery
from .context_managers import TimedExecution

# Defensive utilities (battle-tested)
from .defensive import extract_agent_output
from .defensive import isolate_prompt
from .defensive import parse_llm_json
from .defensive import read_json_with_retry
from .defensive import retry_with_feedback
from .defensive import write_json_with_retry

# Helper classes using SDK via composition
from .helpers import BatchProcessor
from .helpers import ConversationManager

# Structured logging
from .logger import LogEvent
from .logger import LogFormat
from .logger import LogLevel
from .logger import ToolkitLogger
from .logger import create_logger

# Session management (for persistence, not wrapping)
from .sessions import SessionManager
from .sessions import SessionMetadata
from .sessions import SessionState

# Utility functions for direct SDK usage
from .utilities import ProgressTracker
from .utilities import SimpleProgressCallback
from .utilities import batch_query
from .utilities import ensure_data_dir
from .utilities import extract_text_content
from .utilities import load_conversation
from .utilities import parse_sdk_response
from .utilities import query_with_retry
from .utilities import save_conversation
from .utilities import save_response

__version__ = "0.1.0"

__all__ = [
    # Utility functions for direct SDK usage
    "query_with_retry",
    "batch_query",
    "parse_sdk_response",
    "extract_text_content",
    "save_response",
    "load_conversation",
    "save_conversation",
    "ensure_data_dir",
    "ProgressTracker",
    "SimpleProgressCallback",
    # Helper classes using SDK via composition
    "ConversationManager",
    "BatchProcessor",
    # Context managers
    "FileProcessor",
    "StreamingQuery",
    "SessionContext",
    "TimedExecution",
    "RetryContext",
    "RetryStrategy",
    # Defensive utilities
    "parse_llm_json",
    "isolate_prompt",
    "retry_with_feedback",
    "extract_agent_output",
    "write_json_with_retry",
    "read_json_with_retry",
    # Configuration
    "AgentConfig",
    "AgentDefinition",
    "ToolConfig",
    "ToolkitConfig",
    "ToolPermissions",
    "MCPServerConfig",
    "EnvironmentConfig",
    "ConfigLoader",
    # Sessions (for persistence)
    "SessionManager",
    "SessionState",
    "SessionMetadata",
    # Logger
    "ToolkitLogger",
    "create_logger",
    "LogLevel",
    "LogFormat",
    "LogEvent",
    # CLI
    "CliBuilder",
    "CliTemplate",
]
