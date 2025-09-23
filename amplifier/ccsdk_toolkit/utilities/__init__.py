"""
CCSDK Toolkit Utilities

Utility functions that enhance claude-code-sdk usage without wrapping.
These utilities work WITH the SDK, not around it.

Basic Usage:
    >>> from claude_code_sdk import ClaudeSDKClient
    >>> from amplifier.ccsdk_toolkit.utilities import query_with_retry
    >>>
    >>> client = ClaudeSDKClient()
    >>> response = await query_with_retry(client, "Hello")
"""

from .file_utils import ensure_data_dir
from .file_utils import load_conversation
from .file_utils import save_conversation
from .file_utils import save_response
from .progress_utils import ProgressTracker
from .progress_utils import SimpleProgressCallback
from .query_utils import batch_query
from .query_utils import extract_text_content
from .query_utils import parse_sdk_response
from .query_utils import query_with_retry

__all__ = [
    # Query utilities
    "query_with_retry",
    "parse_sdk_response",
    "batch_query",
    "extract_text_content",
    # File utilities
    "save_response",
    "load_conversation",
    "save_conversation",
    "ensure_data_dir",
    # Progress tracking
    "ProgressTracker",
    "SimpleProgressCallback",
]
