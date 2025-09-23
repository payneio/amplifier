"""RetryContext manager for configurable retry strategies.

This module provides a focused context manager for implementing various
retry strategies with error recovery and failure logging.
"""

import asyncio
import logging
import random
from collections.abc import Callable
from enum import Enum
from types import TracebackType
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

if TYPE_CHECKING:
    from amplifier.ccsdk_toolkit.client import ClaudeCodeSDKClient
else:
    ClaudeCodeSDKClient = Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(Enum):
    """Enumeration of available retry strategies."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    RANDOM_JITTER = "random_jitter"


class RetryContext:
    """Context manager for configurable retry strategies.

    This context manager provides robust retry logic with various backoff
    strategies, error recovery, and comprehensive failure reporting.

    Example:
        ```python
        async with RetryContext(client, max_retries=5, backoff="exponential") as retry:
            response = await retry.robust_query("Complex analysis")
            print(f"Succeeded after {retry.attempt_count} attempts")
        ```

    Attributes:
        client: Initialized Claude Code SDK client
        max_retries: Maximum number of retry attempts
        backoff: Backoff strategy to use
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retry_on_exceptions: Exception types to retry on
    """

    def __init__(
        self,
        client: ClaudeCodeSDKClient,
        max_retries: int = 3,
        backoff: str = "exponential",
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        retry_on_exceptions: tuple[type[Exception], ...] | None = None,
    ):
        """Initialize the RetryContext manager.

        Args:
            client: Initialized SDK client
            max_retries: Maximum number of retry attempts
            backoff: Backoff strategy ("linear", "exponential", "fibonacci", "random_jitter")
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            retry_on_exceptions: Tuple of exception types to retry on (default: all)
        """
        self.client = client
        self.max_retries = max_retries
        self.backoff = RetryStrategy(backoff)
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.retry_on_exceptions = retry_on_exceptions or (Exception,)

        self._attempt_count: int = 0
        self._failure_log: list[dict[str, Any]] = []
        self._success_count: int = 0
        self._total_operations: int = 0
        self._fibonacci_cache: list[float] = [initial_delay, initial_delay * 2]

    async def __aenter__(self) -> "RetryContext":
        """Enter the context manager and initialize retry state.

        Returns:
            Self for use in async with statement
        """
        logger.debug(f"Entering RetryContext with {self.backoff.value} strategy")
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Exit the context manager and log retry statistics.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        logger.debug("Exiting RetryContext")

        # Log statistics if any operations were performed
        if self._total_operations > 0:
            success_rate = (self._success_count / self._total_operations) * 100
            logger.info(
                f"Retry context complete: {self._total_operations} operations, "
                f"{self._success_count} succeeded ({success_rate:.1f}% success rate)"
            )

            if self._failure_log:
                logger.debug(f"Total failures encountered: {len(self._failure_log)}")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the next retry based on strategy.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds before next retry
        """
        if self.backoff == RetryStrategy.LINEAR:
            delay = self.initial_delay * (attempt + 1)

        elif self.backoff == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (2**attempt)

        elif self.backoff == RetryStrategy.FIBONACCI:
            # Generate Fibonacci sequence up to current attempt
            while len(self._fibonacci_cache) <= attempt:
                self._fibonacci_cache.append(self._fibonacci_cache[-1] + self._fibonacci_cache[-2])
            delay = self._fibonacci_cache[attempt]

        elif self.backoff == RetryStrategy.RANDOM_JITTER:
            # Exponential with random jitter
            base_delay = self.initial_delay * (2**attempt)
            jitter = random.uniform(0, base_delay * 0.1)  # 10% jitter
            delay = base_delay + jitter

        else:
            delay = self.initial_delay

        # Cap at maximum delay
        return min(delay, self.max_delay)

    async def robust_query(
        self, prompt: str, error_callback: Callable[[Exception, int], None] | None = None, **kwargs: Any
    ) -> str:
        """Execute a query with robust retry logic.

        Args:
            prompt: The prompt to send
            error_callback: Optional callback for each error
            **kwargs: Additional arguments for the query

        Returns:
            Response from the AI

        Raises:
            Exception: After all retries are exhausted
        """
        self._total_operations += 1
        last_exception = None

        for attempt in range(self.max_retries + 1):
            self._attempt_count = attempt

            try:
                # Try the query
                response = await self.client.query_with_retry(
                    prompt,
                    max_retries=1,  # Single attempt here, we handle retries
                    **kwargs,
                )

                # Success!
                self._success_count += 1

                if attempt > 0:
                    logger.info(f"Query succeeded after {attempt} retries")

                return response

            except self.retry_on_exceptions as e:
                last_exception = e

                # Log the failure
                self._failure_log.append({"attempt": attempt, "error": str(e), "error_type": type(e).__name__})

                # Call error callback if provided
                if error_callback:
                    try:
                        if asyncio.iscoroutinefunction(error_callback):
                            await error_callback(e, attempt)
                        else:
                            error_callback(e, attempt)
                    except Exception as cb_error:
                        logger.warning(f"Error callback failed: {cb_error}")

                # Check if we should retry
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")

        # All retries exhausted
        raise last_exception or Exception("All retry attempts failed")

    async def with_fallback(self, primary_func: Callable, fallback_func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function with fallback on failure.

        Args:
            primary_func: Primary function to try
            fallback_func: Fallback function if primary fails
            *args: Positional arguments for functions
            **kwargs: Keyword arguments for functions

        Returns:
            Result from primary or fallback function
        """
        self._total_operations += 1

        try:
            # Try primary function with retries
            for attempt in range(self.max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(primary_func):
                        result = await primary_func(*args, **kwargs)
                    else:
                        result = primary_func(*args, **kwargs)

                    self._success_count += 1
                    return result

                except self.retry_on_exceptions:
                    if attempt < self.max_retries:
                        delay = self._calculate_delay(attempt)
                        logger.debug(f"Primary function failed, retrying in {delay:.1f}s")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning("Primary function failed, using fallback")
                        break

        except Exception as e:
            logger.warning(f"Primary function failed with unexpected error: {e}")

        # Use fallback
        try:
            if asyncio.iscoroutinefunction(fallback_func):
                result = await fallback_func(*args, **kwargs)
            else:
                result = fallback_func(*args, **kwargs)

            self._success_count += 1
            logger.info("Fallback function succeeded")
            return result

        except Exception as e:
            logger.error(f"Both primary and fallback functions failed: {e}")
            raise

    async def batch_with_retry(
        self, prompts: list[str], continue_on_failure: bool = True, **kwargs: Any
    ) -> list[tuple[str, str | None]]:
        """Process multiple prompts with individual retry logic.

        Args:
            prompts: List of prompts to process
            continue_on_failure: Whether to continue if a prompt fails after retries
            **kwargs: Additional arguments for queries

        Returns:
            List of tuples (prompt, response or None if failed)
        """
        results = []

        for i, prompt in enumerate(prompts, 1):
            logger.debug(f"Processing prompt {i}/{len(prompts)}")

            try:
                response = await self.robust_query(prompt, **kwargs)
                results.append((prompt, response))

            except Exception as e:
                logger.error(f"Failed to process prompt after retries: {e}")

                if continue_on_failure:
                    results.append((prompt, None))
                else:
                    raise

        return results

    async def with_circuit_breaker(
        self, func: Callable, failure_threshold: int = 5, recovery_timeout: float = 60.0, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute with circuit breaker pattern.

        Args:
            func: Function to execute
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery (seconds)
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            RuntimeError: If circuit is open
        """
        # Check if circuit should be open
        recent_failures = [f for f in self._failure_log if f.get("circuit_breaker", False)]

        if len(recent_failures) >= failure_threshold:
            # Check if recovery timeout has passed
            # This is simplified - real implementation would track timestamps
            logger.error("Circuit breaker is OPEN - too many failures")
            raise RuntimeError("Circuit breaker is open due to repeated failures")

        try:
            # Try the operation
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Reset circuit breaker on success
            self._failure_log = [f for f in self._failure_log if not f.get("circuit_breaker", False)]

            return result

        except Exception as e:
            # Record circuit breaker failure
            self._failure_log.append({"error": str(e), "circuit_breaker": True})
            raise

    @property
    def attempt_count(self) -> int:
        """Get the current attempt count."""
        return self._attempt_count

    @property
    def failure_log(self) -> list[dict[str, Any]]:
        """Get the failure log."""
        return self._failure_log.copy()

    @property
    def statistics(self) -> dict[str, Any]:
        """Get retry statistics."""
        return {
            "total_operations": self._total_operations,
            "successful_operations": self._success_count,
            "success_rate": ((self._success_count / self._total_operations * 100) if self._total_operations > 0 else 0),
            "total_failures": len(self._failure_log),
            "retry_strategy": self.backoff.value,
            "max_retries": self.max_retries,
        }
