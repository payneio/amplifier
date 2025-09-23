"""Tests for the helpers module.

Tests helper classes that work with the SDK client.
"""

import json
import tempfile

import pytest

from amplifier.ccsdk_toolkit.helpers import BatchProcessor
from amplifier.ccsdk_toolkit.helpers import ConversationManager
from amplifier.ccsdk_toolkit.helpers import SessionManager
from amplifier.ccsdk_toolkit.tests.mock_sdk_client import MockSDKClient


class TestConversationManager:
    """Test the ConversationManager helper."""

    @pytest.mark.asyncio
    async def test_basic_conversation(self):
        """Test basic conversation flow."""
        client = MockSDKClient()
        manager = ConversationManager(client)

        # First message
        response1 = await manager.query_with_context("Hello")
        assert response1 is not None

        # Check conversation history
        assert len(manager.conversation_turns) == 2  # User + assistant

        # Second message with context
        response2 = await manager.query_with_context("What did I just say?")
        assert response2 is not None
        assert len(manager.conversation_turns) == 4

    @pytest.mark.asyncio
    async def test_max_history_limit(self):
        """Test conversation history truncation."""
        client = MockSDKClient()
        manager = ConversationManager(client)

        # Add multiple messages
        for i in range(5):
            await manager.query_with_context(f"Message {i}")

        # History should be truncated to max_history
        assert len(manager.conversation_turns) <= 4

    def test_clear_history(self):
        """Test clearing conversation history."""
        client = MockSDKClient()
        manager = ConversationManager(client)

        # Add some history via the proper method
        manager.add_turn("Test message", "Test response")

        manager.clear()
        assert len(manager.conversation_turns) == 0

    def test_format_for_prompt(self):
        """Test formatting conversation for prompt."""
        client = MockSDKClient()
        manager = ConversationManager(client)

        # Add conversation turns properly
        manager.add_turn("Hello", "Hi there!")

        formatted = manager.get_context()
        assert "Hello" in formatted
        assert "Hi there!" in formatted


class TestBatchProcessor:
    """Test the BatchProcessor helper."""

    @pytest.mark.asyncio
    async def test_process_items(self):
        """Test batch processing of items."""
        client = MockSDKClient()
        processor = BatchProcessor(client)

        items = ["item1", "item2", "item3", "item4", "item5"]

        async def process_func(client, item):
            await client.query(f"Process {item}")
            return f"Processed: {item}"

        results = await processor.process_items(items, process_func)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.status == "success"
            assert f"item{i + 1}" in result.item_id

    @pytest.mark.asyncio
    async def test_process_with_progress(self):
        """Test batch processing with progress callback."""
        client = MockSDKClient()
        processor = BatchProcessor(client)

        items = ["item1", "item2", "item3"]
        progress_updates = []

        def on_progress(completed, total):
            progress_updates.append((completed, total))

        async def process_func(client, item):
            return f"Processed: {item}"

        await processor.process_items(items, process_func, progress_callback=on_progress)

        assert len(progress_updates) > 0
        assert progress_updates[-1] == (3, 3)  # Final should be all complete

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in batch processing."""
        client = MockSDKClient()
        processor = BatchProcessor(client)

        items = ["good1", "error", "good2"]

        async def process_func(client, item):
            if item == "error":
                raise ValueError("Test error")
            return f"Processed: {item}"

        results = await processor.process_items(items, process_func)

        assert len(results) == 3
        assert results[0].status == "success"
        assert results[1].status == "error"
        assert results[2].status == "success"
        assert results[0].result and "Processed: good1" in results[0].result
        assert results[2].result and "Processed: good2" in results[2].result


class TestSessionManager:
    """Test the SessionManager helper."""

    def test_create_session(self):
        """Test creating a new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = MockSDKClient()
            manager = SessionManager(client, session_dir=tmpdir)

            session = manager.create_session("test_session")

            assert session is not None
            assert manager.current_session is not None
            assert manager.current_session.name == "test_session"

    def test_save_and_load_session(self):
        """Test saving and loading sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = MockSDKClient()
            manager = SessionManager(client, session_dir=tmpdir)

            # Create and populate session
            manager.create_session("test")
            manager.set_session_data(
                "messages", [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
            )

            # Save session
            assert manager.current_session is not None
            session_id = manager.current_session.session_id
            manager.save_session()
            session_file = manager.session_dir / f"{session_id}.json"
            assert session_file.exists()

            # Create new manager and load
            manager2 = SessionManager(client, session_dir=tmpdir)
            session = manager2.load_session(session_id)

            assert session is not None
            messages = manager2.get_session_data("messages")
            assert len(messages) == 2
            assert messages[0]["content"] == "Hello"

    def test_list_sessions(self):
        """Test listing saved sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = MockSDKClient()
            manager = SessionManager(client, session_dir=tmpdir)

            # Create and save multiple sessions
            for i in range(3):
                manager.create_session(f"session_{i}")
                manager.save_session()

            # List sessions
            sessions = manager.list_sessions()
            assert len(sessions) >= 3

    def test_session_export(self):
        """Test exporting session data."""
        client = MockSDKClient()
        manager = SessionManager(client)

        manager.create_session("export_test")
        manager.set_session_data(
            "messages", [{"role": "user", "content": "Question?"}, {"role": "assistant", "content": "Answer!"}]
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        manager.export_session(export_path)

        with open(export_path) as f:
            data = json.load(f)

        assert data["name"] == "export_test"
        assert len(data["data"]["messages"]) == 2


# ResponseFormatter tests removed - class doesn't exist yet


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
