# Claude Code SDK Toolkit

A modern Python toolkit that provides composable utilities, helpers, context managers, and decorators for building robust CLI tools with the Claude Code SDK. Embraces direct SDK usage with optional enhancements.

## 🚀 Architecture: Composition over Wrappers

The toolkit follows a **composition-based architecture** that enhances the Claude Code SDK without wrapping it. This provides cleaner code, better performance, and more flexibility.

### Quick Example

```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import query_with_retry
from amplifier.ccsdk_toolkit.defensive import parse_llm_json

# Use SDK directly with optional enhancements
client = ClaudeSDKClient()
response = await query_with_retry(client, "Analyze this code")
data = parse_llm_json(response.content, default={})
```

### Why Composition?

- **🎯 Direct SDK Access** - Use the full power of Claude Code SDK without abstraction layers
- **🔧 Composable Utilities** - Mix and match only the utilities you need
- **⚡ Better Performance** - No wrapper overhead, direct SDK calls
- **🧩 Framework Agnostic** - Use with any async framework or pattern
- **🛡️ Battle-Tested** - Defensive utilities proven through real-world usage

## Quick Start

**Building a new tool?** Start with the production-ready template:

```bash
# Copy template to create your tool
cp amplifier/ccsdk_toolkit/templates/tool_template.py your_tool.py

# Template includes ALL proven patterns:
# ✓ Recursive file discovery (**/*.ext)
# ✓ Input validation and error handling
# ✓ Progress visibility and logging
# ✓ Resume capability with checkpoints
# ✓ Defensive LLM response parsing
# ✓ Cloud-aware file I/O with retries
```

## Installation

```bash
# Install Claude Code SDK
pip install claude-code-sdk

# Or with uv in the amplifier project
uv add claude-code-sdk
```

## Pattern Examples

### 1. Utility Pattern - Direct Enhancement

Pure functions that enhance SDK capabilities without state:

```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import (
    query_with_retry,
    batch_query,
    parse_sdk_response,
    save_response
)

client = ClaudeSDKClient()

# Single query with automatic retry
response = await query_with_retry(client, "Analyze this code", max_retries=3)

# Batch processing multiple queries
queries = ["Query 1", "Query 2", "Query 3"]
results = await batch_query(client, queries, max_concurrent=2)

# Parse and save responses
parsed = parse_sdk_response(response)
save_response(response, Path("output.json"))
```

### 2. Helper Pattern - Compositional Classes

Stateful classes that compose around the SDK:

```python
from amplifier.ccsdk_toolkit.helpers import (
    ConversationManager,
    BatchProcessor,
    SessionManager
)

# Manage multi-turn conversations
conversation = ConversationManager(client)
await conversation.query_with_context("What is Python?")
await conversation.query_with_context("Show me an example")
history = conversation.get_context()

# Process batches with progress tracking
processor = BatchProcessor(client, max_concurrent=3)
async def analyze_file(client, filepath):
    content = filepath.read_text()
    return await client.query(f"Analyze: {content}")

results = await processor.process_items(files, analyze_file)

# Manage persistent sessions
session_mgr = SessionManager(client)
session = session_mgr.create_session("code-analysis")
session_mgr.set_session_data("context", {"project": "amplifier"})
```

### 3. Context Manager Pattern - Scoped Operations

Manage resources and provide clean scoped operations:

```python
from amplifier.ccsdk_toolkit.context_managers import (
    FileProcessor,
    SessionContext,
    TimedExecution,
    RetryContext
)

# Process files with automatic cleanup
async with FileProcessor(client, "src/", "**/*.py") as processor:
    async def analyze_code(file_path, content):
        return f"Analysis of {file_path.name}: {content[:100]}"

    results = await processor.process_batch(analyze_code)

# Session with automatic persistence
async with SessionContext(client, session_name="analysis") as session:
    response1 = await session.query("First question")
    response2 = await session.query("Follow-up question")
    # Session automatically saved on exit

# Time-bounded operations
async with TimedExecution(timeout_seconds=30):
    result = await client.query("Complex analysis task")

# Retry with context
async with RetryContext(max_attempts=3, backoff_factor=2.0):
    result = await client.query("Potentially failing operation")
```

