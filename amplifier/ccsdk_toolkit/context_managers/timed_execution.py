"""TimedExecution context manager for execution timing and timeout handling.

This module provides a focused context manager for tracking execution time
and implementing timeout limits for AI queries.
"""

import asyncio
import logging
import time
from contextlib import suppress
from datetime import datetime
from datetime import timedelta
from types import TracebackType
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from amplifier.ccsdk_toolkit.client import ClaudeCodeSDKClient
else:
    ClaudeCodeSDKClient = Any

logger = logging.getLogger(__name__)


class TimedExecution:
    """Context manager for timed execution with timeout handling.

    This context manager provides execution time tracking, timeout enforcement,
    and performance metrics for AI queries.

    Example:
        ```python
        async with TimedExecution(client, timeout_minutes=5) as timer:
            response = await timer.query_with_timeout("Complex analysis")
            print(f"Execution took {timer.elapsed_time:.2f} seconds")
        ```

    Attributes:
        client: Initialized Claude Code SDK client
        timeout_minutes: Maximum execution time in minutes
        warn_at_percent: Warn when this percentage of timeout is reached
        track_metrics: Whether to track detailed performance metrics
    """

    def __init__(
        self,
        client: ClaudeCodeSDKClient,
        timeout_minutes: float = 5.0,
        warn_at_percent: float = 0.75,
        track_metrics: bool = True,
    ):
        """Initialize the TimedExecution context manager.

        Args:
            client: Initialized SDK client
            timeout_minutes: Maximum execution time in minutes
            warn_at_percent: Warn when this percentage of timeout is reached (0.0-1.0)
            track_metrics: Whether to track detailed performance metrics
        """
        self.client = client
        self.timeout_seconds = timeout_minutes * 60
        self.warn_at_seconds = self.timeout_seconds * warn_at_percent
        self.track_metrics = track_metrics

        self._start_time: float | None = None
        self._end_time: float | None = None
        self._warning_issued: bool = False
        self._queries_executed: int = 0
        self._query_times: list[float] = []
        self._timeout_task: asyncio.Task | None = None

    async def __aenter__(self) -> "TimedExecution":
        """Enter the context manager and start timing.

        Returns:
            Self for use in async with statement
        """
        logger.debug(f"Starting timed execution with {self.timeout_seconds}s timeout")

        self._start_time = time.time()

        # Start timeout monitoring
        if self.timeout_seconds > 0:
            self._timeout_task = asyncio.create_task(self._monitor_timeout())

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Exit the context manager and record final time.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self._end_time = time.time()

        # Cancel timeout monitoring
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._timeout_task

        # Log execution summary
        if self._start_time:
            elapsed = self._end_time - self._start_time
            logger.info(f"Timed execution complete: {elapsed:.2f}s elapsed, {self._queries_executed} queries executed")

            if self.track_metrics and self._query_times:
                avg_time = sum(self._query_times) / len(self._query_times)
                logger.debug(
                    f"Performance metrics - Avg query time: {avg_time:.2f}s, "
                    f"Min: {min(self._query_times):.2f}s, "
                    f"Max: {max(self._query_times):.2f}s"
                )

    async def _monitor_timeout(self) -> None:
        """Monitor for timeout conditions and issue warnings."""
        try:
            # Wait for warning threshold
            await asyncio.sleep(self.warn_at_seconds)

            if not self._warning_issued:
                remaining = self.timeout_seconds - self.warn_at_seconds
                logger.warning(
                    f"Execution time warning: {self.warn_at_seconds}s elapsed, {remaining}s remaining until timeout"
                )
                self._warning_issued = True

            # Wait for remaining time until timeout
            await asyncio.sleep(remaining)

            # Timeout reached
            logger.error(f"Execution timeout reached: {self.timeout_seconds}s")
            raise TimeoutError(f"Execution exceeded {self.timeout_seconds}s timeout")

        except asyncio.CancelledError:
            # Normal cancellation when exiting context
            pass

    async def query_with_timeout(self, prompt: str, individual_timeout: float | None = None, **kwargs: Any) -> str:
        """Execute a query with timeout enforcement.

        Args:
            prompt: The prompt to send
            individual_timeout: Optional timeout for this specific query (seconds)
            **kwargs: Additional arguments for the query

        Returns:
            Response from the AI

        Raises:
            TimeoutError: If the query exceeds the timeout
        """
        if not self._start_time:
            raise RuntimeError("TimedExecution not properly initialized")

        # Check if we've already exceeded the global timeout
        elapsed = time.time() - self._start_time
        if elapsed >= self.timeout_seconds:
            raise TimeoutError(f"Global timeout of {self.timeout_seconds}s already exceeded")

        # Calculate effective timeout
        remaining_global = self.timeout_seconds - elapsed
        effective_timeout = min(remaining_global, individual_timeout or remaining_global)

        # Track query start time
        query_start = time.time()

        try:
            # Execute query with timeout
            response = await asyncio.wait_for(self.client.query_with_retry(prompt, **kwargs), timeout=effective_timeout)

            # Track metrics
            query_time = time.time() - query_start
            self._queries_executed += 1

            if self.track_metrics:
                self._query_times.append(query_time)

            logger.debug(f"Query completed in {query_time:.2f}s")

            return response

        except TimeoutError:
            query_time = time.time() - query_start
            logger.error(f"Query timed out after {query_time:.2f}s")
            raise TimeoutError(f"Query exceeded {effective_timeout}s timeout")

    async def batch_with_timeout(
        self, prompts: list[str], continue_on_timeout: bool = True, **kwargs: Any
    ) -> list[tuple[str, str | None]]:
        """Process multiple prompts with timeout handling.

        Args:
            prompts: List of prompts to process
            continue_on_timeout: Whether to continue if a query times out
            **kwargs: Additional arguments for queries

        Returns:
            List of tuples (prompt, response or None if timed out)
        """
        results = []

        for prompt in prompts:
            try:
                response = await self.query_with_timeout(prompt, **kwargs)
                results.append((prompt, response))

            except TimeoutError as e:
                logger.warning(f"Timeout processing prompt: {str(e)}")

                if continue_on_timeout:
                    results.append((prompt, None))
                else:
                    raise

        return results

    async def with_progress_callback(self, prompt: str, progress_callback: Any, **kwargs: Any) -> str:
        """Execute a query with progress callbacks.

        Args:
            prompt: The prompt to send
            progress_callback: Callback function for progress updates
            **kwargs: Additional arguments

        Returns:
            Response from the AI
        """
        if not self._start_time:
            raise RuntimeError("TimedExecution not properly initialized")

        # Report initial progress
        elapsed = time.time() - self._start_time
        remaining = max(0, self.timeout_seconds - elapsed)

        await self._call_progress_callback(
            progress_callback,
            {
                "status": "starting",
                "elapsed": elapsed,
                "remaining": remaining,
                "query_number": self._queries_executed + 1,
            },
        )

        # Execute query
        response = await self.query_with_timeout(prompt, **kwargs)

        # Report completion
        elapsed = time.time() - self._start_time
        remaining = max(0, self.timeout_seconds - elapsed)

        await self._call_progress_callback(
            progress_callback,
            {"status": "completed", "elapsed": elapsed, "remaining": remaining, "query_number": self._queries_executed},
        )

        return response

    async def _call_progress_callback(self, callback: Any, progress_info: dict[str, Any]) -> None:
        """Call progress callback with proper async handling.

        Args:
            callback: The callback function
            progress_info: Progress information to pass
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(progress_info)
            else:
                callback(progress_info)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if not self._start_time:
            return 0.0

        end_time = self._end_time or time.time()
        return end_time - self._start_time

    @property
    def remaining_time(self) -> float:
        """Get remaining time before timeout in seconds."""
        if not self._start_time:
            return self.timeout_seconds

        return max(0, self.timeout_seconds - self.elapsed_time)

    @property
    def is_timed_out(self) -> bool:
        """Check if execution has timed out."""
        return self.elapsed_time >= self.timeout_seconds

    @property
    def metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        if not self.track_metrics or not self._query_times:
            return {}

        return {
            "total_queries": self._queries_executed,
            "total_time": self.elapsed_time,
            "average_query_time": sum(self._query_times) / len(self._query_times),
            "min_query_time": min(self._query_times),
            "max_query_time": max(self._query_times),
            "timeout_percentage": (self.elapsed_time / self.timeout_seconds * 100) if self.timeout_seconds > 0 else 0,
        }

    def get_deadline(self) -> datetime:
        """Get the absolute deadline for execution.

        Returns:
            Datetime when timeout will be reached
        """
        if not self._start_time:
            return datetime.now() + timedelta(seconds=self.timeout_seconds)

        remaining = self.remaining_time
        return datetime.now() + timedelta(seconds=remaining)
