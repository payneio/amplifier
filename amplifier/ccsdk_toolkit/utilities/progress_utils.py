"""
Progress tracking utilities for claude-code-sdk

Provides progress tracking without modifying SDK interface.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class SimpleProgressCallback:
    """Simple progress callback for batch operations.

    Example:
        >>> callback = SimpleProgressCallback()
        >>> responses = await batch_query(client, prompts, on_progress=callback)
    """

    def __init__(self, prefix: str = "Progress"):
        """Initialize progress callback.

        Args:
            prefix: Prefix for progress messages
        """
        self.prefix = prefix
        self.start_time = None
        self.last_report_time = 0

    def __call__(self, completed: int, total: int) -> None:
        """Handle progress update.

        Args:
            completed: Number of completed items
            total: Total items to process
        """
        if self.start_time is None:
            self.start_time = time.time()

        # Report at most once per second
        current_time = time.time()
        if current_time - self.last_report_time < 1.0 and completed < total:
            return

        self.last_report_time = current_time
        elapsed = current_time - self.start_time
        percent = (completed / total) * 100

        if elapsed > 0 and completed > 0:
            rate = completed / elapsed
            remaining = (total - completed) / rate
            logger.info(
                f"{self.prefix}: {completed}/{total} ({percent:.1f}%) "
                f"- {elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining"
            )
        else:
            logger.info(f"{self.prefix}: {completed}/{total} ({percent:.1f}%)")


class ProgressTracker:
    """Wrap SDK client to add progress tracking.

    This doesn't modify the client, just adds logging around operations.

    Example:
        >>> client = ClaudeSDKClient()
        >>> tracker = ProgressTracker()
        >>> tracked_client = tracker.wrap_client(client)
        >>> # Use tracked_client normally, progress will be logged
        >>> response = await tracked_client.query("Hello")
    """

    def __init__(self, log_level: int = logging.INFO):
        """Initialize progress tracker.

        Args:
            log_level: Logging level for progress messages
        """
        self.log_level = log_level
        self.operation_count = 0
        self.start_time = time.time()

    def wrap_client(self, client: Any) -> Any:
        """Wrap client to add progress tracking.

        This returns a wrapper that logs operations without
        modifying the client's interface.

        Args:
            client: SDK client to wrap

        Returns:
            Wrapped client with same interface
        """
        return TrackedClient(client, self)


class TrackedClient:
    """Wrapper that adds progress tracking to SDK client."""

    def __init__(self, client: Any, tracker: ProgressTracker):
        """Initialize tracked client wrapper.

        Args:
            client: Original SDK client
            tracker: ProgressTracker instance
        """
        self._client = client
        self._tracker = tracker

    def __getattr__(self, name: str) -> Any:
        """Forward all attributes to wrapped client.

        Args:
            name: Attribute name

        Returns:
            Wrapped attribute with tracking if it's a method
        """
        attr = getattr(self._client, name)

        # If it's a method, wrap it with tracking
        if callable(attr):
            return self._wrap_method(name, attr)

        return attr

    def _wrap_method(self, method_name: str, method: Callable) -> Callable:
        """Wrap a method with progress tracking.

        Args:
            method_name: Name of the method
            method: Original method

        Returns:
            Wrapped method with tracking
        """

        async def async_wrapper(*args, **kwargs):
            """Async method wrapper with tracking."""
            self._tracker.operation_count += 1
            operation_id = self._tracker.operation_count
            start_time = time.time()

            logger.log(self._tracker.log_level, f"[Operation {operation_id}] Starting: {method_name}")

            try:
                result = await method(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(
                    self._tracker.log_level, f"[Operation {operation_id}] Completed: {method_name} ({elapsed:.2f}s)"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[Operation {operation_id}] Failed: {method_name} ({elapsed:.2f}s) - {e}")
                raise

        def sync_wrapper(*args, **kwargs):
            """Sync method wrapper with tracking."""
            self._tracker.operation_count += 1
            operation_id = self._tracker.operation_count
            start_time = time.time()

            logger.log(self._tracker.log_level, f"[Operation {operation_id}] Starting: {method_name}")

            try:
                result = method(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(
                    self._tracker.log_level, f"[Operation {operation_id}] Completed: {method_name} ({elapsed:.2f}s)"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[Operation {operation_id}] Failed: {method_name} ({elapsed:.2f}s) - {e}")
                raise

        # Check if the method is async
        import asyncio

        if asyncio.iscoroutinefunction(method):
            return async_wrapper
        return sync_wrapper
