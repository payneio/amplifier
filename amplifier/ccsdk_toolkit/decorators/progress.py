"""
Progress Tracking Decorator

Adds progress tracking to functions working with Claude Code SDK.
Supports callbacks, batch operations, and progress aggregation.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import Any
from typing import TypeVar

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


def with_progress(
    callback: Callable[[float, str], None] | None = None,
    total_steps: int | None = None,
    report_interval: float = 1.0,
    show_eta: bool = True,
    description: str | None = None,
) -> Callable[[F], F]:
    """
    Add progress tracking to a function.

    Args:
        callback: Optional callback function(progress: float, message: str)
        total_steps: Total number of steps (for manual progress tracking)
        report_interval: Minimum seconds between progress reports
        show_eta: Whether to calculate and show ETA
        description: Optional description for progress messages

    Returns:
        Decorated function with progress tracking

    Example:
        @with_progress(callback=print_progress)
        async def process_batch(client, items):
            for i, item in enumerate(items):
                result = await client.query(item)
                update_progress(i + 1, len(items))
    """

    def default_callback(progress: float, message: str):
        """Default progress callback that logs."""
        logger.info(f"Progress: {progress:.1%} - {message}")

    # Use provided callback or default
    progress_callback = callback or default_callback

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            last_report_time = 0.0
            progress_data = {
                "current": 0,
                "total": total_steps or 0,
                "start_time": start_time,
            }

            def update_progress(current: int, total: int | None = None):
                """Update progress from within the function."""
                nonlocal last_report_time

                current_time = time.time()
                if current_time - last_report_time < report_interval:
                    return  # Skip if too soon

                progress_data["current"] = current
                if total is not None:
                    progress_data["total"] = total

                if progress_data["total"] > 0:
                    progress = current / progress_data["total"]

                    # Calculate ETA if requested
                    message = description or func.__name__
                    if show_eta and current > 0:
                        elapsed = current_time - start_time
                        rate = current / elapsed
                        remaining = (progress_data["total"] - current) / rate if rate > 0 else 0
                        message = f"{message} - ETA: {remaining:.1f}s"

                    progress_callback(progress, message)
                    last_report_time = current_time

            # Inject progress updater into function context
            if "update_progress" in func.__code__.co_names:
                # Function expects progress updater
                result = await func(*args, update_progress=update_progress, **kwargs)
            else:
                # Regular function call
                result = await func(*args, **kwargs)

            # Final progress report
            if progress_data["total"] > 0:
                elapsed = time.time() - start_time
                final_message = f"{description or func.__name__} completed in {elapsed:.1f}s"
                progress_callback(1.0, final_message)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            last_report_time = 0.0
            progress_data = {
                "current": 0,
                "total": total_steps or 0,
                "start_time": start_time,
            }

            def update_progress(current: int, total: int | None = None):
                """Update progress from within the function."""
                nonlocal last_report_time

                current_time = time.time()
                if current_time - last_report_time < report_interval:
                    return  # Skip if too soon

                progress_data["current"] = current
                if total is not None:
                    progress_data["total"] = total

                if progress_data["total"] > 0:
                    progress = current / progress_data["total"]

                    # Calculate ETA if requested
                    message = description or func.__name__
                    if show_eta and current > 0:
                        elapsed = current_time - start_time
                        rate = current / elapsed
                        remaining = (progress_data["total"] - current) / rate if rate > 0 else 0
                        message = f"{message} - ETA: {remaining:.1f}s"

                    progress_callback(progress, message)
                    last_report_time = current_time

            # Inject progress updater into function context
            if "update_progress" in func.__code__.co_names:
                # Function expects progress updater
                result = func(*args, update_progress=update_progress, **kwargs)
            else:
                # Regular function call
                result = func(*args, **kwargs)

            # Final progress report
            if progress_data["total"] > 0:
                elapsed = time.time() - start_time
                final_message = f"{description or func.__name__} completed in {elapsed:.1f}s"
                progress_callback(1.0, final_message)

            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def with_batch_progress(
    batch_size: int = 10,
    callback: Callable[[int, int, str], None] | None = None,
    parallel: bool = False,
) -> Callable[[F], F]:
    """
    Add progress tracking for batch operations.

    Args:
        batch_size: Size of each batch
        callback: Optional callback(completed, total, message)
        parallel: Whether batches are processed in parallel

    Returns:
        Decorated function with batch progress tracking

    Example:
        @with_batch_progress(batch_size=5, parallel=True)
        async def analyze_files(client, files: list):
            results = []
            for file in files:
                result = await client.query(f"Analyze: {file.read_text()}")
                results.append(result)
            return results
    """

    def default_callback(completed: int, total: int, message: str):
        """Default batch progress callback."""
        progress = completed / total if total > 0 else 0
        logger.info(f"Batch progress: {completed}/{total} ({progress:.1%}) - {message}")

    batch_callback = callback or default_callback

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Find list/iterable argument
            items = None
            for arg in args:
                if isinstance(arg, list | tuple) and len(arg) > 0:
                    items = arg
                    break

            if items is None:
                # No batch to process
                return await func(*args, **kwargs)

            total_items = len(items)
            completed = 0
            results = []

            # Process in batches
            for i in range(0, total_items, batch_size):
                batch = items[i : i + batch_size]
                batch_num = i // batch_size + 1

                batch_callback(completed, total_items, f"Processing batch {batch_num}")

                if parallel and asyncio.iscoroutinefunction(func):
                    # Process batch items in parallel
                    batch_results = await asyncio.gather(
                        *[
                            func(*args[: args.index(items)], item, *args[args.index(items) + 1 :], **kwargs)
                            for item in batch
                        ]
                    )
                    results.extend(batch_results)
                else:
                    # Process batch items sequentially
                    for item in batch:
                        result = await func(*args[: args.index(items)], item, *args[args.index(items) + 1 :], **kwargs)
                        results.append(result)

                completed += len(batch)
                batch_callback(completed, total_items, f"Completed batch {batch_num}")

            return results

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Find list/iterable argument
            items = None
            for arg in args:
                if isinstance(arg, list | tuple) and len(arg) > 0:
                    items = arg
                    break

            if items is None:
                # No batch to process
                return func(*args, **kwargs)

            total_items = len(items)
            completed = 0
            results = []

            # Process in batches
            for i in range(0, total_items, batch_size):
                batch = items[i : i + batch_size]
                batch_num = i // batch_size + 1

                batch_callback(completed, total_items, f"Processing batch {batch_num}")

                # Process batch items sequentially
                for item in batch:
                    result = func(*args[: args.index(items)], item, *args[args.index(items) + 1 :], **kwargs)
                    results.append(result)

                completed += len(batch)
                batch_callback(completed, total_items, f"Completed batch {batch_num}")

            return results

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
