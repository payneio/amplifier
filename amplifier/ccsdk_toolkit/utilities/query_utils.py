"""
Query utilities for claude-code-sdk

Provides retry logic, response parsing, and batch processing for SDK queries.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from amplifier.ccsdk_toolkit.defensive import parse_llm_json

logger = logging.getLogger(__name__)


async def query_with_retry(
    client: Any,
    prompt: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Any:
    """Query SDK with automatic retry on failure.

    Args:
        client: ClaudeSDKClient instance
        prompt: Query prompt
        max_retries: Maximum retry attempts
        retry_delay: Initial delay between retries (exponential backoff)

    Returns:
        SDK response object

    Raises:
        RuntimeError: After all retries exhausted

    Example:
        >>> client = ClaudeSDKClient()
        >>> response = await query_with_retry(client, "Hello")
    """
    last_error = None
    delay = retry_delay

    for attempt in range(max_retries):
        try:
            # Use the client's query method directly
            response = await client.query(prompt)
            return response
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(f"Query attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries} query attempts failed")

    raise RuntimeError(f"Query failed after {max_retries} attempts: {last_error}")


def parse_sdk_response(response: Any) -> dict[str, Any]:
    """Parse SDK response object into clean dictionary.

    Args:
        response: SDK response object

    Returns:
        Parsed dictionary with content and metadata

    Example:
        >>> response = await client.query("Hello")
        >>> data = parse_sdk_response(response)
        >>> print(data['content'])
    """
    # Handle different response types
    result: dict[str, Any]
    if hasattr(response, "__dict__"):
        # Convert object to dict
        result = dict(vars(response))
    elif isinstance(response, dict):
        result = dict(response)
    elif isinstance(response, str):
        # Try to parse as JSON if string
        parsed = parse_llm_json(response)
        if parsed:
            result = dict(parsed)
        else:
            result = {"content": response}
    else:
        result = {"content": str(response)}

    # Ensure we have required fields
    if "content" not in result:
        # Try to extract content from various fields
        if "text" in result:
            result["content"] = result["text"]
        elif "message" in result:
            result["content"] = result["message"]
        elif "response" in result:
            result["content"] = result["response"]
        else:
            # Fallback to string representation
            result["content"] = str(response)

    return result


def extract_text_content(response: Any) -> str:
    """Extract plain text content from SDK response.

    Args:
        response: SDK response object

    Returns:
        Plain text content

    Example:
        >>> response = await client.query("Hello")
        >>> text = extract_text_content(response)
    """
    parsed = parse_sdk_response(response)
    content = parsed.get("content", "")

    # Handle nested content structures
    if isinstance(content, dict):
        # Look for text fields
        for key in ["text", "message", "content", "response"]:
            if key in content:
                return str(content[key])
        return str(content)

    return str(content)


async def batch_query(
    client: Any,
    prompts: list[str],
    max_concurrent: int = 5,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Any]:
    """Process multiple prompts in parallel with concurrency control.

    Args:
        client: ClaudeSDKClient instance
        prompts: List of prompts to process
        max_concurrent: Maximum concurrent queries
        on_progress: Optional callback(completed, total)

    Returns:
        List of responses in same order as prompts

    Example:
        >>> prompts = ["Question 1", "Question 2", "Question 3"]
        >>> responses = await batch_query(client, prompts, max_concurrent=2)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[Any] = [None] * len(prompts)
    completed = 0

    async def process_prompt(index: int, prompt: str) -> None:
        """Process single prompt with concurrency control."""
        nonlocal completed
        async with semaphore:
            try:
                response = await query_with_retry(client, prompt)
                results[index] = response
            except Exception as e:
                logger.error(f"Failed to process prompt {index}: {e}")
                error_result: dict[str, Any] = {"error": str(e), "prompt": prompt}
                results[index] = error_result
            finally:
                completed += 1
                if on_progress:
                    on_progress(completed, len(prompts))

    # Create tasks for all prompts
    tasks = [process_prompt(i, prompt) for i, prompt in enumerate(prompts)]

    # Wait for all to complete
    await asyncio.gather(*tasks)

    return results
