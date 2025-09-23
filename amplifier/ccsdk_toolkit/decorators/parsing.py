"""
Defensive Parsing Decorator

Adds defensive response parsing to functions working with Claude Code SDK.
Automatically extracts and parses JSON from LLM responses.
"""

import asyncio
import functools
import json
import logging
from collections.abc import Callable
from typing import Any
from typing import TypeVar

# Import defensive utilities from the toolkit
from amplifier.ccsdk_toolkit.defensive import parse_llm_json

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


def with_defensive_parsing(
    extract_json: bool = True,
    validate_structure: dict | None = None,
    fallback_value: Any = None,
    log_errors: bool = True,
) -> Callable[[F], F]:
    """
    Add defensive parsing to LLM response handling.

    Args:
        extract_json: Whether to extract JSON from response text
        validate_structure: Optional dictionary defining expected structure
        fallback_value: Value to return if parsing fails (None = raise error)
        log_errors: Whether to log parsing errors

    Returns:
        Decorated function with defensive parsing

    Example:
        @with_defensive_parsing(extract_json=True)
        async def get_analysis(client, code: str):
            response = await client.query(f"Analyze and return JSON: {code}")
            return response  # Automatically parsed to dict/list
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return _parse_response(
                    result, extract_json, validate_structure, fallback_value, log_errors, func.__name__
                )
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                if fallback_value is not None:
                    return fallback_value
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return _parse_response(
                    result, extract_json, validate_structure, fallback_value, log_errors, func.__name__
                )
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                if fallback_value is not None:
                    return fallback_value
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _parse_response(
    response: Any,
    extract_json: bool,
    validate_structure: dict | None,
    fallback_value: Any,
    log_errors: bool,
    func_name: str,
) -> Any:
    """Parse and validate LLM response."""
    # Handle different response types
    if hasattr(response, "content"):
        # Response object from SDK
        content = response.content
    elif isinstance(response, str):
        content = response
    elif isinstance(response, dict | list):
        # Already parsed
        content = response
    else:
        # Unknown type, return as-is
        return response

    # Extract JSON if requested
    if extract_json and isinstance(content, str):
        try:
            parsed = parse_llm_json(content)
            if parsed is not None:
                content = parsed
            else:
                # parse_llm_json returned None, try basic JSON parse
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    if log_errors:
                        logger.warning(f"Could not extract JSON from response in {func_name}")
                    if fallback_value is not None:
                        return fallback_value
                    # Return original string if no fallback
                    return content
        except Exception as e:
            if log_errors:
                logger.error(f"Error parsing JSON in {func_name}: {str(e)}")
            if fallback_value is not None:
                return fallback_value
            raise

    # Validate structure if provided
    if validate_structure and isinstance(content, dict) and not _validate_dict_structure(content, validate_structure):
        if log_errors:
            logger.warning(
                f"Response structure validation failed in {func_name}. "
                f"Expected: {validate_structure}, Got: {list(content.keys())}"
            )
        if fallback_value is not None:
            return fallback_value

    return content


def _validate_dict_structure(data: dict, expected: dict) -> bool:
    """Validate dictionary structure against expected template."""
    for key, value_type in expected.items():
        if key not in data:
            return False
        if value_type is not None and not isinstance(data[key], value_type):
            # Check type if specified
            return False
    return True


def with_json_response(
    required_keys: list[str] | None = None,
    optional_keys: list[str] | None = None,
    strict: bool = False,
) -> Callable[[F], F]:
    """
    Decorator specifically for functions that should return JSON.

    Args:
        required_keys: List of keys that must be present in response
        optional_keys: List of keys that may be present
        strict: If True, no additional keys allowed beyond required+optional

    Returns:
        Decorated function that ensures JSON response

    Example:
        @with_json_response(required_keys=["result", "status"])
        async def analyze(client, prompt: str):
            return await client.query(prompt)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return _validate_json_response(result, required_keys, optional_keys, strict, func.__name__)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return _validate_json_response(result, required_keys, optional_keys, strict, func.__name__)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _validate_json_response(
    response: Any,
    required_keys: list[str] | None,
    optional_keys: list[str] | None,
    strict: bool,
    func_name: str,
) -> dict:
    """Validate and return JSON response."""
    # Parse response to JSON
    if hasattr(response, "content"):
        content = response.content
    elif isinstance(response, str | dict):
        content = response
    else:
        raise ValueError(f"Unexpected response type in {func_name}: {type(response)}")

    # Parse JSON if string
    if isinstance(content, str):
        parsed = parse_llm_json(content)
        if parsed is None:
            raise ValueError(f"Could not parse JSON from response in {func_name}")
        content = parsed

    # Validate it's a dictionary
    if not isinstance(content, dict):
        raise ValueError(f"Expected dict response in {func_name}, got {type(content)}")

    # Check required keys
    if required_keys:
        missing = [key for key in required_keys if key not in content]
        if missing:
            raise ValueError(f"Missing required keys in {func_name}: {missing}")

    # Check strict mode
    if strict and (required_keys or optional_keys):
        allowed = set(required_keys or []) | set(optional_keys or [])
        extra = [key for key in content if key not in allowed]
        if extra:
            raise ValueError(f"Unexpected keys in {func_name}: {extra}")

    return content
