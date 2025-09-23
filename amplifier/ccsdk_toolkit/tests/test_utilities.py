"""Tests for the utilities module.

Tests core utility functions that work with the SDK client.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from amplifier.ccsdk_toolkit.tests.mock_sdk_client import MockSDKClient
from amplifier.ccsdk_toolkit.tests.mock_sdk_client import MockSDKClientWithErrors
from amplifier.ccsdk_toolkit.utilities import batch_query
from amplifier.ccsdk_toolkit.utilities import parse_sdk_response
from amplifier.ccsdk_toolkit.utilities import query_with_retry


class TestQueryWithRetry:
    """Test the query_with_retry utility."""

    @pytest.mark.asyncio
    async def test_successful_query(self):
        """Test successful query without retries."""
        client = MockSDKClient()
        response = await query_with_retry(client, "test prompt")

        assert response is not None
        assert response.content is not None
        assert "Mock response" in response.content

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry logic on timeout errors."""
        client = MockSDKClientWithErrors(error_sequence=["timeout", "timeout"])

        # Should succeed on third attempt (after 2 timeouts)
        response = await query_with_retry(client, "test prompt", max_retries=3, retry_delay=0.1)

        assert response is not None
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries raises error."""
        client = MockSDKClientWithErrors(error_sequence=["timeout", "timeout", "timeout", "timeout"])

        with pytest.raises((TimeoutError, RuntimeError)):
            await query_with_retry(client, "test prompt", max_retries=3, retry_delay=0.1)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff between retries."""
        client = MockSDKClientWithErrors(error_sequence=["timeout"])

        start = asyncio.get_event_loop().time()
        await query_with_retry(client, "test prompt", max_retries=2, retry_delay=0.1)
        elapsed = asyncio.get_event_loop().time() - start

        # Should have at least initial delay
        assert elapsed >= 0.1


class TestBatchQuery:
    """Test the batch_query utility."""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test processing multiple prompts in batch."""
        client = MockSDKClient()
        prompts = [f"prompt {i}" for i in range(5)]

        responses = await batch_query(client, prompts, max_concurrent=2)

        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert response is not None
            assert f"prompt {i}" in response.content

    @pytest.mark.asyncio
    async def test_batch_with_errors(self):
        """Test batch processing handles individual errors."""
        client = MockSDKClientWithErrors(error_sequence=["success", "api", "success", "connection", "success"])
        prompts = [f"prompt {i}" for i in range(5)]

        responses = await batch_query(client, prompts, max_concurrent=1)

        # Should get responses even with some errors
        assert len(responses) == 5
        # Check that some succeeded
        success_count = sum(1 for r in responses if r and not r.error)
        assert success_count >= 3

    @pytest.mark.asyncio
    async def test_empty_batch(self):
        """Test handling empty prompt list."""
        client = MockSDKClient()
        responses = await batch_query(client, [])

        assert responses == []


class TestParseSDKResponse:
    """Test the parse_sdk_response utility."""

    def test_parse_json_response(self):
        """Test parsing JSON from response."""
        response = MagicMock()
        response.content = json.dumps({"status": "success", "data": [1, 2, 3]})

        parsed = parse_sdk_response(response)

        # parse_sdk_response returns a dict with the content
        assert "content" in parsed
        # Since the content is JSON, it should be parsed
        content_parsed = json.loads(parsed["content"])
        assert content_parsed["status"] == "success"
        assert content_parsed["data"] == [1, 2, 3]

    def test_parse_object_response(self):
        """Test parsing response object with attributes."""
        response = MagicMock()
        response.content = "Test content"
        response.text = "Test text"

        parsed = parse_sdk_response(response)

        assert "content" in parsed
        assert parsed["content"] == "Test content"

    def test_parse_dict_response(self):
        """Test parsing dict response."""
        response = {"text": "Hello", "metadata": {"timestamp": "2024-01-01"}}

        parsed = parse_sdk_response(response)

        assert "content" in parsed
        assert parsed["content"] == "Hello"  # Should extract from 'text' field

    def test_plain_text_response(self):
        """Test handling plain text response."""
        response = "This is plain text"

        result = parse_sdk_response(response)

        assert result["content"] == "This is plain text"


class TestFileOperations:
    """Test file operation utilities."""

    def test_save_response(self):
        """Test saving response to file."""
        from amplifier.ccsdk_toolkit.utilities import save_response

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "response.json"
            response = MagicMock()
            response.content = json.dumps({"test": "data"})
            response.__dict__ = {"content": response.content}

            result_path = save_response(response, filepath)

            assert result_path.exists()
            with open(result_path) as f:
                data = json.load(f)
            # save_response wraps the content
            assert "content" in data

    def test_save_response_text_format(self):
        """Test saving response in text format."""
        from amplifier.ccsdk_toolkit.utilities import save_response

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "response.txt"
            response = MagicMock()
            response.content = "This is test content"
            response.__dict__ = {"content": response.content}

            result_path = save_response(response, filepath, format="txt")

            assert result_path.exists()
            with open(result_path) as f:
                content = f.read()
            assert "This is test content" in content


class TestIntegrationWithSDK:
    """Test integration with real SDK patterns."""

    @pytest.mark.asyncio
    async def test_conversation_flow(self):
        """Test a conversation flow with utilities."""
        client = MockSDKClient()

        # Initial query
        response1 = await query_with_retry(client, "Hello, let's analyze some data")
        assert response1 is not None

        # Follow-up with context
        response2 = await query_with_retry(
            client, "You are a data analyst. Based on the previous analysis, what's next?"
        )
        assert response2 is not None

        # Verify conversation history
        assert len(client.conversation_history) == 4  # 2 queries, 2 responses

    @pytest.mark.asyncio
    async def test_parallel_processing(self):
        """Test parallel processing of multiple queries."""
        client = MockSDKClient(response_delay=0.05)
        prompts = [f"Process item {i}" for i in range(10)]

        # Process in parallel (should be faster than sequential)
        start = asyncio.get_event_loop().time()
        responses = await batch_query(client, prompts, max_concurrent=5)
        elapsed = asyncio.get_event_loop().time() - start

        assert len(responses) == 10
        # With batch_size=5 and delay=0.05, should take ~0.1s (2 batches)
        # Sequential would take ~0.5s
        assert elapsed < 0.3  # Allow some overhead

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery in utility functions."""
        # Client that fails twice then succeeds
        client = MockSDKClientWithErrors(error_sequence=["connection", "rate_limit"])

        response = await query_with_retry(client, "Important query", max_retries=3)

        assert response is not None
        assert "Important query" in response.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
