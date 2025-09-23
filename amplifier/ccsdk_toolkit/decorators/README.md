# CCSDK Toolkit Decorators

Composable decorators that enhance functions working with Claude Code SDK clients. These decorators add capabilities without modifying the SDK itself, following the composition over inheritance principle.

## Overview

The decorators module provides optional enhancements for functions that work WITH the Claude Code SDK, not modifications TO the SDK. Each decorator is:

- **Composable** - Can be combined with other decorators
- **Optional** - Users choose which enhancements to apply
- **Non-invasive** - Doesn't modify the SDK client itself
- **Type-preserving** - Maintains function signatures and return types

## Installation

```python
from amplifier.ccsdk_toolkit.decorators import (
    with_retry,
    with_logging,
    with_defensive_parsing,
    with_timing,
    sdk_function,
    batch_operation
)
```

## Core Decorators

### 1. Retry Decorator (`@with_retry`)

Adds configurable retry logic with exponential backoff.

```python
from amplifier.ccsdk_toolkit.decorators import with_retry

@with_retry(attempts=3, backoff="exponential")
async def query_llm(client, prompt: str):
    return await client.query(prompt)

# With custom retry callback
def log_retry(error, attempt):
    print(f"Retry {attempt}: {error}")

@with_retry(attempts=5, on_retry=log_retry)
async def robust_query(client, prompt: str):
    return await client.query(prompt)
```

**Options:**
- `attempts`: Maximum retry attempts (default: 3)
- `backoff`: "exponential", "linear", or fixed delay
- `initial_delay`: Initial delay between retries
- `max_delay`: Maximum delay between retries
- `retryable_errors`: Tuple of exception types to retry
- `on_retry`: Callback function for retry events

### 2. Logging Decorator (`@with_logging`)

Adds structured logging to function calls.

```python
from amplifier.ccsdk_toolkit.decorators import with_logging

@with_logging(log_file="analysis.log", include_result=True)
async def analyze_code(client, code: str):
    return await client.query(f"Analyze: {code}")

# With custom logger
import logging
custom_logger = logging.getLogger("my_app")

@with_logging(custom_logger=custom_logger)
async def process_data(client, data: dict):
    return await client.query(str(data))
```

**Options:**
- `log_file`: Optional file path for logs
- `level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `include_args`: Whether to log function arguments
- `include_result`: Whether to log results
- `include_timing`: Whether to log execution time
- `custom_logger`: Optional custom logger instance

### 3. Defensive Parsing Decorator (`@with_defensive_parsing`)

Automatically extracts and parses JSON from LLM responses.

```python
from amplifier.ccsdk_toolkit.decorators import with_defensive_parsing

@with_defensive_parsing(extract_json=True)
async def get_structured_data(client, prompt: str):
    response = await client.query(f"Return JSON: {prompt}")
    return response  # Automatically parsed to dict/list

# With validation
@with_defensive_parsing(
    validate_structure={"result": str, "score": float},
    fallback_value={"result": "error", "score": 0.0}
)
async def get_analysis(client, text: str):
    return await client.query(f"Analyze: {text}")
```

**Options:**
- `extract_json`: Whether to extract JSON from response
- `validate_structure`: Optional structure validation
- `fallback_value`: Value to return if parsing fails
- `log_errors`: Whether to log parsing errors

### 4. Timing Decorator (`@with_timing`)

Tracks execution time and warns on slow operations.

```python
from amplifier.ccsdk_toolkit.decorators import with_timing, get_timing_stats

@with_timing(warn_threshold=30.0, track_stats=True)
async def slow_operation(client, data: str):
    return await client.query(f"Process: {data}")

# Get statistics
stats = get_timing_stats("slow_operation")
print(f"Average time: {stats['slow_operation']['avg']:.2f}s")
```

**Options:**
- `warn_threshold`: Warn if execution exceeds this many seconds
- `error_threshold`: Log error if execution exceeds this
- `track_stats`: Whether to track global statistics
- `include_args`: Whether to include args in timing logs

### 5. Cache Decorator (`@with_cache`)

Adds response caching with TTL and LRU eviction.

```python
from amplifier.ccsdk_toolkit.decorators import with_cache, clear_cache