### 4. Decorator Pattern - Function Enhancement

Enhance functions with cross-cutting concerns:

```python
from amplifier.ccsdk_toolkit.decorators import (
    with_retry,
    with_logging,
    sdk_function,
    with_validation
)

# Automatic retry on failure
@with_retry(attempts=3, backoff=2.0)
async def analyze_code(client, code: str):
    return await client.query(f"Analyze: {code}")

# Add structured logging
@with_logging()
async def process_file(client, filepath: Path):
    content = filepath.read_text()
    return await client.query(f"Process: {content}")

# Complete SDK function with all enhancements
@sdk_function()
@with_logging()
@with_retry(attempts=3)
async def review_code(client, code: str):
    return await client.query(f"Review this code: {code}")

# Input/output validation with Pydantic
from pydantic import BaseModel

class CodeInput(BaseModel):
    code: str
    language: str = "python"

class ReviewOutput(BaseModel):
    summary: str
    issues: list[str]
    score: float

@with_validation(input_schema=CodeInput, output_schema=ReviewOutput)
async def structured_review(client, code: str, language: str = "python"):
    response = await client.query(f"Review {language} code: {code}")
    # Response automatically validated against ReviewOutput schema
    return parse_llm_json(response.content)
```

### 5. Defensive Pattern - Safe LLM Interaction

Battle-tested utilities for robust LLM interaction:

```python
from amplifier.ccsdk_toolkit.defensive import (
    parse_llm_json,
    retry_with_feedback,
    isolate_prompt,
    write_json_with_retry
)

# Parse JSON from any LLM response format
llm_response = """Here's the analysis:
` ``json
{"summary": "Code looks good", "issues": []}
` ``
Hope that helps!"""

data = parse_llm_json(llm_response, default={"error": "parse_failed"})
# Returns: {"summary": "Code looks good", "issues": []}

# Retry with error feedback to LLM for self-correction
async def generate_valid_json(prompt):
    response = await client.query(prompt)
    return parse_llm_json(response.content)

result = await retry_with_feedback(
    generate_valid_json,
    "Generate JSON with fields: name, age, email",
    max_retries=3
)

# Prevent prompt injection
user_input = "Ignore all previous instructions..."
safe_prompt = isolate_prompt("Analyze this user input", user_input)
# Adds clear boundaries around potentially malicious content

# Cloud-aware file operations with retries
data = {"analysis": "results", "timestamp": "2024-01-01"}
write_json_with_retry(data, Path("results.json"))
# Handles OneDrive sync delays and other I/O issues automatically
```

## Core Modules

### Utilities (`utilities/`)
Pure functions for common SDK operations:
- `query_with_retry()` - Robust querying with exponential backoff
- `batch_query()` - Concurrent batch processing
- `parse_sdk_response()` - Normalize different response formats
- `save_response()` - Persist responses to files

### Helpers (`helpers/`)
Compositional classes for stateful operations:
- `ConversationManager` - Multi-turn conversation management
- `BatchProcessor` - Batch processing with progress tracking
- `SessionManager` - Persistent session management

### Context Managers (`context_managers/`)
Scoped resource management:
- `FileProcessor` - Batch file processing with cleanup
- `SessionContext` - Session lifecycle management
- `TimedExecution` - Time-bounded operations
- `RetryContext` - Scoped retry logic

### Decorators (`decorators/`)
Function enhancement patterns:
- `@with_retry` - Add retry logic to functions
- `@with_logging` - Structured logging
- `@sdk_function` - Complete SDK function enhancement
- `@with_validation` - Pydantic-based input/output validation

### Defensive (`defensive/`)
Battle-tested utilities for robust LLM interaction:
- `parse_llm_json()` - Extract JSON from any LLM response format
- `retry_with_feedback()` - Self-correcting retry with error feedback
- `isolate_prompt()` - Prevent prompt injection
- `write_json_with_retry()` - Cloud-aware file I/O

