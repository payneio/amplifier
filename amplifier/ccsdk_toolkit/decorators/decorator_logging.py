"""
Logging Decorator

Adds structured logging to functions working with Claude Code SDK.
Logs function calls, parameters, results, and performance metrics.
"""

import asyncio
import functools
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import TypeVar
from typing import Union

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


def with_logging(
    log_file: Union[str, Path] | None = None,
    level: str = "INFO",
    include_args: bool = True,
    include_result: bool = False,
    include_timing: bool = True,
    max_result_length: int = 500,
    custom_logger: logging.Logger | None = None,
) -> Callable[[F], F]:
    """
    Add structured logging to a function.

    Args:
        log_file: Optional file path to write logs (None = use standard logger)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        include_args: Whether to log function arguments
        include_result: Whether to log function results
        include_timing: Whether to log execution time
        max_result_length: Maximum length of result to log
        custom_logger: Optional custom logger instance

    Returns:
        Decorated function with logging

    Example:
        @with_logging(log_file="analysis.log", include_result=True)
        async def analyze_code(client, code: str):
            return await client.query(f"Analyze: {code}")
    """
    # Set up logger
    if custom_logger:
        func_logger = custom_logger
    elif log_file:
        func_logger = logging.getLogger(f"ccsdk.{log_file}")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        func_logger.addHandler(handler)
        func_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    else:
        func_logger = logger

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            log_entry: dict[str, Any] = {"function": func.__name__, "type": "async"}

            # Log function call with arguments
            if include_args:
                log_entry["args"] = _serialize_args(args, kwargs)

            func_logger.info(f"Calling {func.__name__} - {json.dumps(log_entry)}")

            try:
                result = await func(*args, **kwargs)

                # Log successful completion
                elapsed = time.time() - start_time
                success_log: dict[str, Any] = {"function": func.__name__, "status": "success"}

                if include_timing:
                    success_log["duration_seconds"] = round(elapsed, 3)

                if include_result:
                    success_log["result"] = _truncate_result(result, max_result_length)

                func_logger.info(f"Completed {func.__name__} in {elapsed:.3f}s - {json.dumps(success_log)}")

                return result

            except Exception as e:
                elapsed = time.time() - start_time
                error_log: dict[str, Any] = {
                    "function": func.__name__,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

                if include_timing:
                    error_log["duration_seconds"] = round(elapsed, 3)

                func_logger.error(f"Error in {func.__name__}: {str(e)} - {json.dumps(error_log)}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            log_entry: dict[str, Any] = {"function": func.__name__, "type": "sync"}

            # Log function call with arguments
            if include_args:
                log_entry["args"] = _serialize_args(args, kwargs)

            func_logger.info(f"Calling {func.__name__} - {json.dumps(log_entry)}")

            try:
                result = func(*args, **kwargs)

                # Log successful completion
                elapsed = time.time() - start_time
                success_log: dict[str, Any] = {"function": func.__name__, "status": "success"}

                if include_timing:
                    success_log["duration_seconds"] = round(elapsed, 3)

                if include_result:
                    success_log["result"] = _truncate_result(result, max_result_length)

                func_logger.info(f"Completed {func.__name__} in {elapsed:.3f}s - {json.dumps(success_log)}")

                return result

            except Exception as e:
                elapsed = time.time() - start_time
                error_log: dict[str, Any] = {
                    "function": func.__name__,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

                if include_timing:
                    error_log["duration_seconds"] = round(elapsed, 3)

                func_logger.error(f"Error in {func.__name__}: {str(e)} - {json.dumps(error_log)}")
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _serialize_args(args: tuple, kwargs: dict) -> dict:
    """Serialize function arguments for logging."""
    serialized = {}

    # Serialize positional arguments
    if args:
        serialized["positional"] = []
        for _i, arg in enumerate(args):
            try:
                # Skip client objects
                if hasattr(arg, "__class__") and "client" in arg.__class__.__name__.lower():
                    serialized["positional"].append("<SDK Client>")
                else:
                    serialized["positional"].append(_safe_serialize(arg))
            except Exception:
                serialized["positional"].append(f"<unserializable: {type(arg).__name__}>")

    # Serialize keyword arguments
    if kwargs:
        serialized["keyword"] = {}
        for key, value in kwargs.items():
            try:
                serialized["keyword"][key] = _safe_serialize(value)
            except Exception:
                serialized["keyword"][key] = f"<unserializable: {type(value).__name__}>"

    return serialized


def _safe_serialize(obj: Any, max_length: int = 200) -> Any:
    """Safely serialize an object for logging."""
    if obj is None or isinstance(obj, bool | int | float):
        return obj
    if isinstance(obj, str):
        return obj[:max_length] + "..." if len(obj) > max_length else obj
    if isinstance(obj, list | tuple):
        return [_safe_serialize(item, 50) for item in obj[:5]]
    if isinstance(obj, dict):
        return {k: _safe_serialize(v, 50) for k, v in list(obj.items())[:5]}
    if isinstance(obj, Path):
        return str(obj)
    return f"<{type(obj).__name__}>"


def _truncate_result(result: Any, max_length: int) -> Any:
    """Truncate result for logging."""
    try:
        if result is None:
            return None
        if isinstance(result, str):
            return result[:max_length] + "..." if len(result) > max_length else result
        if isinstance(result, list | dict):
            serialized = json.dumps(result, default=str)
            if len(serialized) > max_length:
                return serialized[:max_length] + "..."
            return result
        str_result = str(result)
        return str_result[:max_length] + "..." if len(str_result) > max_length else str_result
    except Exception:
        return f"<{type(result).__name__}>"
