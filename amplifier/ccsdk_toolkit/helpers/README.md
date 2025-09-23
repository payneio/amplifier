# CCSDK Toolkit Helpers Module

Optional helper classes for complex workflows that USE the Claude Code SDK client through composition rather than wrapping it.

## Module Contract

**Purpose:** Provide convenience helpers for common workflow patterns

**Inputs:** Initialized SDK client passed to helper constructors

**Outputs:** Workflow results specific to each helper

**Side Effects:** None beyond what the SDK client performs

**Dependencies:**
- `amplifier.ccsdk_toolkit.CCSDKSession`
- `amplifier.ccsdk_toolkit.utilities`

## Design Philosophy

These helpers follow a strict composition pattern:
- Accept an initialized SDK client, never create one
- Use the client directly, don't wrap its methods
- Each helper has a single, focused purpose
- Leverage utilities module for common operations
- Keep implementations simple and maintainable

## Available Helpers

### ConversationManager

Manages multi-turn conversations with context tracking.

```python
from amplifier.ccsdk_toolkit import CCSDKSession
from amplifier.ccsdk_toolkit.helpers import ConversationManager

# Initialize with client
client = CCSDKSession(api_key="your-key")
manager = ConversationManager(client)

# Add conversation turns
manager.add_turn("What is Python?", "Python is a programming language...")

# Query with context
response = await manager.query_with_context("Tell me more about its uses")

# Save/load conversations
manager.save_to_file("conversation.json")
manager.load_from_file("conversation.json")

# Get formatted context
context = manager.get_context(max_turns=5)
```

**Key Methods:**
- `add_turn(user_message, assistant_response)` - Add conversation turn
- `query_with_context(prompt)` - Query with conversation history
- `get_context(max_turns)` - Get formatted conversation context
- `save_to_file(filepath)` - Save conversation to JSON
- `load_from_file(filepath)` - Load conversation from JSON
- `clear()` - Clear conversation history
- `get_summary()` - Get conversation statistics

### BatchProcessor

Process multiple items with concurrency control and progress tracking.

```python
from amplifier.ccsdk_toolkit import CCSDKSession
from amplifier.ccsdk_toolkit.helpers import BatchProcessor

# Initialize with client
client = CCSDKSession(api_key="your-key")
processor = BatchProcessor(client, max_concurrent=5)

# Define processing function
async def process_item(client, item):
    response = await client.query(f"Analyze: {item}")
    return response

# Process items
items = ["item1", "item2", "item3"]
results = await processor.process_items(
    items,
    processor_func=process_item,
    progress_callback=lambda done, total: print(f"{done}/{total}")
)

# Get results
successful = processor.get_successful_results()
failed = processor.get_failed_results()

# Save results
processor.save_results("results.json")
```

**Key Methods:**
- `process_items(items, processor_func)` - Process list of items
- `process_files(pattern, processor_func)` - Process files by pattern
- `get_results()` - Get all processing results
- `get_successful_results()` - Get only successful results
- `get_failed_results()` - Get only failed results
- `save_results(filepath)` - Save results to JSON
- `get_summary()` - Get processing statistics

### SessionManager

Manage persistent sessions that can be saved and resumed.

```python
from amplifier.ccsdk_toolkit import CCSDKSession
from amplifier.ccsdk_toolkit.helpers import SessionManager

# Initialize with client
client = CCSDKSession(api_key="your-key")
manager = SessionManager(client, session_dir="./sessions")

# Create new session
session = manager.create_session("analysis_session")

# Store data in session
manager.set_session_data("results", analysis_results)
manager.set_session_data("config", {"threshold": 0.8})

# Update metadata
manager.update_session_metadata({"status": "in_progress"})

# Save session
manager.save_session()

# List available sessions
sessions = manager.list_sessions()

# Load existing session
manager.load_session(session_id)

# Get session data
results = manager.get_session_data("results")

# Export/import sessions
manager.export_session("backup.json")
manager.import_session("backup.json")
```

**Key Methods:**
- `create_session(name)` - Create new named session
- `load_session(session_id)` - Load existing session
- `save_session()` - Save current session
- `list_sessions()` - List all available sessions
- `get_session_data(key)` - Get data from session
- `set_session_data(key, value)` - Set data in session
- `update_session_metadata(metadata)` - Update session metadata
- `delete_session(session_id)` - Delete a session
- `export_session(filepath)` - Export session to file
- `import_session(filepath)` - Import session from file

## Usage Examples

### Complete Conversation Workflow

