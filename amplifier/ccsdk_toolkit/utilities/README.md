# Module: CCSDK Toolkit Utilities

## Purpose

Provide utility functions that enhance claude-code-sdk usage without wrapping. These utilities work WITH the SDK, not around it, following the principle of composable, single-responsibility functions.

## Contract

### Inputs
- SDK client instances (ClaudeSDKClient)
- Prompts (strings)
- SDK responses (various formats)
- File paths for I/O operations

### Outputs
- Enhanced results with retry logic
- Parsed data from SDK responses
- Saved/loaded conversation data
- Progress tracking information

### Side Effects
- Logging of operations and errors
- File I/O with retry logic for cloud sync
- Progress callbacks during batch operations

### Dependencies
- claude-code-sdk (external)
- amplifier.ccsdk_toolkit.defensive (internal)
- amplifier.utils.file_io (internal)

## Public Interface

### Query Utilities (query_utils.py)

```python
async def query_with_retry(client: Any, prompt: str, max_retries: int = 3) -> Any:
    """Query SDK with automatic retry on failure.

    Example:
        >>> client = ClaudeSDKClient()
        >>> response = await query_with_retry(client, "Hello")
    """

def parse_sdk_response(response: Any) -> dict:
    """Parse SDK response object into clean dictionary.

    Example:
        >>> data = parse_sdk_response(response)
        >>> print(data['content'])
    """

def extract_text_content(response: Any) -> str:
    """Extract plain text content from SDK response."""

async def batch_query(client: Any, prompts: list[str], max_concurrent: int = 5) -> list[Any]:
    """Process multiple prompts in parallel with concurrency control."""
```

### File Utilities (file_utils.py)

```python
def ensure_data_dir(base_path: Path | None = None) -> Path:
    """Ensure data directory exists and return path."""

def save_response(response: Any, filepath: str | Path, format: str = 'json') -> Path:
    """Save SDK response with cloud-sync retry logic.

    Formats: 'json', 'txt', 'md'
    """

def load_conversation(filepath: str | Path) -> list[dict]:
    """Load saved conversation from file."""

def save_conversation(entries: list[dict], filepath: str | Path) -> Path:
    """Save conversation history to file."""
```

### Progress Utilities (progress_utils.py)

```python
class SimpleProgressCallback:
    """Simple progress callback for batch operations.

    Example:
        >>> callback = SimpleProgressCallback()
        >>> await batch_query(client, prompts, on_progress=callback)
    """

class ProgressTracker:
    """Wrap SDK client to add progress tracking.

    Example:
        >>> tracker = ProgressTracker()
        >>> tracked_client = tracker.wrap_client(client)
        >>> response = await tracked_client.query("Hello")
    """
```

## Error Handling

| Error Type | Condition | Recovery Strategy |
|------------|-----------|-------------------|
| RuntimeError | Query fails after retries | Log error, re-raise |
| OSError | File I/O fails (cloud sync) | Retry with exponential backoff |
| ValueError | Unsupported format | Raise with clear message |

## Performance Characteristics

- Query retry: Exponential backoff (1s, 2s, 4s)
- Batch queries: Default 5 concurrent operations
- File I/O retry: 3 attempts with exponential backoff
- Progress reporting: Max once per second

## Configuration

```python
# Default configurations (can be overridden)
MAX_RETRIES = 3
RETRY_DELAY = 1.0
MAX_CONCURRENT = 5
DATA_DIR = Path("data/ccsdk")
```

## Migration from ClaudeSession

### Old Pattern (Wrapped)
```python
async with ClaudeSession() as session:
    response = await session.query("Hello")
    session.save_response(response, "output.json")
```

### New Pattern (Direct + Utilities)
```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import (
    query_with_retry,
    save_response
)

client = ClaudeSDKClient()
response = await query_with_retry(client, "Hello")
save_response(response, "output.json")
```

## Usage Examples

### Basic Query with Retry
```python
from claude_code_sdk import ClaudeSDKClient
from amplifier.ccsdk_toolkit.utilities import query_with_retry

client = ClaudeSDKClient()
response = await query_with_retry(client, "Explain quantum computing", max_retries=3)
```

### Batch Processing with Progress
```python
from amplifier.ccsdk_toolkit.utilities import batch_query, SimpleProgressCallback

prompts = ["Question 1", "Question 2", "Question 3"]
callback = SimpleProgressCallback(prefix="Processing")
responses = await batch_query(client, prompts, on_progress=callback)
```

### Save and Load Conversations
```python
from amplifier.ccsdk_toolkit.utilities import save_conversation, load_conversation

# Save conversation
conversation = [
    {'role': 'user', 'content': 'Hello'},
    {'role': 'assistant', 'content': 'Hi there!'}
]
save_conversation(conversation, "chat.json")

# Load conversation
history = load_conversation("chat.json")
```

### Progress Tracking
```python
from amplifier.ccsdk_toolkit.utilities import ProgressTracker

tracker = ProgressTracker()
tracked_client = tracker.wrap_client(client)

# All operations are now tracked
response = await tracked_client.query("Hello")
# Logs: [Operation 1] Starting: query
# Logs: [Operation 1] Completed: query (1.23s)
```

## Testing

```bash
# Run module tests
pytest amplifier/ccsdk_toolkit/utilities/tests/

# Run integration tests
pytest tests/test_ccsdk_utilities.py
```

## Regeneration Specification

This module can be regenerated from this specification alone. Key invariants:

1. All functions work WITH SDK instances, not wrap them
2. Defensive I/O for cloud sync issues
3. Progress tracking without interface modification
4. Clean error handling with retries
5. Simple, composable functions

The module provides utility functions that enhance SDK usage while maintaining the direct SDK interface pattern.