"""Context managers for Claude Code SDK - focused, single-purpose managers.

This module provides specialized context managers for common patterns when
working with the Claude Code SDK. Each manager has a single, well-defined
purpose and integrates cleanly with the SDK's utilities and helpers.

Available Context Managers:
    - FileProcessor: Batch file processing with progress tracking
    - StreamingQuery: Streaming responses with progress indicators
    - SessionContext: Conversation session management with persistence
    - TimedExecution: Execution timing and timeout handling
    - RetryContext: Configurable retry strategies with error recovery
"""

from amplifier.ccsdk_toolkit.context_managers.file_processing import FileProcessor
from amplifier.ccsdk_toolkit.context_managers.retry_context import RetryContext
from amplifier.ccsdk_toolkit.context_managers.retry_context import RetryStrategy
from amplifier.ccsdk_toolkit.context_managers.session_context import SessionContext
from amplifier.ccsdk_toolkit.context_managers.streaming import StreamingQuery
from amplifier.ccsdk_toolkit.context_managers.timed_execution import TimedExecution

__all__ = [
    "FileProcessor",
    "StreamingQuery",
    "SessionContext",
    "TimedExecution",
    "RetryContext",
    "RetryStrategy",
]

__version__ = "1.0.0"
