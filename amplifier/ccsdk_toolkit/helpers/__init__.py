"""CCSDK Toolkit Helpers Module

Optional helper classes for complex workflows that USE the SDK client
through composition rather than wrapping it.

These helpers provide convenience for common patterns while maintaining
clean separation from the core SDK.
"""

from .batch import BatchProcessor
from .conversation import ConversationManager
from .session import SessionManager

__all__ = [
    "ConversationManager",
    "BatchProcessor",
    "SessionManager",
]
