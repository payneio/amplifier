# Migration Guide: From ClaudeSession to Direct SDK Patterns

## Overview

The CCSDK Toolkit is evolving to embrace direct SDK usage with focused utilities, rather than wrapping the SDK in a monolithic session class. This guide helps you migrate from the deprecated `ClaudeSession` wrapper to the new, more flexible architecture.

## Why Migrate?

### Benefits of the New Architecture

1. **Better Performance**: Direct SDK calls without wrapper overhead
2. **Greater Flexibility**: Mix and match utilities as needed
3. **Clearer Code**: Explicit operations instead of hidden complexity
4. **Easier Testing**: Test individual utilities in isolation
5. **Future-Proof**: Aligned with SDK evolution and best practices

### Timeline

- **v2.0.0** (Current): ClaudeSession deprecated, new patterns recommended
- **v2.x**: ClaudeSession maintained for compatibility with deprecation warnings
- **v3.0.0** (Future): ClaudeSession removed entirely

## Quick Migration Examples

### Basic Query

**Old Pattern (ClaudeSession)**:
```python
from amplifier.ccsdk_toolkit import ClaudeSession, SessionOptions

async def analyze_text(text: str):
    options = SessionOptions(
        retry_attempts=3,
        retry_delay=1.0
    )

    async with ClaudeSession(options) as session:
        response = await session.query(f"Analyze this: {text}")
        return response.content
```

**New Pattern (Direct SDK)**:
```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import query_with_retry
from amplifier.ccsdk_toolkit.defensive import parse_llm_json

async def analyze_text(text: str):
    client = ClaudeSDKClient()

    response = await query_with_retry(
        client,
        f"Analyze this: {text}",
        max_retries=3,
        initial_delay=1.0
    )

    # If expecting JSON response
    data = parse_llm_json(response.content)
    return data
```

### Batch Processing

**Old Pattern**:
```python
from amplifier.ccsdk_toolkit import ClaudeSession

async def process_documents(docs: list[str]):
    async with ClaudeSession() as session:
        results = []
        for doc in docs:
            response = await session.query(f"Summarize: {doc}")
            results.append(response.content)
        return results
```

**New Pattern**:
```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import batch_query

async def process_documents(docs: list[str]):
    client = ClaudeSDKClient()

    prompts = [f"Summarize: {doc}" for doc in docs]
    results = await batch_query(
        client,
        prompts,
        max_concurrent=5,
        progress_callback=lambda i, t: print(f"Processing {i}/{t}")
    )

    return [r.content for r in results]
```

### Conversation Management

**Old Pattern**:
```python
from amplifier.ccsdk_toolkit import ClaudeSession

async def chat_session():
    async with ClaudeSession() as session:
        # Session maintains conversation history
        response1 = await session.query("What is Python?")
        response2 = await session.query("Can you give an example?")
        # History is implicit in session
```

**New Pattern**:
```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.helpers import ConversationManager

async def chat_session():
    client = ClaudeSDKClient()
    conversation = ConversationManager(client)

    # Explicit conversation management
    response1 = await conversation.send_message("What is Python?")
    response2 = await conversation.send_message("Can you give an example?")

    # Access history explicitly
    history = conversation.get_history()
```

### File Processing

**Old Pattern**:
```python
from amplifier.ccsdk_toolkit import ClaudeSession
from pathlib import Path

async def analyze_files(directory: str):
    async with ClaudeSession() as session:
        results = {}
        for file in Path(directory).glob("*.md"):
            content = file.read_text()
            response = await session.query(f"Analyze: {content}")
            results[file.name] = response.content
        return results
```

**New Pattern**:
```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.context_managers import FileProcessor
from pathlib import Path

async def analyze_files(directory: str):
    client = ClaudeSDKClient()

    async with FileProcessor(client, directory, "*.md") as processor:
        results = await processor.process_all(
            lambda file, content: f"Analyze: {content}"
        )
        return {r.file.name: r.result for r in results}
```

## Pattern-by-Pattern Migration

### 1. Error Handling and Retries

**Old**: Built into ClaudeSession
```python
options = SessionOptions(retry_attempts=3, retry_delay=1.0)
async with ClaudeSession(options) as session:
    response = await session.query(prompt)  # Retries automatically
```

**New**: Use decorators or utilities
```python
from amplifier.ccsdk_toolkit.decorators import with_retry

@with_retry(max_attempts=3, initial_delay=1.0)
async def query_claude(client, prompt):
    return await client.query(prompt)

# Or use the utility directly
from amplifier.ccsdk_toolkit.utilities import query_with_retry
response = await query_with_retry(client, prompt, max_retries=3)
```

