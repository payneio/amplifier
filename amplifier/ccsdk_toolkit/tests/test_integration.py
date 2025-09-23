"""Integration tests for CCSDK toolkit patterns.

Tests that verify the patterns work together with the SDK.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

# Import all the patterns we're testing
from amplifier.ccsdk_toolkit.context_managers import FileProcessor
from amplifier.ccsdk_toolkit.context_managers import SessionContext
from amplifier.ccsdk_toolkit.decorators import sdk_function
from amplifier.ccsdk_toolkit.decorators import with_logging
from amplifier.ccsdk_toolkit.decorators import with_retry
from amplifier.ccsdk_toolkit.defensive import isolate_prompt
from amplifier.ccsdk_toolkit.defensive import parse_llm_json
from amplifier.ccsdk_toolkit.defensive import write_json_with_retry
from amplifier.ccsdk_toolkit.helpers import BatchProcessor
from amplifier.ccsdk_toolkit.helpers import ConversationManager
from amplifier.ccsdk_toolkit.tests.mock_sdk_client import MockSDKClient
from amplifier.ccsdk_toolkit.tests.mock_sdk_client import MockSDKClientWithErrors
from amplifier.ccsdk_toolkit.utilities import batch_query
from amplifier.ccsdk_toolkit.utilities import query_with_retry


class TestBasicSDKIntegration:
    """Test basic SDK integration with patterns."""

    @pytest.mark.asyncio
    async def test_simple_query_flow(self):
        """Test a simple query through the patterns."""
        client = MockSDKClient()

        # Use utility for retry logic
        response = await query_with_retry(client, "Hello, analyze this")

        assert response is not None
        assert response.content is not None
        assert "Mock response" in response.content

    @pytest.mark.asyncio
    async def test_error_handling_flow(self):
        """Test error handling through the patterns."""
        client = MockSDKClientWithErrors(error_sequence=["timeout", "api", "success"])

        # Should retry and eventually succeed
        response = await query_with_retry(client, "Test query", max_retries=4)

        assert response is not None
        assert "Test query" in response.content


class TestConversationWorkflow:
    """Test conversation management workflow."""

    @pytest.mark.asyncio
    async def test_conversation_with_context(self):
        """Test managing a conversation with context."""
        client = MockSDKClient()
        manager = ConversationManager(client)

        # First query
        response1 = await manager.query_with_context("What is AI?")
        assert response1 is not None

        # Follow-up with context
        response2 = await manager.query_with_context("Tell me more about that")
        assert response2 is not None

        # Verify conversation history is maintained
        assert len(manager.conversation_turns) >= 2

        # Format for display
        formatted = manager.get_context()
        assert "What is AI?" in formatted

    @pytest.mark.asyncio
    async def test_conversation_with_defensive_parsing(self):
        """Test conversation with defensive JSON parsing."""
        client = MockSDKClient(malformed_json_probability=0.5)
        manager = ConversationManager(client)

        # Query that returns JSON
        response = await manager.query_with_context("Give me JSON data")

        # Parse with defensive utilities
        parsed = parse_llm_json(response, default={"status": "error"})

        assert parsed is not None
        assert "status" in parsed or "error" in parsed


class TestBatchProcessingWorkflow:
    """Test batch processing workflows."""

    @pytest.mark.asyncio
    async def test_batch_file_processing(self):
        """Test processing multiple files in batch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = []
            for i in range(5):
                filepath = Path(tmpdir) / f"file_{i}.txt"
                filepath.write_text(f"Content {i}")
                files.append(filepath)

            client = MockSDKClient()
            processor = BatchProcessor(client)

            # Process files
            async def analyze_file(client, filepath):
                content = filepath.read_text()
                response = await client.query(f"Analyze: {content}")
                return {"file": filepath.name, "analysis": response.content}

            results = await processor.process_items(files, analyze_file)

            assert len(results) == 5
            for result in results:
                assert result.status == "success"
                assert result.result is not None

    @pytest.mark.asyncio
    async def test_batch_with_error_recovery(self):
        """Test batch processing with error recovery."""
        client = MockSDKClientWithErrors(error_sequence=["success", "api", "success", "timeout", "success"])

        prompts = [f"Query {i}" for i in range(5)]

        # Use batch query with retry
        responses = await batch_query(client, prompts, max_concurrent=2)

        # Should have responses for all, even with errors
        assert len(responses) == 5

        # Count successful responses
        success_count = sum(1 for r in responses if r and not getattr(r, "error", None))
        assert success_count >= 3  # At least 3 should succeed


class TestSessionManagement:
    """Test session management workflows."""

    @pytest.mark.asyncio
    async def test_session_workflow(self):
        """Test complete session workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = MockSDKClient()

            async with SessionContext(client, sessions_dir=Path(tmpdir)) as session:
                # Add queries to session
                await session.query("First question")
                await session.query("Second question")

                assert len(session.history) >= 2  # 2 queries

                # Session should auto-save on exit

            # Verify session was saved
            session_files = list(Path(tmpdir).glob("*.json"))
            assert len(session_files) > 0

    @pytest.mark.asyncio
    async def test_session_with_file_processing(self):
        """Test session with file processing integration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(3):
                filepath = Path(tmpdir) / f"doc_{i}.md"
                filepath.write_text(f"# Document {i}\n\nContent here.")

            client = MockSDKClient()

            async with FileProcessor(client, tmpdir, "*.md") as processor:

                async def process_file(file_path, content):
                    return f"Processed: {file_path.name}"

                results = await processor.process_batch(process_file)

                assert len(results) == 3
                for file_path, result in results.items():
                    assert "doc_" in file_path.name
                    assert "Processed:" in result


