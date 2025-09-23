#!/usr/bin/env python3
"""
Example usage of CCSDK Toolkit Decorators

This file demonstrates how to use the decorators with Claude Code SDK.
Run with: python -m amplifier.ccsdk_toolkit.decorators.example_usage
"""

import asyncio
import json
from collections.abc import Callable

from pydantic import BaseModel
from pydantic import Field

# Import decorators
from amplifier.ccsdk_toolkit.decorators import batch_operation

# from amplifier.ccsdk_toolkit.decorators import robust_sdk_function  # Not implemented
from amplifier.ccsdk_toolkit.decorators import sdk_function
from amplifier.ccsdk_toolkit.decorators import with_cache
from amplifier.ccsdk_toolkit.decorators import with_defensive_parsing
from amplifier.ccsdk_toolkit.decorators import with_logging
from amplifier.ccsdk_toolkit.decorators import with_progress
from amplifier.ccsdk_toolkit.decorators import with_retry
from amplifier.ccsdk_toolkit.decorators import with_timing
from amplifier.ccsdk_toolkit.decorators import with_validation


# Mock response class for demonstration
class MockResponse:
    """Mock response object with content attribute."""

    def __init__(self, content: str):
        self.content = content


# Mock client for demonstration (replace with actual ClaudeSDKClient)
class MockClient:
    """Mock client for demonstration purposes."""

    async def query(self, prompt: str) -> "MockResponse":
        """Simulate an LLM query."""
        await asyncio.sleep(0.1)  # Simulate network delay

        # Return different responses based on prompt
        if "analyze" in prompt.lower():
            return MockResponse('{"analysis": "Code looks good", "score": 8.5, "issues": []}')
        if "summarize" in prompt.lower():
            return MockResponse("This is a summary of the content.")
        if "json" in prompt.lower():
            return MockResponse('```json\n{"result": "success", "data": [1, 2, 3]}\n```')
        return MockResponse(f"Processed: {prompt[:50]}")


# Example 1: Basic retry with logging
@with_logging(include_result=True)
@with_retry(attempts=3, backoff="exponential")
async def simple_query(client: MockClient, prompt: str) -> str:
    """Simple query with retry and logging."""
    response = await client.query(prompt)
    return response.content


# Example 2: SDK function with common enhancements
@sdk_function(retry_attempts=3, cache_ttl=60, parse_json=True)
async def analyze_code(client: MockClient, code: str) -> dict:
    """Analyze code with SDK enhancements."""
    response = await client.query(f"Analyze this code: {code}")
    # The decorator will parse this JSON string into a dict
    return {"raw": response.content}  # Wrapped to ensure dict return type


# Example 3: Defensive parsing with fallback
@with_defensive_parsing(extract_json=True, fallback_value={"error": "Failed to parse"}, log_errors=True)
async def get_json_response(client: MockClient, prompt: str) -> dict:
    """Get JSON response with defensive parsing."""
    response = await client.query(f"Return JSON for: {prompt}")
    # The decorator will extract and parse JSON from response.content
    return {"raw": response.content}  # Wrapped to ensure dict return type