@with_cache(ttl=300, max_size=100)
async def cached_analysis(client, code: str):
    return await client.query(f"Analyze: {code}")

# Clear cache manually
clear_cache("cached_analysis")

# Get cache info
info = cached_analysis.cache_info()
print(f"Cache hits: {info['hits']}, misses: {info['misses']}")
```

**Options:**
- `ttl`: Time to live in seconds (None = no expiration)
- `max_size`: Maximum cache size
- `cache_key_func`: Custom cache key generator
- `skip_args`: List of argument indices to skip in cache key

### 6. Progress Tracking Decorator (`@with_progress`)

Adds progress tracking for long operations.

```python
from amplifier.ccsdk_toolkit.decorators import with_progress

def print_progress(progress: float, message: str):
    print(f"{progress:.1%} - {message}")

@with_progress(callback=print_progress, show_eta=True)
async def process_items(client, items: list, update_progress=None):
    results = []
    for i, item in enumerate(items):
        result = await client.query(str(item))
        results.append(result)
        if update_progress:
            update_progress(i + 1, len(items))
    return results
```

**Options:**
- `callback`: Progress callback function
- `total_steps`: Total number of steps
- `report_interval`: Minimum seconds between reports
- `show_eta`: Whether to calculate ETA

### 7. Validation Decorator (`@with_validation`)

Validates inputs/outputs against Pydantic schemas.

```python
from amplifier.ccsdk_toolkit.decorators import with_validation
from pydantic import BaseModel

class QueryInput(BaseModel):
    prompt: str
    max_tokens: int = 100

class QueryOutput(BaseModel):
    result: str
    confidence: float

@with_validation(input_schema=QueryInput, output_schema=QueryOutput)
async def validated_query(client, prompt: str, max_tokens: int = 100):
    response = await client.query(prompt)
    return {
        "result": response.content,
        "confidence": 0.95
    }
```

**Options:**
- `input_schema`: Pydantic model for input validation
- `output_schema`: Pydantic model for output validation
- `validate_types`: Whether to validate type hints
- `strict`: Whether to raise on validation errors
- `coerce`: Whether to attempt type coercion

## Advanced Patterns

### SDK Function Pattern

Combines common enhancements in one decorator:

```python
from amplifier.ccsdk_toolkit.decorators import sdk_function

@sdk_function(
    retry_attempts=3,
    enable_logging=True,
    parse_json=True,
    cache_ttl=300
)
async def enhanced_query(client, prompt: str):
    return await client.query(prompt)
```

### Batch Operation Pattern

Enhanced batch processing with error handling:

```python
from amplifier.ccsdk_toolkit.decorators import batch_operation

@batch_operation(batch_size=5, parallel=True, retry_per_item=True)
async def analyze_files(client, files: list[Path]):
    results = []
    for file in files:
        content = file.read_text()
        result = await client.query(f"Analyze: {content}")
        results.append(result)
    return results
```

### Robust SDK Function

Maximum protection for critical operations:

```python
from amplifier.ccsdk_toolkit.decorators import robust_sdk_function

@robust_sdk_function(
    max_retries=5,
    cache_ttl=3600,
    warn_threshold=30.0,
    log_file="critical_ops.log"
)
async def critical_operation(client, data: dict):
    import json
    return await client.query(f"Critical: {json.dumps(data)}")
```

## Combining Decorators

Decorators can be combined for comprehensive functionality:

```python
from amplifier.ccsdk_toolkit.decorators import (
    with_retry,
    with_logging,
    with_timing,
    with_defensive_parsing,
    with_cache
)

@with_logging(log_file="app.log")
@with_timing(warn_threshold=60.0)
@with_cache(ttl=600)
@with_retry(attempts=3)
@with_defensive_parsing(extract_json=True)
async def comprehensive_analysis(client, code: str):
    """Fully enhanced function with all protections."""
    response = await client.query(f"Analyze this code: {code}")
    return response
```

**Order matters!** Decorators are applied from bottom to top:
1. `with_defensive_parsing` - Innermost, processes response first
2. `with_retry` - Retries the parsing operation if needed
3. `with_cache` - Caches successful results
4. `with_timing` - Times the entire cached operation
5. `with_logging` - Logs everything including timing

## Real-World Examples

### Example 1: Robust Document Processing

```python
from pathlib import Path
from amplifier.ccsdk_toolkit.decorators import (
    batch_operation,
    with_logging,
    with_progress
)