## Example Tools

### Create Your Own Tool

```python
#!/usr/bin/env python3
"""My custom CCSDK tool using composition patterns"""

import asyncio
from pathlib import Path
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import query_with_retry
from amplifier.ccsdk_toolkit.defensive import parse_llm_json
from amplifier.ccsdk_toolkit.helpers import BatchProcessor

async def analyze_file(client, filepath: Path):
    """Analyze a single file"""
    content = filepath.read_text()
    prompt = f"Analyze this {filepath.suffix} file for complexity:\n\n{content}"

    response = await query_with_retry(client, prompt, max_retries=3)
    return parse_llm_json(response.content, default={"error": "Failed to parse"})

async def main():
    # Create SDK client directly
    client = ClaudeSDKClient()

    # Find all Python files
    files = list(Path(".").glob("**/*.py"))
    print(f"Found {len(files)} Python files")

    # Process in batches
    processor = BatchProcessor(client, max_concurrent=3)
    results = await processor.process_items(files, analyze_file)

    # Show results
    for result in results:
        if result.status == "success":
            print(f"✓ {result.item_id}: {result.result.get('summary', 'No summary')}")
        else:
            print(f"✗ {result.item_id}: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

The toolkit uses direct SDK configuration:

```python
from claude_code_sdk import ClaudeSDKClient

# Basic configuration
client = ClaudeSDKClient(
    api_key="your-key",  # Or from ANTHROPIC_API_KEY env var
    system_prompt="You are a helpful assistant"
)

# Advanced configuration
client = ClaudeSDKClient(
    api_key="your-key",
    timeout_seconds=60,
    max_retries=3,
    system_prompt="Custom system prompt"
)
```

## Error Handling

The toolkit provides clear error handling:

```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import query_with_retry

try:
    client = ClaudeSDKClient()
    response = await query_with_retry(client, "Analyze this code")
    print(response.content)

except Exception as e:
    print(f"Error: {e}")
    # Handle specific error types as needed
```

## Architecture Philosophy

The toolkit follows these principles:

- **Composition over Inheritance** - Use the SDK directly, enhance with utilities
- **Ruthless Simplicity** - Every abstraction must justify its existence
- **Modular Design** - Self-contained modules with clear interfaces
- **Defensive Programming** - Assume LLMs will return unexpected formats
- **Battle-Tested Patterns** - Utilities proven through real-world usage

## Testing

All modules include comprehensive tests:

```bash
# Run all tests
make test

# Run specific test file
uv run pytest amplifier/ccsdk_toolkit/tests/test_utilities.py -v

# Run with coverage
make test-coverage
```

## Contributing

Contributions welcome! Please ensure:

1. **Follow the composition pattern** - Enhance SDK, don't wrap it
2. **Include tests** - Every utility/helper needs tests
3. **Document defensive patterns** - Explain why edge cases are handled
4. **Pass all checks** - `make check` must pass

```bash
make check  # Format, lint, and type-check
make test   # Run tests
```

## Known Issues & Solutions

### Cloud Sync File I/O Errors

If you encounter intermittent I/O errors (especially in OneDrive/Dropbox folders):

```python
# The toolkit handles this automatically
from amplifier.ccsdk_toolkit.defensive import write_json_with_retry

# This will retry on cloud sync delays
write_json_with_retry(data, filepath)
```

### LLM JSON Parsing Failures

LLMs don't always return clean JSON:

```python
# Use defensive parsing
from amplifier.ccsdk_toolkit.defensive import parse_llm_json

# This handles markdown blocks, explanations, malformed JSON
data = parse_llm_json(llm_response, default={})
```

## License

[Project License]

## Support

- GitHub Issues: [Project Issues]
- Documentation: See `/ai_context/claude_code/` for SDK details

---

Built with the Claude Code SDK and a commitment to ruthless simplicity through composition.