class TestDefensiveIntegration:
    """Test defensive utilities integration."""

    @pytest.mark.asyncio
    async def test_defensive_query_chain(self):
        """Test complete defensive query chain."""
        client = MockSDKClient(malformed_json_probability=0.7, error_probability=0.2)

        # Isolate prompt to prevent injection
        prompt = "Analyze this data and return JSON"
        data_content = "sample data to analyze"
        isolated = isolate_prompt(prompt, data_content)

        # Query with retry
        response = await query_with_retry(client, isolated, max_retries=3)

        # Parse response defensively
        if response and response.content:
            parsed = parse_llm_json(response.content, default={"status": "failed"})
            assert parsed is not None

    @pytest.mark.asyncio
    async def test_defensive_file_operations(self):
        """Test defensive file operations."""
        from amplifier.ccsdk_toolkit.defensive import write_json_with_retry

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MockSDKClient()

            # Generate response
            response = await client.query("Generate some data")

            # Parse defensively
            data = parse_llm_json(response.content, default={"generated": True})

            # Save with retry logic
            filepath = Path(tmpdir) / "output.json"
            write_json_with_retry(data, filepath)

            assert filepath.exists()

            # Verify saved data
            with open(filepath) as f:
                loaded = json.load(f)
            assert loaded is not None


class TestDecoratorIntegration:
    """Test decorator pattern integration."""

    @pytest.mark.asyncio
    async def test_decorated_sdk_function(self):
        """Test SDK function with decorators."""

        @with_retry(attempts=3)
        @with_logging()
        @sdk_function()
        async def analyze_text(client, text: str):
            """Analyze text with SDK."""
            response = await client.query(f"Analyze: {text}")
            return parse_llm_json(response, default={})

        client = MockSDKClient()
        result = await analyze_text(client, "Test text")

        assert result is not None

    @pytest.mark.asyncio
    async def test_decorated_batch_processor(self):
        """Test decorated batch processing."""

        @with_logging()
        async def process_batch_with_sdk(client, items):
            """Process batch with logging."""
            processor = BatchProcessor(client)

            @with_retry(attempts=2)
            async def process_item(client, item):
                return await client.query(f"Process: {item}")

            return await processor.process_items(items, process_item)

        client = MockSDKClient()
        items = ["item1", "item2", "item3"]
        results = await process_batch_with_sdk(client, items)

        assert len(results) == 3


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_document_analysis_workflow(self):
        """Test complete document analysis workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create documents
            docs = []
            for i in range(3):
                doc_path = Path(tmpdir) / f"document_{i}.md"
                doc_path.write_text(f"# Document {i}\n\nContent for analysis.")
                docs.append(doc_path)

            # Initialize components
            client = MockSDKClient()
            conversation = ConversationManager(client)

            # Step 1: Load and analyze documents
            analyses = []
            for doc in docs:
                content = doc.read_text()
                isolated = isolate_prompt(f"Analyze: {content}", content)
                response = await conversation.query_with_context(isolated)
                parsed = parse_llm_json(response, default={"text": response})
                analyses.append(parsed)

            assert len(analyses) == 3

            # Step 2: Synthesize results
            synthesis_prompt = "Synthesize the previous analyses"
            synthesis_response = await conversation.query_with_context(synthesis_prompt)

            # Step 3: Save results
            results = {
                "analyses": analyses,
                "synthesis": synthesis_response,
                "conversation": conversation.conversation_turns,
            }

            output_path = Path(tmpdir) / "results.json"
            write_json_with_retry(results, output_path)

            assert output_path.exists()

    @pytest.mark.asyncio
    async def test_parallel_analysis_workflow(self):
        """Test parallel analysis of multiple inputs."""
        client = MockSDKClient(response_delay=0.05)

        # Create multiple analysis tasks
        tasks = []
        for category in ["technical", "business", "user"]:
            for i in range(3):
                prompt = f"Analyze {category} aspect {i}"
                tasks.append(prompt)

        # Process in parallel with defensive parsing
        start_time = asyncio.get_event_loop().time()
        responses = await batch_query(client, tasks, max_concurrent=5)
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should be faster than sequential (9 * 0.05 = 0.45s)
        assert elapsed < 0.3  # Parallel should be much faster

        # Parse all responses defensively
        parsed_results = []
        for response in responses:
            if response:
                parsed = parse_llm_json(response, default={"content": response})
                parsed_results.append(parsed)

        assert len(parsed_results) == 9


class TestRealSDKCompatibility:
    """Test compatibility with real SDK patterns."""

    def test_mock_client_interface(self):
        """Test mock client matches expected SDK interface."""
        client = MockSDKClient()

        # Should have expected methods
        assert hasattr(client, "query")
        assert hasattr(client, "stream_query")
        assert hasattr(client, "connect")
        assert hasattr(client, "disconnect")

    @pytest.mark.asyncio
    async def test_sdk_response_format(self):
        """Test response format matches SDK expectations."""
        client = MockSDKClient()
        response = await client.query("Test")

        # Should have expected attributes
        assert hasattr(response, "content")
        assert hasattr(response, "metadata")
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_streaming_interface(self):
        """Test streaming interface compatibility."""
        client = MockSDKClient()

        chunks = []
        async for chunk in client.stream_query("Stream this"):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert "Stream this" in full_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
