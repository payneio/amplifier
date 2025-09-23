"""
Advanced Decorator Patterns

Provides high-level decorator patterns for common SDK use cases.
Combines multiple decorators for comprehensive functionality.
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any
from typing import TypeVar

from .cache import with_cache
from .logging import with_logging
from .parsing import with_defensive_parsing
from .retry import with_retry
from .timing import with_timing

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


def sdk_function(
    retry_attempts: int = 3,
    enable_logging: bool = True,
    enable_timing: bool = True,
    parse_json: bool = True,
    cache_ttl: float | None = None,
) -> Callable[[F], F]:
    """
    Mark and enhance a function as an SDK-enhanced function.

    This is a convenience decorator that applies common enhancements.

    Args:
        retry_attempts: Number of retry attempts (0 to disable)
        enable_logging: Whether to enable logging
        enable_timing: Whether to track timing
        parse_json: Whether to parse JSON responses
        cache_ttl: Optional cache TTL in seconds

    Returns:
        Decorated function with SDK enhancements

    Example:
        @sdk_function(retry_attempts=3, cache_ttl=300)
        async def get_analysis(client, code: str):
            return await client.query(f"Analyze: {code}")
    """

    def decorator(func: F) -> F:
        # Build decorator chain
        decorated = func

        # Apply decorators in reverse order (innermost first)
        if parse_json:
            decorated = with_defensive_parsing(extract_json=True)(decorated)

        if cache_ttl:
            decorated = with_cache(ttl=cache_ttl)(decorated)

        if retry_attempts > 0:
            decorated = with_retry(attempts=retry_attempts)(decorated)

        if enable_timing:
            decorated = with_timing(warn_threshold=30.0)(decorated)

        if enable_logging:
            decorated = with_logging(include_timing=False)(decorated)  # Timing already tracked

        # Mark as SDK function
        decorated.__sdk_function__ = True  # type: ignore

        return decorated

    return decorator


def batch_operation(
    batch_size: int = 10,
    parallel: bool = False,
    retry_per_item: bool = True,
    progress_callback: Callable | None = None,
) -> Callable[[F], F]:
    """
    Enhanced batch processing decorator.

    Automatically batches operations and handles errors gracefully.

    Args:
        batch_size: Size of each batch
        parallel: Whether to process batch items in parallel
        retry_per_item: Whether to retry failed items
        progress_callback: Optional progress callback

    Returns:
        Decorated function for batch processing

    Example:
        @batch_operation(batch_size=5, parallel=True)
        async def analyze_files(client, files: list[Path]):
            results = []
            for file in files:
                content = file.read_text()
                result = await client.query(f"Analyze: {content}")
                results.append(result)
            return results
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Find list/iterable argument
            items = None
            items_index = None
            for i, arg in enumerate(args):
                if isinstance(arg, list | tuple) and len(arg) > 0:
                    items = arg
                    items_index = i
                    break

            if items is None or items_index is None:
                # No batch to process
                return await func(*args, **kwargs)

            total_items = len(items)
            completed = 0
            results = []
            failed_items = []

            # Process in batches
            for batch_start in range(0, total_items, batch_size):
                batch_end = min(batch_start + batch_size, total_items)
                batch = items[batch_start:batch_end]
                batch_num = batch_start // batch_size + 1

                if progress_callback:
                    progress_callback(
                        completed,
                        total_items,
                        f"Processing batch {batch_num}/{(total_items + batch_size - 1) // batch_size}",
                    )

                if parallel:
                    # Process batch items in parallel
                    batch_tasks = []
                    for item in batch:
                        # Create new args with single item
                        item_args = args[:items_index] + (item,) + args[items_index + 1 :]

                        if retry_per_item:
                            # Wrap each item with retry
                            @with_retry(attempts=3)
                            async def process_item(captured_args=item_args):
                                return await func(*captured_args, **kwargs)

                            batch_tasks.append(process_item())
                        else:
                            batch_tasks.append(func(*item_args, **kwargs))

                    # Execute batch with error handling
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                    # Process results
                    for i, result in enumerate(batch_results):
                        if isinstance(result, Exception):
                            logger.error(f"Failed to process item {batch_start + i}: {result}")
                            failed_items.append((batch_start + i, batch[i], result))
                            results.append(None)  # Placeholder for failed item
                        else:
                            results.append(result)

                else:
                    # Process batch items sequentially
                    for i, item in enumerate(batch):
                        item_args = args[:items_index] + (item,) + args[items_index + 1 :]

                        try:
                            if retry_per_item:
                                # Apply retry to individual item
                                @with_retry(attempts=3)
                                async def process_item(captured_args=item_args):
                                    return await func(*captured_args, **kwargs)

                                result = await process_item()
                            else:
                                result = await func(*item_args, **kwargs)
                            results.append(result)

                        except Exception as e:
                            logger.error(f"Failed to process item {batch_start + i}: {e}")
                            failed_items.append((batch_start + i, item, e))
                            results.append(None)  # Placeholder for failed item

                completed += len(batch)

                if progress_callback:
                    progress_callback(completed, total_items, f"Completed batch {batch_num}")

            # Log summary if there were failures
            if failed_items:
                logger.warning(
                    f"Batch operation completed with {len(failed_items)} failures out of {total_items} items"
                )

            # Store failed items metadata in results if needed
            if hasattr(results, "__dict__"):
                results.__failed_items__ = failed_items  # type: ignore

            return results

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Find list/iterable argument
            items = None
            items_index = None
            for i, arg in enumerate(args):
                if isinstance(arg, list | tuple) and len(arg) > 0:
                    items = arg
                    items_index = i
                    break

            if items is None or items_index is None:
                # No batch to process
                return func(*args, **kwargs)

            total_items = len(items)
            completed = 0
            results = []
            failed_items = []

            # Process in batches (sequential only for sync)
            for batch_start in range(0, total_items, batch_size):
                batch_end = min(batch_start + batch_size, total_items)
                batch = items[batch_start:batch_end]
                batch_num = batch_start // batch_size + 1

                if progress_callback:
                    progress_callback(
                        completed,
                        total_items,
                        f"Processing batch {batch_num}/{(total_items + batch_size - 1) // batch_size}",
                    )

                # Process batch items sequentially
                for i, item in enumerate(batch):
                    item_args = args[:items_index] + (item,) + args[items_index + 1 :]

                    try:
                        result = func(*item_args, **kwargs)
                        results.append(result)

                    except Exception as e:
                        logger.error(f"Failed to process item {batch_start + i}: {e}")
                        failed_items.append((batch_start + i, item, e))
                        results.append(None)  # Placeholder for failed item

                completed += len(batch)

                if progress_callback:
                    progress_callback(completed, total_items, f"Completed batch {batch_num}")

            # Log summary if there were failures
            if failed_items:
                logger.warning(
                    f"Batch operation completed with {len(failed_items)} failures out of {total_items} items"
                )

            return results

        # Mark as batch operation
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper.__batch_operation__ = True  # type: ignore

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def robust_sdk_function(
    max_retries: int = 5,
    cache_ttl: float = 3600,
    warn_threshold: float = 30.0,
    parse_json: bool = True,
    log_file: str | None = None,
) -> Callable[[F], F]:
    """
    Create a robust SDK function with all safety features.

    This applies maximum protection for critical operations.

    Args:
        max_retries: Maximum retry attempts
        cache_ttl: Cache time-to-live in seconds
        warn_threshold: Warning threshold for slow operations
        parse_json: Whether to parse JSON responses
        log_file: Optional log file for dedicated logging

    Returns:
        Highly robust decorated function

    Example:
        @robust_sdk_function(max_retries=5, cache_ttl=3600)
        async def critical_operation(client, data: dict):
            return await client.query("Critical: " + json.dumps(data))
    """

    def decorator(func: F) -> F:
        # Apply comprehensive enhancements
        decorated = func

        # Defensive parsing (innermost)
        if parse_json:
            decorated = with_defensive_parsing(
                extract_json=True, fallback_value={"error": "Failed to parse response"}, log_errors=True
            )(decorated)

        # Caching
        decorated = with_cache(ttl=cache_ttl, max_size=100)(decorated)

        # Retry with exponential backoff
        decorated = with_retry(attempts=max_retries, backoff="exponential", initial_delay=1.0, max_delay=30.0)(
            decorated
        )

        # Timing with warnings
        decorated = with_timing(warn_threshold=warn_threshold, error_threshold=warn_threshold * 2, track_stats=True)(
            decorated
        )

        # Comprehensive logging
        decorated = with_logging(
            log_file=log_file,
            include_args=True,
            include_result=False,  # Don't log potentially sensitive results
            include_timing=True,
        )(decorated)

        # Mark as robust function
        decorated.__robust_sdk_function__ = True  # type: ignore

        return decorated

    return decorator
