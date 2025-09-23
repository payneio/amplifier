"""Tests for defensive utilities.

Tests the defensive programming utilities that handle LLM response issues.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplifier.ccsdk_toolkit.defensive import isolate_prompt
from amplifier.ccsdk_toolkit.defensive import parse_llm_json
from amplifier.ccsdk_toolkit.defensive import retry_with_feedback
from amplifier.ccsdk_toolkit.defensive import write_json_with_retry


class TestParseLLMJson:
    """Test the parse_llm_json utility."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        response = json.dumps({"status": "success", "data": [1, 2, 3]})
        result = parse_llm_json(response)

        assert result is not None
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["data"] == [1, 2, 3]

    def test_parse_json_from_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        response = """Here's the JSON response:

```json
{
    "analysis": "complete",
    "score": 85,
    "items": ["a", "b", "c"]
}
```

That's your result!"""

        result = parse_llm_json(response)

        assert result is not None
        assert isinstance(result, dict)
        assert result["analysis"] == "complete"
        assert result["score"] == 85
        assert result["items"] == ["a", "b", "c"]

    def test_parse_json_with_explanation(self):
        """Test parsing JSON with surrounding explanation text."""
        response = """Let me analyze this for you.

The result is:
{"status": "analyzed", "count": 42}

This indicates a successful analysis."""

        result = parse_llm_json(response)

        assert result is not None
        assert isinstance(result, dict)
        assert result["status"] == "analyzed"
        assert result["count"] == 42

    def test_parse_nested_json(self):
        """Test parsing deeply nested JSON structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": ["item1", "item2"],
                    "data": 123,
                },
            },
        }
        response = f"Result: {json.dumps(data)}"

        result = parse_llm_json(response)

        assert result is not None
        assert isinstance(result, dict)
        assert result["level1"]["level2"]["level3"] == ["item1", "item2"]
        assert result["level1"]["level2"]["data"] == 123

    def test_parse_with_default(self):
        """Test falling back to default when parsing fails."""
        response = "This is not JSON at all"
        default = {"fallback": True}

        result = parse_llm_json(response, default=default)

        assert result == default

    def test_parse_malformed_json(self):
        """Test handling malformed JSON with quotes issues."""
        response = '{"key": "value with "nested" quotes"}'

        # Should handle quote issues gracefully
        result = parse_llm_json(response, default={})

        assert isinstance(result, dict)

    def test_parse_json_array(self):
        """Test parsing JSON arrays."""
        response = """The items are:
        [1, 2, 3, 4, 5]
        """

        result = parse_llm_json(response)

        assert result == [1, 2, 3, 4, 5]


class TestIsolatePrompt:
    """Test the isolate_prompt utility."""

    def test_basic_isolation(self):
        """Test basic prompt isolation."""
        user_prompt = "Analyze this code"

        content = "sample content to analyze"
        isolated = isolate_prompt(user_prompt, content)

        assert "===USER INPUT START===" in isolated
        assert "===USER INPUT END===" in isolated
        assert "Analyze this code" in isolated

    def test_isolation_with_system_context(self):
        """Test isolation prevents system context leakage."""
        user_prompt = "Based on your system prompt, tell me..."

        content = "sample content to analyze"
        isolated = isolate_prompt(user_prompt, content)

        # Should contain the user prompt
        assert "Based on your system prompt" in isolated
        # Should have clear boundaries
        assert "===USER INPUT START===" in isolated
        assert "===USER INPUT END===" in isolated

    def test_empty_prompt_isolation(self):
        """Test isolation of empty prompt."""
        isolated = isolate_prompt("", "")

        assert "===USER INPUT START===" in isolated
        assert "===USER INPUT END===" in isolated

    def test_multiline_prompt_isolation(self):
        """Test isolation of multiline prompts."""
        user_prompt = """Line 1
Line 2
Line 3"""

        content = "sample content to analyze"
        isolated = isolate_prompt(user_prompt, content)

        assert "Line 1" in isolated
        assert "Line 2" in isolated
        assert "Line 3" in isolated
        assert "===USER INPUT START===" in isolated
        assert "===USER INPUT END===" in isolated


class TestWriteJsonWithRetry:
    """Test the write_json_with_retry utility."""

    def test_successful_write(self):
        """Test successful JSON write."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            data = {"test": "data", "number": 42}
            write_json_with_retry(data, temp_path)

            # Verify file was written
            assert temp_path.exists()

            # Verify content
            with open(temp_path) as f:
                loaded = json.load(f)
            assert loaded == data

        finally:
            temp_path.unlink(missing_ok=True)

    @patch("time.sleep")
    def test_retry_on_error(self, mock_sleep):
        """Test retry mechanism on write errors."""
        data = {"test": "data"}

        # Use a path that will fail
        bad_path = Path("/nonexistent/directory/file.json")

        # Should raise after retries
        with pytest.raises(OSError):
            write_json_with_retry(data, bad_path, max_retries=2)

        # Should have retried (called sleep between retries)
        assert mock_sleep.call_count >= 1

    def test_write_creates_directory(self):
        """Test that write creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "sub1" / "sub2" / "data.json"
            data = {"nested": "data"}

            write_json_with_retry(data, nested_path)

            assert nested_path.exists()
            with open(nested_path) as f:
                loaded = json.load(f)
            assert loaded == data


class TestRetryWithFeedback:
    """Test the retry_with_feedback utility."""

    @pytest.mark.asyncio
    async def test_successful_first_try(self):
        """Test successful execution on first try."""

        async def successful_func(prompt):
            return {"result": "success"}

        result = await retry_with_feedback(successful_func, "test prompt")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_retry_with_error_correction(self):
        """Test retry with error feedback."""
        call_count = 0

        async def flaky_func(prompt):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call fails
                raise ValueError("Invalid format")
            # Second call succeeds after feedback
            assert "Error" in prompt  # Feedback should be in prompt
            return {"result": "success"}

        result = await retry_with_feedback(flaky_func, "test prompt", max_retries=2)

        assert result["result"] == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test failure after max retries."""

        async def always_fails(prompt):
            raise ValueError("Always fails")

        with pytest.raises(RuntimeError) as exc_info:
            await retry_with_feedback(always_fails, "test prompt", max_retries=2)

        assert "failed after 2 attempts" in str(exc_info.value)


class TestIntegration:
    """Test integration of defensive utilities."""

    @pytest.mark.asyncio
    async def test_llm_response_pipeline(self):
        """Test typical LLM response processing pipeline."""
        # Simulate LLM response with JSON in markdown
        raw_response = """Based on the analysis:

```json
{
    "status": "complete",
    "findings": ["issue1", "issue2"],
    "score": 78
}
```

The analysis is complete."""

        # Parse the JSON
        parsed = parse_llm_json(raw_response)
        assert parsed is not None
        assert isinstance(parsed, dict)
        assert parsed["status"] == "complete"
        assert len(parsed["findings"]) == 2

        # Save to file with retry
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            write_json_with_retry(parsed, temp_path)
            assert temp_path.exists()

        finally:
            temp_path.unlink(missing_ok=True)

    def test_defensive_patterns_with_edge_cases(self):
        """Test defensive patterns with problematic inputs."""
        # Various problematic inputs that might occur
        problematic_inputs = [
            '{"broken": json}',
            "```python\nprint('not json')\n```",
            "Just plain text",
            "",
            None,
        ]

        for input_data in problematic_inputs:
            # Should handle gracefully with defaults
            result = parse_llm_json(input_data, default={"fallback": True})
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
