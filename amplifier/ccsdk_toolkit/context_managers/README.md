# Context Managers for Claude Code SDK

Focused, single-purpose context managers for common patterns when working with the Claude Code SDK. Each manager provides clean resource management and integrates seamlessly with the SDK's utilities and helpers.

## Overview

The context managers module provides specialized async context managers that handle specific use cases:

- **FileProcessor**: Batch file processing with progress tracking
- **StreamingQuery**: Streaming AI responses with progress indicators
- **SessionContext**: Conversation session management with persistence
- **TimedExecution**: Execution timing and timeout handling
- **RetryContext**: Configurable retry strategies with error recovery

## Installation

```python
from amplifier.ccsdk_toolkit.context_managers import (
    FileProcessor,
    StreamingQuery,
    SessionContext,
    TimedExecution,
    RetryContext,
    RetryStrategy
)
```

## Context Managers

### FileProcessor

Process files in batches with automatic progress tracking and resource cleanup.

```python
from amplifier.ccsdk_toolkit.client import ClaudeCodeSDKClient
from amplifier.ccsdk_toolkit.context_managers import FileProcessor

client = ClaudeCodeSDKClient()

# Process all Python files
async with FileProcessor(client, pattern="**/*.py") as processor:
    # Process with a custom function
    async def analyze_file(path, content):
        return await client.query_with_retry(f"Analyze: {content[:500]}")

    results = await processor.process_batch(analyze_file)
    print(f"Processed {len(results)} files")

# Process with prompt template
async with FileProcessor(client, pattern="**/*.md") as processor:
    template = "Summarize this document:\n{content}"
    summaries = await processor.process_with_prompt(template)
```

**Features:**
- Automatic file discovery with glob patterns
- Parallel batch processing
- Progress tracking
- Error collection and reporting
- Filter functions for selective processing

### StreamingQuery

Stream AI responses with progress indicators and proper cleanup.

```python
from amplifier.ccsdk_toolkit.context_managers import StreamingQuery

# Stream with progress display
async with StreamingQuery(client, show_progress=True) as query:
    # Get complete response with streaming display
    response = await query.ask("Generate a detailed analysis")

    # Or stream chunks directly
    async for chunk in query.stream("Generate documentation"):
        print(chunk, end="", flush=True)

# Multi-turn conversation with streaming
async with StreamingQuery(client) as query:
    prompts = [
        "What is Python?",
        "How does it compare to JavaScript?",
        "Which should I learn first?"
    ]
    responses = await query.multi_turn_conversation(prompts)
```

**Features:**
- Real-time streaming output
- Progress tracking for chunks
- Fallback for non-streaming clients
- Multi-turn conversations
- Response buffering

### SessionContext

Manage conversation sessions with automatic persistence and context preservation.

```python
from amplifier.ccsdk_toolkit.context_managers import SessionContext

# Create a persistent session
async with SessionContext(client, session_name="analysis") as session:
    # Queries maintain conversation context
    response1 = await session.query("What is this code doing?")
    response2 = await session.query("Can you improve it?")
    response3 = await session.query("Add error handling")

    # Session automatically saved on exit
    print(f"Session complete with {session.query_count} queries")

# Resume a previous session
async with SessionContext(client, session_name="analysis") as session:
    # Automatically loads previous conversation
    response = await session.query("Continue from where we left off")

    # Generate summary of conversation
    summary = await session.summarize_session()
```

**Features:**
- Automatic session persistence to JSON
- Conversation history management
- Context preservation across queries
- Session resumption
- Auto-save at intervals
- Session summarization

### TimedExecution

Track execution time and enforce timeout limits with detailed metrics.

```python
from amplifier.ccsdk_toolkit.context_managers import TimedExecution

# Execute with 5-minute timeout
async with TimedExecution(client, timeout_minutes=5) as timer:
    response = await timer.query_with_timeout("Complex analysis task")
    print(f"Completed in {timer.elapsed_time:.2f} seconds")
    print(f"Remaining time: {timer.remaining_time:.2f} seconds")

# Batch processing with timeout
async with TimedExecution(client, timeout_minutes=10) as timer:
    prompts = ["Task 1", "Task 2", "Task 3"]
    results = await timer.batch_with_timeout(
        prompts,
        continue_on_timeout=True
    )

    # Get performance metrics
    metrics = timer.metrics
    print(f"Average query time: {metrics['average_query_time']:.2f}s")
```