# Example 4: Validation with Pydantic schemas
class AnalysisInput(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field(default="python")
    max_issues: int = Field(default=10, ge=1, le=100)


class AnalysisOutput(BaseModel):
    analysis: str
    score: float = Field(ge=0, le=10)
    issues: list[str] = Field(default_factory=list)


@with_validation(input_schema=AnalysisInput, output_schema=AnalysisOutput)
@with_defensive_parsing(extract_json=True)
async def validated_analysis(client: MockClient, code: str, language: str = "python", max_issues: int = 10) -> dict:
    """Analyze with input/output validation."""
    prompt = f"Analyze this {language} code (max {max_issues} issues): {code}"
    response = await client.query(prompt)
    return {"raw": response.content}  # Wrapped to ensure dict return type


# Example 5: Batch operation with progress
def print_progress(completed: int, total: int, message: str):
    """Progress callback for batch operations."""
    progress = completed / total if total > 0 else 0
    print(f"[{progress:.0%}] {completed}/{total} - {message}")


@batch_operation(batch_size=3, parallel=True, progress_callback=print_progress)
async def process_files(client: MockClient, files: list[str]) -> list[str]:
    """Process multiple files in batches."""
    results = []
    for file in files:
        response = await client.query(f"Summarize file: {file}")
        results.append(response.content)
    return results


# Example 6: Caching with timing
@with_timing(warn_threshold=1.0)
@with_cache(ttl=300, max_size=50)
async def expensive_operation(client: MockClient, data: str) -> str:
    """Expensive operation with caching."""
    response = await client.query(f"Complex processing: {data}")
    return response.content


# Example 7: Robust function for critical operations (using available decorators)
@sdk_function(retry_attempts=5, cache_ttl=600, parse_json=False)
async def critical_operation(client: MockClient, critical_data: dict) -> str:
    """Critical operation with maximum protection."""
    prompt = f"Process critical data: {json.dumps(critical_data)}"
    response = await client.query(prompt)
    return str(response.content)


# Example 8: Progress tracking for long operations
@with_progress(show_eta=True, description="Processing items")
async def long_operation(client: MockClient, items: list[str], update_progress: Callable | None = None) -> list[str]:
    """Long operation with progress tracking."""
    results = []
    for i, item in enumerate(items):
        response = await client.query(f"Process: {item}")
        results.append(response.content)
        if update_progress:
            update_progress(i + 1, len(items))
    return results


# Example 9: Combined decorators for comprehensive functionality
@with_logging(log_file="comprehensive.log")
@with_timing(warn_threshold=5.0)
@with_cache(ttl=600)
@with_retry(attempts=3)
@with_defensive_parsing(extract_json=True)
async def comprehensive_function(client: MockClient, prompt: str) -> dict:
    """Function with all enhancements combined."""
    response = await client.query(f"Return JSON data for: {prompt}")
    return {"raw": response.content}  # Wrapped to ensure dict return type


async def main():
    """Run examples."""
    client = MockClient()

    print("=" * 60)
    print("CCSDK Toolkit Decorators - Example Usage")
    print("=" * 60)

    # Example 1: Simple query
    print("\n1. Simple query with retry and logging:")
    result = await simple_query(client, "Hello, Claude!")
    print(f"Result: {result}")

    # Example 2: SDK function
    print("\n2. SDK function with enhancements:")
    code = "def hello(): print('Hello')"
    result = await analyze_code(client, code)
    print(f"Analysis: {result}")

    # Example 3: Defensive parsing
    print("\n3. Defensive JSON parsing:")
    result = await get_json_response(client, "test data")
    print(f"Parsed JSON: {result}")

    # Example 4: Validation
    print("\n4. Validated analysis:")
    try:
        result = await validated_analysis(client, "print('test')", language="python")
        print(f"Validated result: {result}")
    except ValueError as e:
        print(f"Validation error: {e}")

    # Example 5: Batch operation
    print("\n5. Batch processing:")
    files = [f"file_{i}.py" for i in range(10)]
    results = await process_files(client, files)
    print(f"Processed {len(results)} files")

    # Example 6: Caching demonstration
    print("\n6. Caching demonstration:")
    data = "expensive data"

    # First call - cache miss
    print("First call (cache miss):")
    result1 = await expensive_operation(client, data)
    print(f"Result 1: {result1}")

    # Second call - cache hit
    print("Second call (cache hit):")
    result2 = await expensive_operation(client, data)
    print(f"Result 2 (cached): {result2}")

    # Check cache info
    cache_info = expensive_operation.cache_info()
    print(f"Cache stats: hits={cache_info['hits']}, misses={cache_info['misses']}")

    # Example 7: Critical operation
    print("\n7. Critical operation:")
    critical_data = {"user_id": 123, "action": "important"}
    result = await critical_operation(client, critical_data)
    print(f"Critical result: {result}")

    # Example 8: Progress tracking
    print("\n8. Long operation with progress:")
    items = [f"item_{i}" for i in range(5)]
    results = await long_operation(client, items)
    print(f"Completed {len(results)} items")

    # Example 9: Comprehensive function
    print("\n9. Comprehensive function:")
    result = await comprehensive_function(client, "complex request")
    print(f"Comprehensive result: {result}")

    # Show timing statistics
    print("\n" + "=" * 60)
    print("Timing Statistics:")
    from amplifier.ccsdk_toolkit.decorators.timing import get_timing_stats

    stats = get_timing_stats()
    for func_name, func_stats in stats.items():
        print(f"\n{func_name}:")
        print(f"  Calls: {func_stats['count']}")
        print(f"  Avg: {func_stats['avg']:.3f}s")
        print(f"  Min: {func_stats['min']:.3f}s")
        print(f"  Max: {func_stats['max']:.3f}s")

    # Show cache statistics
    print("\n" + "=" * 60)
    print("Cache Statistics:")
    from amplifier.ccsdk_toolkit.decorators.cache import get_cache_info

    cache_stats = get_cache_info()
    for cache_name, cache_info in cache_stats.items():
        print(f"\n{cache_name}:")
        print(f"  Size: {cache_info['size']}")
        print(f"  Hits: {cache_info['hits']}")
        print(f"  Misses: {cache_info['misses']}")
        print(f"  Evictions: {cache_info['evictions']}")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