### 2. Progress Tracking

**Old**: Via SessionOptions callback
```python
def progress(text):
    print(f"Progress: {text}")

options = SessionOptions(progress_callback=progress)
```

**New**: Use ProgressTracker utility
```python
from amplifier.ccsdk_toolkit.utilities import ProgressTracker

tracker = ProgressTracker(total=10)
for i in range(10):
    response = await client.query(prompts[i])
    tracker.update(1, f"Processed {i+1}/10")
```

### 3. Response Parsing

**Old**: SessionResponse wrapper
```python
response = await session.query(prompt)
if response.error:
    print(f"Error: {response.error}")
else:
    data = json.loads(response.content)  # Risky!
```

**New**: Defensive utilities
```python
from amplifier.ccsdk_toolkit.defensive import parse_llm_json

response = await query_with_retry(client, prompt)
data = parse_llm_json(response.content)  # Safe parsing
```

### 4. Session Persistence

**Old**: Built into ClaudeSession (limited)
```python
# Session state was partially managed internally
```

**New**: Explicit session management
```python
from amplifier.ccsdk_toolkit.context_managers import SessionContext
from amplifier.ccsdk_toolkit.utilities import save_conversation, load_conversation

# Use context manager for automatic persistence
async with SessionContext(client, session_dir="./sessions") as session:
    await session.query("Question")
    # Auto-saves on exit

# Or manage manually
messages = []
messages.append({"role": "user", "content": prompt})
messages.append({"role": "assistant", "content": response.content})
save_conversation(messages, "session.json")
```

## Complete Migration Example

Here's a complete before-and-after example of a document analysis tool:

### Before (ClaudeSession)

```python
from amplifier.ccsdk_toolkit import ClaudeSession, SessionOptions
from amplifier.ccsdk_toolkit.defensive import write_json_with_retry
from pathlib import Path
import json

async def analyze_project_docs(project_dir: str):
    """Analyze all markdown files in a project."""

    options = SessionOptions(
        retry_attempts=3,
        stream_output=True,
        system_prompt="You are a documentation analyzer."
    )

    async with ClaudeSession(options) as session:
        results = []

        for doc_file in Path(project_dir).glob("**/*.md"):
            print(f"Analyzing {doc_file.name}...")

            content = doc_file.read_text()
            prompt = f"""Analyze this documentation file and return JSON:

            File: {doc_file.name}
            Content: {content}

            Return: {{"quality": 0-10, "issues": [], "suggestions": []}}
            """

            response = await session.query(prompt)

            if response.error:
                print(f"Error analyzing {doc_file.name}: {response.error}")
                continue

            try:
                analysis = json.loads(response.content)
                analysis["file"] = str(doc_file)
                results.append(analysis)
            except json.JSONDecodeError:
                print(f"Failed to parse response for {doc_file.name}")

        # Save results
        write_json_with_retry(results, "analysis_results.json")
        return results
```

### After (Direct SDK with Utilities)

```python
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from amplifier.ccsdk_toolkit.context_managers import FileProcessor
from amplifier.ccsdk_toolkit.utilities import batch_query
from amplifier.ccsdk_toolkit.defensive import parse_llm_json, write_json_with_retry
from amplifier.ccsdk_toolkit.decorators import with_retry
from pathlib import Path
import asyncio

async def analyze_project_docs(project_dir: str):
    """Analyze all markdown files in a project."""

    # Initialize client with options
    client = ClaudeSDKClient(
        options=ClaudeCodeOptions(
            system_prompt="You are a documentation analyzer."
        )
    )

    # Use FileProcessor for automatic file handling
    async with FileProcessor(client, project_dir, "**/*.md") as processor:

        # Define analysis function
        @with_retry(max_attempts=3)
        async def analyze_file(file: Path, content: str):
            prompt = f"""Analyze this documentation file and return JSON:

            File: {file.name}
            Content: {content}

            Return: {{"quality": 0-10, "issues": [], "suggestions": []}}
            """

            response = await client.query(prompt)

            # Safe JSON parsing
            analysis = parse_llm_json(response.content)
            analysis["file"] = str(file)
            return analysis

        # Process all files with progress tracking
        results = await processor.process_all(
            analyze_file,
            max_concurrent=5,  # Process up to 5 files in parallel
            progress=True       # Show progress bar
        )

        # Extract successful results
        successful = [r.result for r in results if r.result and "error" not in r.result]

        # Save results with retry protection
        write_json_with_retry(successful, "analysis_results.json")

        # Report summary
        print(f"\nAnalyzed {len(successful)}/{len(results)} files successfully")
        return successful
```