def progress_callback(completed: int, total: int, message: str):
    print(f"[{completed}/{total}] {message}")

@with_logging(log_file="document_processing.log")
@batch_operation(batch_size=10, parallel=True)
@with_progress(callback=progress_callback)
async def process_documents(client, doc_paths: list[Path]):
    """Process multiple documents with progress tracking."""
    results = []
    for path in doc_paths:
        content = path.read_text()
        result = await client.query(f"Summarize: {content[:5000]}")
        results.append({
            "file": path.name,
            "summary": result.content
        })
    return results

# Usage
doc_paths = list(Path("docs").glob("*.md"))
summaries = await process_documents(client, doc_paths)
```

### Example 2: Cached API with Validation

```python
from pydantic import BaseModel, Field
from amplifier.ccsdk_toolkit.decorators import (
    with_cache,
    with_validation,
    with_retry
)

class CodeAnalysis(BaseModel):
    complexity: int = Field(ge=1, le=10)
    issues: list[str]
    suggestions: list[str]

@with_cache(ttl=3600, max_size=1000)
@with_validation(output_schema=CodeAnalysis, strict=True)
@with_retry(attempts=3)
async def analyze_code_quality(client, code: str) -> dict:
    """Analyze code quality with caching and validation."""
    prompt = f"""
    Analyze this code and return JSON:
    {{
        "complexity": <1-10>,
        "issues": ["list of issues"],
        "suggestions": ["list of improvements"]
    }}

    Code:
    {code}
    """
    response = await client.query(prompt)
    # Parse and return (will be validated)
    from amplifier.ccsdk_toolkit.defensive import parse_llm_json
    return parse_llm_json(response.content)
```

### Example 3: Monitoring Slow Operations

```python
from amplifier.ccsdk_toolkit.decorators import (
    with_timing,
    with_timeout,
    get_timing_stats
)

@with_timeout(timeout_seconds=120.0)
@with_timing(warn_threshold=30.0, error_threshold=60.0)
async def deep_analysis(client, data: str):
    """Deep analysis with timeout and performance monitoring."""
    return await client.query(f"Deep analysis required: {data}")

# Monitor performance
for i in range(10):
    await deep_analysis(client, f"Data batch {i}")

# Check statistics
stats = get_timing_stats("deep_analysis")
if stats:
    print(f"Analysis performance:")
    print(f"  Min: {stats['deep_analysis']['min']:.2f}s")
    print(f"  Max: {stats['deep_analysis']['max']:.2f}s")
    print(f"  Avg: {stats['deep_analysis']['avg']:.2f}s")
```

## Best Practices

1. **Order decorators thoughtfully** - Inner decorators execute first
2. **Use `sdk_function` for common cases** - Avoid decorator soup
3. **Enable caching for expensive operations** - But set appropriate TTL
4. **Always add retry for network operations** - LLM APIs can be flaky
5. **Use validation for structured outputs** - Catch issues early
6. **Track timing for performance monitoring** - Identify bottlenecks
7. **Log critical operations** - But avoid logging sensitive data

## Performance Considerations

- **Caching**: Reduces API calls but uses memory
- **Parallel batch operations**: Faster but higher resource usage
- **Retry logic**: Increases reliability but may increase latency
- **Validation**: Adds overhead but catches errors early
- **Logging**: I/O overhead, use async loggers for high throughput

## Troubleshooting

### Decorator not working
- Check decorator order - they apply bottom to top
- Ensure function is properly async/sync
- Verify decorator parameters are correct

### Cache not hitting
- Check cache key generation with `skip_args`
- Verify TTL hasn't expired
- Monitor cache size limits

### Validation failures
- Use `strict=False` for development
- Check schema matches actual data structure
- Enable `coerce=True` for type conversion

### Performance issues
- Reduce batch sizes for memory constraints
- Adjust retry delays and attempts
- Consider disabling some decorators for debugging

## Module Contract

This module provides composable decorators that:
- Enhance functions working with SDK clients
- Don't modify the SDK itself
- Can be combined in any order
- Preserve function signatures
- Support both sync and async functions
- Provide optional functionality

The decorators are self-contained and can be regenerated from this specification.