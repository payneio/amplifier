#!/usr/bin/env python3
"""
Defensive Utilities Integration Example

This example demonstrates how to use the battle-tested defensive utilities
with the claude-code-sdk directly (without the wrapper).

The defensive utilities handle common LLM integration failures:
- JSON parsing from various response formats
- Cloud sync file I/O issues (OneDrive, Dropbox)
- Context contamination prevention
- Intelligent retry with feedback
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path when running as script
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# Direct SDK imports
from claude_code_sdk import ClaudeSDKClient
from claude_code_sdk.exceptions import SDKException

# Defensive utilities - the most valuable part of the toolkit
from amplifier.ccsdk_toolkit.defensive import isolate_prompt
from amplifier.ccsdk_toolkit.defensive import parse_llm_json
from amplifier.ccsdk_toolkit.defensive import read_json_with_retry
from amplifier.ccsdk_toolkit.defensive import retry_with_feedback
from amplifier.ccsdk_toolkit.defensive import write_json_with_retry

# Helper utilities for SDK usage
from amplifier.ccsdk_toolkit.utilities import extract_text_content
from amplifier.ccsdk_toolkit.utilities import query_with_retry
from amplifier.ccsdk_toolkit.utilities import save_conversation


async def example_json_parsing():
    """Demonstrate robust JSON parsing from LLM responses."""
    print("\n=== JSON Parsing Example ===")

    # Simulate various LLM response formats
    test_responses = [
        # Clean JSON
        '{"status": "success", "data": [1, 2, 3]}',
        # JSON in markdown block
        '```json\n{"status": "success", "data": [1, 2, 3]}\n```',
        # JSON with explanation
        'Here is the result:\n\n```json\n{"status": "success"}\n```\n\nThis shows success.',
        # Nested JSON with preamble
        'I analyzed the data:\n{"outer": {"inner": "value"}}',
        # Malformed but fixable
        "{'status': 'success', 'data': [1, 2, 3]}",  # Single quotes
    ]

    for i, response in enumerate(test_responses, 1):
        try:
            result = parse_llm_json(response)
            print(f"Response {i}: ✓ Parsed successfully")
            print(f"  Result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Response {i}: ✗ Failed - {e}")


async def example_file_operations():
    """Demonstrate cloud-sync aware file operations."""
    print("\n=== File I/O Example (Cloud-Sync Aware) ===")

    # Test data
    test_data = {"analysis": {"complexity": "moderate", "score": 7.5}, "files": ["file1.py", "file2.py"]}

    # Write with retry (handles OneDrive, Dropbox sync delays)
    output_file = Path("test_output.json")
    try:
        write_json_with_retry(test_data, output_file)
        print(f"✓ Wrote data to {output_file}")

        # Read with retry
        loaded_data = read_json_with_retry(output_file)
        print("✓ Read data back successfully")
        assert loaded_data == test_data
        print("✓ Data integrity verified")

        # Clean up
        output_file.unlink()
        print(f"✓ Cleaned up {output_file}")
    except Exception as e:
        print(f"✗ File operation failed: {e}")


async def example_llm_integration():
    """Demonstrate defensive LLM integration with direct SDK."""
    print("\n=== LLM Integration Example ===")

    try:
        # Initialize SDK client
        client = ClaudeSDKClient()
        print("✓ Initialized Claude SDK client")

        # Example 1: Query with retry and JSON parsing
        print("\n1. Analyzing code with JSON response:")
        code_sample = """def add(a, b):
    return a + b"""

        prompt = """Analyze this simple function and return JSON:
Return format: {"complexity": "low/medium/high", "issues": [...]}"""

        # Use isolate_prompt to prevent context contamination
        clean_prompt = isolate_prompt(prompt, code_sample)

        # Query with automatic retry
        response = await query_with_retry(client, clean_prompt, max_retries=3)
        print("✓ Got response from Claude")

        # Extract text content and parse JSON
        text_content = extract_text_content(response)
        analysis = parse_llm_json(text_content)
        print(f"✓ Parsed JSON response: {json.dumps(analysis, indent=2)}")

        # Example 2: Using retry_with_feedback for self-correcting queries
        print("\n2. Self-correcting query with feedback:")

        async def generate_structured_output(prompt: str) -> dict | list | None:
            """Generate structured output with retry feedback."""
            response = await client.query(prompt)
            text = extract_text_content(response)
            # This might fail, triggering retry with feedback
            return parse_llm_json(text)

        result = await retry_with_feedback(
            func=generate_structured_output,
            prompt="List 3 Python best practices as JSON array with 'title' and 'description' fields",
            max_retries=2,
        )
        print(f"✓ Got structured result with retry feedback: {len(result)} items")

        # Example 3: Extract structured data with Pydantic
        print("\n3. Extracting structured data:")

        # Define expected structure
        from pydantic import BaseModel

        class CodeAnalysis(BaseModel):
            language: str
            complexity: str
            suggestions: list[str]

        extract_prompt = """Analyze this code:
for i in range(10):
    for j in range(10):
        print(i * j)
"""

        response = await query_with_retry(client, extract_prompt)
        text = extract_text_content(response)

        # Extract with Pydantic model
        analysis_data = parse_llm_json(text)
        analysis_obj = CodeAnalysis(**analysis_data) if isinstance(analysis_data, dict) else None

        if not analysis_obj:
            print("✗ Failed to extract structured data")
            return
        print("✓ Extracted structured data:")
        print(f"  Language: {analysis_obj.language}")
        print(f"  Complexity: {analysis_obj.complexity}")
        print(f"  Suggestions: {len(analysis_obj.suggestions)} items")

        # Save conversation
        save_conversation(
            [{"role": "user", "content": extract_prompt}, {"role": "assistant", "content": text}],
            Path("conversation.json"),
        )
        print("\n✓ Saved conversation to conversation.json")

        # Clean up
        Path("conversation.json").unlink()

    except SDKException as e:
        print(f"✗ SDK error: {e}")
        print("\nMake sure claude-code-sdk is available:")
        print("  pip install claude-code-sdk")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


async def example_batch_processing():
    """Demonstrate batch processing with defensive patterns."""
    print("\n=== Batch Processing Example ===")

    # Simulate batch of items to process
    items = ["item1.txt", "item2.txt", "item3.txt"]
    results = []

    print(f"Processing {len(items)} items with defensive patterns...")

    for i, item in enumerate(items, 1):
        try:
            # Simulate processing with potential failures
            if i == 2:
                # Simulate a failure that needs retry
                result = {"item": item, "status": "retry_needed"}
            else:
                result = {"item": item, "status": "success", "data": f"Processed {item}"}

            results.append(result)
            print(f"  [{i}/{len(items)}] {item}: {result['status']}")

            # Save incrementally (cloud-sync aware)
            write_json_with_retry(
                {"results": results, "processed": i, "total": len(items)}, Path("batch_progress.json")
            )

        except Exception as e:
            print(f"  [{i}/{len(items)}] {item}: Failed - {e}")
            results.append({"item": item, "status": "failed", "error": str(e)})

    print(f"\n✓ Batch processing complete: {len([r for r in results if r.get('status') == 'success'])} successful")

    # Clean up
    if Path("batch_progress.json").exists():
        Path("batch_progress.json").unlink()


async def main():
    """Run all examples."""
    print("""
Defensive Utilities Integration Examples
========================================

These examples show how to use the battle-tested defensive utilities
with claude-code-sdk directly, without the wrapper.

Key benefits:
- Handle any LLM response format (JSON parsing)
- Survive cloud sync delays (OneDrive, Dropbox)
- Prevent context contamination
- Automatic retry with feedback
    """)

    # Run examples
    await example_json_parsing()
    await example_file_operations()
    await example_llm_integration()
    await example_batch_processing()

    print("\n" + "=" * 50)
    print("All examples complete!")
    print("\nTo use defensive utilities in your project:")
    print("  from amplifier.ccsdk_toolkit.defensive import parse_llm_json, write_json_with_retry")
    print("  from amplifier.ccsdk_toolkit.utilities import query_with_retry")


if __name__ == "__main__":
    asyncio.run(main())
