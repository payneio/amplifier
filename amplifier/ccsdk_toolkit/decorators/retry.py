"""
Retry Decorator

Adds configurable retry logic to functions working with Claude Code SDK.
Supports exponential backoff, error classification, and retry callbacks.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import Any
from typing import TypeVar
from typing import Union

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    attempts: int = 3,
    backoff: Union[str, float] = "exponential",
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_errors: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable[[F], F]:
    """
    Add retry logic to a function.

    Args:
        attempts: Maximum number of retry attempts
        backoff: Backoff strategy - "exponential", "linear", or fixed delay
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retryable_errors: Tuple of exception types to retry (None = retry all)
        on_retry: Optional callback called on each retry with (exception, attempt_number)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(attempts=3, backoff="exponential")
        async def query_llm(client, prompt):
            return await client.query(prompt)
    """
    if retryable_errors is None:
        # Default retryable errors for LLM operations
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError,
        )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay

            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e

                    if attempt == attempts:
                        logger.error(f"All {attempts} retry attempts failed for {func.__name__}")
                        raise

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback error: {callback_error}")

                    # Calculate next delay
                    if backoff == "exponential":
                        delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
                    elif backoff == "linear":
                        delay = min(initial_delay * attempt, max_delay)
                    elif isinstance(backoff, int | float):
                        delay = float(backoff)

                    logger.info(
                        f"Retry {attempt}/{attempts} for {func.__name__} after {delay:.1f}s delay. Error: {str(e)}"
                    )
                    await asyncio.sleep(delay)

                except Exception as e:
                    # Non-retryable error, raise immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            return None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay

            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e

                    if attempt == attempts:
                        logger.error(f"All {attempts} retry attempts failed for {func.__name__}")
                        raise

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback error: {callback_error}")

                    # Calculate next delay
                    if backoff == "exponential":
                        delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
                    elif backoff == "linear":
                        delay = min(initial_delay * attempt, max_delay)
                    elif isinstance(backoff, int | float):
                        delay = float(backoff)

                    logger.info(
                        f"Retry {attempt}/{attempts} for {func.__name__} after {delay:.1f}s delay. Error: {str(e)}"
                    )
                    time.sleep(delay)

                except Exception as e:
                    # Non-retryable error, raise immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            return None

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
