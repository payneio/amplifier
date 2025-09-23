"""
Timing Decorator

Adds execution timing and performance monitoring to functions.
Warns on slow operations and provides timing statistics.
"""

import asyncio
import functools
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any
from typing import TypeVar

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])

# Global timing statistics
_timing_stats: dict[str, list[float]] = defaultdict(list)


def with_timing(
    warn_threshold: float | None = None,
    error_threshold: float | None = None,
    track_stats: bool = True,
    log_level: str = "INFO",
    include_args: bool = False,
) -> Callable[[F], F]:
    """
    Add execution timing to a function.

    Args:
        warn_threshold: Warn if execution exceeds this many seconds
        error_threshold: Log error if execution exceeds this many seconds
        track_stats: Whether to track timing statistics globally
        log_level: Default log level for timing messages
        include_args: Whether to include args in timing logs

    Returns:
        Decorated function with timing

    Example:
        @with_timing(warn_threshold=30.0)
        async def slow_analysis(client, data):
            return await client.query(f"Analyze: {data}")
    """
    log_func = getattr(logger, log_level.lower(), logger.info)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            func_name = func.__name__

            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                # Track statistics
                if track_stats:
                    _timing_stats[func_name].append(elapsed)

                # Log timing with appropriate level
                log_message = f"{func_name} completed in {elapsed:.3f}s"
                if include_args:
                    log_message += f" (args: {_format_args(args, kwargs)})"

                if error_threshold and elapsed > error_threshold:
                    logger.error(f"SLOW: {log_message} - Exceeded error threshold of {error_threshold}s")
                elif warn_threshold and elapsed > warn_threshold:
                    logger.warning(f"SLOW: {log_message} - Exceeded warning threshold of {warn_threshold}s")
                else:
                    log_func(log_message)

                return result

            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"{func_name} failed after {elapsed:.3f}s: {str(e)}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            func_name = func.__name__

            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time

                # Track statistics
                if track_stats:
                    _timing_stats[func_name].append(elapsed)

                # Log timing with appropriate level
                log_message = f"{func_name} completed in {elapsed:.3f}s"
                if include_args:
                    log_message += f" (args: {_format_args(args, kwargs)})"

                if error_threshold and elapsed > error_threshold:
                    logger.error(f"SLOW: {log_message} - Exceeded error threshold of {error_threshold}s")
                elif warn_threshold and elapsed > warn_threshold:
                    logger.warning(f"SLOW: {log_message} - Exceeded warning threshold of {warn_threshold}s")
                else:
                    log_func(log_message)

                return result

            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"{func_name} failed after {elapsed:.3f}s: {str(e)}")
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _format_args(args: tuple, kwargs: dict) -> str:
    """Format arguments for logging."""
    parts = []
    if args:
        # Skip first arg if it looks like a client
        start_idx = (
            1 if args and hasattr(args[0], "__class__") and "client" in args[0].__class__.__name__.lower() else 0
        )
        if len(args) > start_idx:
            arg_strs = [str(arg)[:50] for arg in args[start_idx:]]
            parts.append(", ".join(arg_strs))
    if kwargs:
        kwarg_strs = [f"{k}={str(v)[:50]}" for k, v in kwargs.items()]
        parts.append(", ".join(kwarg_strs))
    return ", ".join(parts) if parts else "no args"


def get_timing_stats(func_name: str | None = None) -> dict[str, dict[str, float]]:
    """
    Get timing statistics for functions.

    Args:
        func_name: Optional specific function name, or None for all

    Returns:
        Dictionary with timing statistics (min, max, avg, count)

    Example:
        stats = get_timing_stats("analyze_code")
        print(f"Average time: {stats['analyze_code']['avg']:.3f}s")
    """
    if func_name:
        if func_name not in _timing_stats:
            return {}
        timings = _timing_stats[func_name]
        if not timings:
            return {}
        return {
            func_name: {
                "min": min(timings),
                "max": max(timings),
                "avg": sum(timings) / len(timings),
                "count": len(timings),
                "total": sum(timings),
            }
        }
    results = {}
    for name, timings in _timing_stats.items():
        if timings:
            results[name] = {
                "min": min(timings),
                "max": max(timings),
                "avg": sum(timings) / len(timings),
                "count": len(timings),
                "total": sum(timings),
            }
    return results


def clear_timing_stats(func_name: str | None = None) -> None:
    """
    Clear timing statistics.

    Args:
        func_name: Optional specific function name, or None to clear all
    """
    if func_name:
        if func_name in _timing_stats:
            _timing_stats[func_name].clear()
    else:
        _timing_stats.clear()


def with_timeout(timeout_seconds: float, error_message: str | None = None) -> Callable[[F], F]:
    """
    Add timeout to async functions.

    Args:
        timeout_seconds: Maximum execution time in seconds
        error_message: Optional custom error message

    Returns:
        Decorated function with timeout

    Example:
        @with_timeout(60.0)
        async def long_analysis(client, data):
            return await client.query(f"Deep analysis: {data}")
    """

    def decorator(func: F) -> F:
        if not asyncio.iscoroutinefunction(func):
            raise ValueError(f"@with_timeout can only be used with async functions, not {func.__name__}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except TimeoutError:
                msg = error_message or f"{func.__name__} timed out after {timeout_seconds}s"
                logger.error(msg)
                raise TimeoutError(msg) from None

        return wrapper  # type: ignore

    return decorator
