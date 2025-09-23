"""
CCSDK Toolkit Decorators

Composable decorators that enhance functions working with Claude Code SDK clients.
These decorators add capabilities without modifying the SDK itself.

Basic Usage:
    from amplifier.ccsdk_toolkit.decorators import with_retry, with_logging

    @with_retry(attempts=3)
    @with_logging()
    async def analyze_code(client, code: str):
        return await client.query(f"Analyze: {code}")

Advanced Usage:
    from amplifier.ccsdk_toolkit.decorators import sdk_function, batch_operation

    @sdk_function
    @batch_operation(batch_size=10)
    async def process_files(client, files: list):
        # Automatically batched and enhanced
        pass
"""

from .advanced import batch_operation
from .advanced import sdk_function
from .cache import with_cache
from .decorator_logging import with_logging
from .parsing import with_defensive_parsing
from .progress import with_progress
from .retry import with_retry
from .timing import with_timing
from .validation import with_validation

__all__ = [
    # Core decorators
    "with_retry",
    "with_logging",
    "with_defensive_parsing",
    "with_timing",
    "with_cache",
    "with_progress",
    "with_validation",
    # Advanced patterns
    "sdk_function",
    "batch_operation",
]