**Features:**
- Global and per-query timeouts
- Warning thresholds
- Performance metrics tracking
- Progress callbacks
- Deadline calculation
- Timeout-resilient batch processing

### RetryContext

Implement robust retry strategies with various backoff algorithms.

```python
from amplifier.ccsdk_toolkit.context_managers import RetryContext, RetryStrategy

# Exponential backoff retry
async with RetryContext(
    client,
    max_retries=5,
    backoff="exponential"
) as retry:
    response = await retry.robust_query("Analyze this dataset")
    print(f"Succeeded after {retry.attempt_count} attempts")

# Custom retry with error callback
async def on_error(error, attempt):
    print(f"Attempt {attempt} failed: {error}")

async with RetryContext(client, backoff="fibonacci") as retry:
    response = await retry.robust_query(
        "Process document",
        error_callback=on_error
    )

# Fallback pattern
async with RetryContext(client) as retry:
    async def primary():
        return await expensive_api_call()

    async def fallback():
        return await cached_response()

    result = await retry.with_fallback(primary, fallback)
```

**Features:**
- Multiple backoff strategies (linear, exponential, fibonacci, random jitter)
- Error callbacks
- Fallback functions
- Circuit breaker pattern
- Batch retry processing
- Comprehensive failure logging

## Advanced Usage

### Combining Context Managers

Context managers can be combined for complex workflows:

```python
# File processing with timeout and retry
async with TimedExecution(client, timeout_minutes=30) as timer:
    async with RetryContext(client, max_retries=3) as retry:
        async with FileProcessor(client, pattern="**/*.py") as processor:

            async def robust_analyze(path, content):
                return await retry.robust_query(
                    f"Analyze {path}: {content[:500]}"
                )

            results = await processor.process_batch(robust_analyze)

            print(f"Processed {len(results)} files")
            print(f"Time taken: {timer.elapsed_time:.2f}s")
            print(f"Retry statistics: {retry.statistics}")
```

### Session with Streaming

```python
# Streaming responses within a session
async with SessionContext(client, "chat") as session:
    async with StreamingQuery(client) as stream:

        # First query with streaming
        print("AI: ", end="")
        async for chunk in stream.stream("Hello! How can I help?"):
            print(chunk, end="", flush=True)
        print()

        # Save to session
        response = stream.buffered_response
        await session.query("User said hello", save_immediately=True)
```

### Progress Monitoring

```python
# Complex task with comprehensive progress monitoring
async def process_with_monitoring():
    async with TimedExecution(client, timeout_minutes=60) as timer:

        async def progress_callback(info):
            print(f"Status: {info['status']}")
            print(f"Elapsed: {info['elapsed']:.1f}s")
            print(f"Remaining: {info['remaining']:.1f}s")

        # Process with progress updates
        response = await timer.with_progress_callback(
            "Long running task",
            progress_callback
        )

        return response, timer.metrics
```

## Error Handling

All context managers provide comprehensive error handling:

```python
try:
    async with FileProcessor(client) as processor:
        results = await processor.process_batch(analyze_func)

        # Check for failures
        if processor.errors:
            print(f"Failed files: {len(processor.errors)}")
            for path, error in processor.errors.items():
                print(f"  {path}: {error}")

except Exception as e:
    print(f"Critical error: {e}")
```

## Performance Considerations

- **FileProcessor**: Batches files to avoid overwhelming the API
- **StreamingQuery**: Reduces memory usage for large responses
- **SessionContext**: Auto-saves prevent data loss
- **TimedExecution**: Prevents runaway operations
- **RetryContext**: Implements exponential backoff to avoid rate limits

## Best Practices

1. **Choose the right manager**: Each manager is optimized for specific use cases
2. **Combine managers thoughtfully**: Layer managers for complex workflows
3. **Handle errors gracefully**: All managers provide error information
4. **Monitor progress**: Use progress features for long-running operations
5. **Clean up resources**: Context managers handle cleanup automatically

## API Reference

See individual module docstrings for detailed API documentation:

- `file_processing.py`: FileProcessor API
- `streaming.py`: StreamingQuery API
- `session_context.py`: SessionContext API
- `timed_execution.py`: TimedExecution API
- `retry_context.py`: RetryContext API

## Contributing

When adding new context managers:

1. Follow the single-purpose principle
2. Accept initialized SDK client, don't create one
3. Implement proper `__aenter__` and `__aexit__` methods
4. Provide comprehensive error handling
5. Include usage examples in docstrings
6. Add type hints for all parameters and returns