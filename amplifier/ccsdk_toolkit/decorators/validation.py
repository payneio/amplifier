"""
Validation Decorator

Adds input/output validation to functions working with Claude Code SDK.
Supports Pydantic schemas, type checking, and error reporting.
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T", bound=BaseModel)


def with_validation(
    input_schema: type[BaseModel] | None = None,
    output_schema: type[BaseModel] | None = None,
    validate_types: bool = True,
    strict: bool = False,
    coerce: bool = True,
) -> Callable[[F], F]:
    """
    Add input/output validation to a function.

    Args:
        input_schema: Optional Pydantic model for input validation
        output_schema: Optional Pydantic model for output validation
        validate_types: Whether to validate against type hints
        strict: Whether to raise on validation errors (vs log and continue)
        coerce: Whether to attempt type coercion

    Returns:
        Decorated function with validation

    Example:
        class QueryInput(BaseModel):
            prompt: str
            max_tokens: int = 100

        class QueryOutput(BaseModel):
            result: str
            confidence: float

        @with_validation(input_schema=QueryInput, output_schema=QueryOutput)
        async def query_with_validation(client, prompt: str, max_tokens: int = 100):
            response = await client.query(prompt)
            return {"result": response.content, "confidence": 0.95}
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Validate input if schema provided
            if input_schema:
                try:
                    # Create input data from args and kwargs
                    input_data = _create_input_data(func, args, kwargs)

                    # Validate against schema
                    if coerce:
                        validated_input = input_schema(**input_data)
                        # Update kwargs with validated values
                        kwargs.update(validated_input.model_dump())
                    else:
                        # Just validate, don't coerce
                        input_schema.model_validate(input_data)

                except ValidationError as e:
                    msg = f"Input validation failed for {func.__name__}: {e}"
                    logger.error(msg)
                    if strict:
                        raise ValueError(msg) from e
                except Exception as e:
                    logger.warning(f"Input validation error in {func.__name__}: {e}")
                    if strict:
                        raise

            # Execute function
            result = await func(*args, **kwargs)

            # Validate output if schema provided
            if output_schema:
                try:
                    if isinstance(result, dict):
                        if coerce:
                            validated_output = output_schema(**result)
                            return validated_output.model_dump()
                        output_schema.model_validate(result)
                    elif isinstance(result, BaseModel):
                        if coerce and not isinstance(result, output_schema):
                            # Convert to target schema
                            validated_output = output_schema(**result.model_dump())
                            return validated_output
                    else:
                        # Try to construct from result
                        if coerce:
                            validated_output = output_schema(result=result)
                            return validated_output.model_dump()

                except ValidationError as e:
                    msg = f"Output validation failed for {func.__name__}: {e}"
                    logger.error(msg)
                    if strict:
                        raise ValueError(msg) from e
                except Exception as e:
                    logger.warning(f"Output validation error in {func.__name__}: {e}")
                    if strict:
                        raise

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Validate input if schema provided
            if input_schema:
                try:
                    # Create input data from args and kwargs
                    input_data = _create_input_data(func, args, kwargs)

                    # Validate against schema
                    if coerce:
                        validated_input = input_schema(**input_data)
                        # Update kwargs with validated values
                        kwargs.update(validated_input.model_dump())
                    else:
                        # Just validate, don't coerce
                        input_schema.model_validate(input_data)

                except ValidationError as e:
                    msg = f"Input validation failed for {func.__name__}: {e}"
                    logger.error(msg)
                    if strict:
                        raise ValueError(msg) from e
                except Exception as e:
                    logger.warning(f"Input validation error in {func.__name__}: {e}")
                    if strict:
                        raise

            # Execute function
            result = func(*args, **kwargs)

            # Validate output if schema provided
            if output_schema:
                try:
                    if isinstance(result, dict):
                        if coerce:
                            validated_output = output_schema(**result)
                            return validated_output.model_dump()
                        output_schema.model_validate(result)
                    elif isinstance(result, BaseModel):
                        if coerce and not isinstance(result, output_schema):
                            # Convert to target schema
                            validated_output = output_schema(**result.model_dump())
                            return validated_output
                    else:
                        # Try to construct from result
                        if coerce:
                            validated_output = output_schema(result=result)
                            return validated_output.model_dump()

                except ValidationError as e:
                    msg = f"Output validation failed for {func.__name__}: {e}"
                    logger.error(msg)
                    if strict:
                        raise ValueError(msg) from e
                except Exception as e:
                    logger.warning(f"Output validation error in {func.__name__}: {e}")
                    if strict:
                        raise

            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _create_input_data(func: Callable, args: tuple, kwargs: dict) -> dict:
    """Create input data dictionary from function arguments."""
    import inspect

    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    # Skip 'self' or 'cls' if present
    if params and params[0] in ("self", "cls"):
        params = params[1:]
        args = args[1:] if args else args

    # Skip client parameter (usually first)
    if params and "client" in params[0].lower():
        params = params[1:]
        args = args[1:] if args else args

    # Map positional arguments
    input_data = {}
    for i, param in enumerate(params):
        if i < len(args):
            input_data[param] = args[i]

    # Add keyword arguments
    input_data.update(kwargs)

    return input_data


def validate_response(
    schema: type[T],
    field_mapping: dict[str, str] | None = None,
    strict: bool = True,
) -> Callable[[F], F]:
    """
    Validate function response against a specific schema.

    Args:
        schema: Pydantic model to validate against
        field_mapping: Optional mapping of response fields to schema fields
        strict: Whether to raise on validation failure

    Returns:
        Decorated function that validates response

    Example:
        class AnalysisResult(BaseModel):
            summary: str
            issues: list[str]
            score: float

        @validate_response(AnalysisResult)
        async def analyze(client, code: str):
            response = await client.query(f"Analyze: {code}")
            return parse_llm_json(response.content)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return _validate_against_schema(result, schema, field_mapping, strict, func.__name__)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return _validate_against_schema(result, schema, field_mapping, strict, func.__name__)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _validate_against_schema(
    data: Any,
    schema: type[BaseModel],
    field_mapping: dict[str, str] | None,
    strict: bool,
    func_name: str,
) -> Any:
    """Validate data against a Pydantic schema."""
    try:
        # Apply field mapping if provided
        if field_mapping and isinstance(data, dict):
            mapped_data = {}
            for old_key, new_key in field_mapping.items():
                if old_key in data:
                    mapped_data[new_key] = data[old_key]
            data = {**data, **mapped_data}

        # Validate and return
        if isinstance(data, dict):
            validated = schema(**data)
            return validated.model_dump()
        if isinstance(data, BaseModel):
            if isinstance(data, schema):
                return data
            # Convert to target schema
            validated = schema(**data.model_dump())
            return validated
        # For non-dict data, try to wrap in a dict or create empty schema
        try:
            # Try to create empty schema and return original data if it fails
            validated = schema()
            return data  # Return original data if we can't validate it properly
        except (TypeError, ValueError):
            # Last resort: return original data
            return data

    except ValidationError as e:
        msg = f"Schema validation failed in {func_name}: {e}"
        logger.error(msg)
        if strict:
            raise ValueError(msg) from e
        return data  # Return original data if not strict

    except Exception as e:
        logger.warning(f"Validation error in {func_name}: {e}")
        if strict:
            raise
        return data