### Key Improvements in the New Version

1. **Parallel Processing**: Process up to 5 files concurrently
2. **Better Error Handling**: Decorator-based retry logic
3. **Safe JSON Parsing**: Using `parse_llm_json` utility
4. **Progress Tracking**: Built-in progress reporting
5. **Cleaner Separation**: File handling separate from SDK calls
6. **More Testable**: Each component can be tested independently

## Advanced Migration Patterns

### Custom Retry Strategies

```python
from amplifier.ccsdk_toolkit.context_managers import RetryContext, RetryStrategy

# Define custom retry strategy
strategy = RetryStrategy(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=30.0,
    backoff="exponential",
    retryable_errors=(TimeoutError, ConnectionError)
)

async with RetryContext(strategy) as retry:
    result = await retry.execute(client.query, prompt)
```

### Streaming Responses

```python
from amplifier.ccsdk_toolkit.context_managers import StreamingQuery

async with StreamingQuery(client) as stream:
    async for chunk in stream.query(prompt):
        print(chunk, end="", flush=True)
```

### Timed Execution

```python
from amplifier.ccsdk_toolkit.context_managers import TimedExecution

async with TimedExecution(timeout=30.0) as timer:
    result = await client.query(prompt)
    print(f"Query took {timer.elapsed:.2f} seconds")
```

## Testing Your Migration

### 1. Verify Functionality

Run your migrated code with the same inputs to ensure identical results:

```python
# Test both old and new patterns
old_results = await analyze_with_session(data)
new_results = await analyze_with_sdk(data)

assert old_results == new_results, "Results should match"
```

### 2. Check Performance

The new patterns should be faster:

```python
import time

# Benchmark old pattern
start = time.time()
await old_pattern_function()
old_time = time.time() - start

# Benchmark new pattern
start = time.time()
await new_pattern_function()
new_time = time.time() - start

print(f"Old: {old_time:.2f}s, New: {new_time:.2f}s")
print(f"Speedup: {old_time/new_time:.1f}x")
```

### 3. Suppress Deprecation Warnings (Temporary)

During migration, you can suppress warnings:

```bash
# Via environment variable
export CCSDK_SUPPRESS_DEPRECATION=1
python your_script.py

# Or in code
import os
os.environ["CCSDK_SUPPRESS_DEPRECATION"] = "1"
```

## Common Pitfalls and Solutions

### Pitfall 1: Forgetting to Initialize Client

**Problem**: Creating utilities without a client
```python
# This won't work
response = await query_with_retry(prompt)  # Missing client!
```

**Solution**: Always initialize the client first
```python
client = ClaudeSDKClient()
response = await query_with_retry(client, prompt)
```

### Pitfall 2: Not Using Defensive Utilities

**Problem**: Assuming LLM returns clean JSON
```python
# Risky!
data = json.loads(response.content)
```

**Solution**: Use defensive parsing
```python
from amplifier.ccsdk_toolkit.defensive import parse_llm_json
data = parse_llm_json(response.content)
```

### Pitfall 3: Missing Retry Logic

**Problem**: No automatic retries like ClaudeSession
```python
# No retry protection
response = await client.query(prompt)
```

**Solution**: Add retry logic explicitly
```python
# Option 1: Utility
response = await query_with_retry(client, prompt)

# Option 2: Decorator
@with_retry()
async def safe_query(client, prompt):
    return await client.query(prompt)
```

## Need Help?

- **Documentation**: See the full toolkit documentation in `README.md`
- **Examples**: Check `amplifier/ccsdk_toolkit/examples/` for working examples
- **Issues**: Report migration issues on GitHub
- **Support**: Deprecation timeline allows plenty of time to migrate

## Summary

The migration from `ClaudeSession` to direct SDK patterns with utilities offers:

1. **More Control**: Explicit over implicit
2. **Better Performance**: Less overhead, parallel processing
3. **Greater Flexibility**: Mix and match utilities
4. **Improved Testing**: Test components in isolation
5. **Future-Proof**: Aligned with SDK evolution

Take your time to migrate - the old patterns will continue working through v2.x releases. Use this guide to migrate incrementally, testing as you go.