```python
import asyncio
from amplifier.ccsdk_toolkit import CCSDKSession
from amplifier.ccsdk_toolkit.helpers import ConversationManager

async def main():
    # Initialize client and manager
    client = ClaudeCodeClient(api_key="your-key")
    manager = ConversationManager(client)

    # Have a conversation
    response1 = await manager.query_with_context("What is machine learning?")
    response2 = await manager.query_with_context("How does it differ from AI?")
    response3 = await manager.query_with_context("What are some applications?")

    # Save conversation
    manager.save_to_file("ml_conversation.json")

    # Get summary
    summary = manager.get_summary()
    print(f"Conversation had {summary['turn_count']} turns")

asyncio.run(main())
```

### Batch File Processing

```python
import asyncio
from pathlib import Path
from amplifier.ccsdk_toolkit import CCSDKSession
from amplifier.ccsdk_toolkit.helpers import BatchProcessor

async def analyze_file(client: CCSDKSession, file_path: Path):
    """Analyze a single file"""
    content = file_path.read_text()
    prompt = f"Summarize this file:\n{content[:1000]}"
    return await client.query(prompt)

async def main():
    # Initialize client and processor
    client = ClaudeCodeClient(api_key="your-key")
    processor = BatchProcessor(client, max_concurrent=3)

    # Process all markdown files
    results = await processor.process_files(
        "**/*.md",
        processor_func=analyze_file,
        base_dir="./docs"
    )

    # Save results
    processor.save_results("analysis_results.json")

    # Print summary
    summary = processor.get_summary()
    print(f"Processed {summary['total_items']} files")
    print(f"Success rate: {summary['success_rate']:.1f}%")

asyncio.run(main())
```

### Session-Based Workflow

```python
import asyncio
from amplifier.ccsdk_toolkit import CCSDKSession
from amplifier.ccsdk_toolkit.helpers import SessionManager, BatchProcessor

async def resumable_analysis():
    # Initialize client and managers
    client = ClaudeCodeClient(api_key="your-key")
    session_mgr = SessionManager(client)
    batch_proc = BatchProcessor(client)

    # Check for existing session
    sessions = session_mgr.list_sessions()
    if sessions:
        # Resume most recent session
        session_mgr.load_session(sessions[0]["session_id"])
        processed_items = session_mgr.get_session_data("processed", [])
        print(f"Resuming with {len(processed_items)} already processed")
    else:
        # Create new session
        session_mgr.create_session("batch_analysis")
        processed_items = []

    # Get items to process
    all_items = ["item1", "item2", "item3", "item4"]
    remaining = [i for i in all_items if i not in processed_items]

    if remaining:
        # Process remaining items
        async def process_and_track(client, item):
            result = await client.query(f"Analyze: {item}")
            processed_items.append(item)
            session_mgr.set_session_data("processed", processed_items)
            return result

        results = await batch_proc.process_items(
            remaining,
            processor_func=process_and_track
        )

        # Save final results
        session_mgr.set_session_data("results", batch_proc.get_results())
        session_mgr.save_session()

    print("Analysis complete!")

asyncio.run(resumable_analysis())
```

## Integration with Utilities

The helpers module leverages the utilities module for:

- **Retry logic** - Using `query_with_retry()` for robust queries
- **Defensive parsing** - Could use defensive utilities if needed
- **File operations** - Standard file I/O with proper encoding

## Best Practices

1. **Always pass initialized client** - Never create clients inside helpers
2. **Use composition, not inheritance** - Helpers use the client, don't extend it
3. **Handle errors gracefully** - Catch and log errors, don't crash
4. **Provide progress feedback** - Use callbacks for long operations
5. **Save state frequently** - Enable interruption and resume
6. **Keep helpers focused** - Each helper does one thing well

## Testing

The helpers can be tested independently by passing mock clients:

```python
import pytest
from unittest.mock import AsyncMock
from amplifier.ccsdk_toolkit.helpers import ConversationManager

@pytest.mark.asyncio
async def test_conversation_manager():
    # Create mock client
    mock_client = AsyncMock()
    mock_client.query.return_value = "Test response"

    # Test manager
    manager = ConversationManager(mock_client)
    response = await manager.query_with_context("Test prompt")

    assert response == "Test response"
    assert manager.metadata["turn_count"] == 1
```

## Extending the Helpers

To add new helpers:

1. Create a new file in `helpers/` directory
2. Follow the composition pattern - accept client in `__init__`
3. Use the client directly, don't wrap it
4. Add to `__all__` in `__init__.py`
5. Document in this README

Example structure for new helper:

```python
class WorkflowHelper:
    """Helper for complex workflows"""

    def __init__(self, client: CCSDKSession):
        """Accept initialized client"""
        self.client = client  # Store, don't wrap

    async def execute_workflow(self, params):
        """Use client directly"""
        result = await self.client.query(params["prompt"])
        return self.process_result(result)
```

## Module Regeneration

This module can be regenerated from this specification. Key invariants:

- Helpers accept initialized clients through composition
- Each helper has single, focused responsibility
- Public method signatures remain stable
- File formats (JSON) remain compatible
- Error handling patterns are preserved