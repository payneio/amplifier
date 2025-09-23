"""SessionContext manager for managing AI conversation sessions.

This module provides a focused context manager for managing conversation
sessions with state persistence and automatic cleanup.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from amplifier.ccsdk_toolkit.client import ClaudeCodeSDKClient
else:
    ClaudeCodeSDKClient = Any

logger = logging.getLogger(__name__)


class SessionContext:
    """Context manager for AI conversation sessions with state management.

    This context manager provides a clean interface for managing multi-turn
    conversations with automatic session persistence and cleanup.

    Example:
        ```python
        async with SessionContext(client, session_name="analysis") as session:
            response1 = await session.query("What is this code doing?")
            response2 = await session.query("Can you improve it?")
            # Session automatically saved on exit
        ```

    Attributes:
        client: Initialized Claude Code SDK client
        session_name: Name for the session
        persist_to_file: Whether to save session to file
        auto_save_interval: Number of queries between auto-saves
    """

    def __init__(
        self,
        client: ClaudeCodeSDKClient,
        session_name: str = "default",
        persist_to_file: bool = True,
        auto_save_interval: int = 5,
        sessions_dir: Path | None = None,
    ):
        """Initialize the SessionContext manager.

        Args:
            client: Initialized SDK client
            session_name: Name for the session
            persist_to_file: Whether to save session to file
            auto_save_interval: Number of queries between auto-saves
            sessions_dir: Directory for session files (default: ./sessions)
        """
        self.client = client
        self.session_name = session_name
        self.persist_to_file = persist_to_file
        self.auto_save_interval = auto_save_interval
        self.sessions_dir = Path(sessions_dir) if sessions_dir else Path("sessions")

        self._session_manager: Any | None = None
        self._query_count: int = 0
        self._session_file: Path | None = None
        self._conversation_history: list[dict[str, Any]] = []
        self._session_metadata: dict[str, Any] = {}

    async def __aenter__(self) -> "SessionContext":
        """Enter the context manager and initialize session.

        Returns:
            Self for use in async with statement
        """
        logger.debug(f"Entering SessionContext for session: {self.session_name}")

        # Initialize session manager (simplified)
        self._session_manager = self.client  # Use client directly

        # Set up session file if persistence is enabled
        if self.persist_to_file:
            self._setup_session_file()
            self._load_existing_session()

        # Initialize session metadata
        self._session_metadata = {
            "session_name": self.session_name,
            "started_at": datetime.now().isoformat(),
            "query_count": 0,
        }

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Exit the context manager and save session.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        logger.debug(f"Exiting SessionContext for session: {self.session_name}")

        # Update session metadata
        self._session_metadata["ended_at"] = datetime.now().isoformat()
        self._session_metadata["query_count"] = self._query_count

        # Save session if persistence is enabled
        if self.persist_to_file:
            self._save_session()

        # Log session summary
        logger.info(f"Session '{self.session_name}' complete: {self._query_count} queries processed")

    def _setup_session_file(self) -> None:
        """Set up the session file for persistence."""
        # Create sessions directory if it doesn't exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Generate session filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_file = self.sessions_dir / f"{self.session_name}_{timestamp}.json"

    def _load_existing_session(self) -> None:
        """Load an existing session if resuming."""
        # Look for most recent session file with same name
        pattern = f"{self.session_name}_*.json"
        existing_files = list(self.sessions_dir.glob(pattern))

        if existing_files:
            # Sort by modification time and get most recent
            most_recent = max(existing_files, key=lambda p: p.stat().st_mtime)

            try:
                with open(most_recent) as f:
                    data = json.load(f)
                    self._conversation_history = data.get("history", [])
                    self._session_metadata = data.get("metadata", {})
                    self._query_count = len(self._conversation_history)

                logger.info(f"Resumed session from {most_recent}")

            except Exception as e:
                logger.warning(f"Could not load existing session: {e}")

    def _save_session(self) -> None:
        """Save the current session to file."""
        if not self._session_file:
            return

        try:
            session_data = {"metadata": self._session_metadata, "history": self._conversation_history}

            with open(self._session_file, "w") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Session saved to {self._session_file}")

        except Exception as e:
            logger.error(f"Error saving session: {e}")

    async def query(self, prompt: str, save_immediately: bool = False, **kwargs: Any) -> str:
        """Send a query within the session context.

        Args:
            prompt: The prompt to send
            save_immediately: Whether to save session immediately after query
            **kwargs: Additional arguments for the query

        Returns:
            Response from the AI
        """
        if not self._session_manager:
            raise RuntimeError("SessionContext not properly initialized")

        # Build context from history
        context_prompt = self._build_context_prompt(prompt)

        # Send query using client
        response = await self.client.query_with_retry(context_prompt, **kwargs)

        # Update conversation history
        self._conversation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "response": response,
                "query_index": self._query_count,
            }
        )

        self._query_count += 1

        # Auto-save if interval reached or explicitly requested
        if save_immediately or (self.persist_to_file and self._query_count % self.auto_save_interval == 0):
            self._save_session()

        return response

    def _build_context_prompt(self, prompt: str) -> str:
        """Build a prompt with conversation context.

        Args:
            prompt: The current prompt

        Returns:
            Prompt with conversation history context
        """
        if not self._conversation_history:
            return prompt

        # Include relevant recent history
        history_limit = 5  # Include last 5 exchanges
        recent_history = self._conversation_history[-history_limit:]

        context_parts = ["Previous conversation:"]
        for entry in recent_history:
            context_parts.append(f"Q: {entry['prompt']}")
            context_parts.append(f"A: {entry['response'][:200]}...")  # Truncate long responses

        context_parts.append("")
        context_parts.append(f"Current question: {prompt}")

        return "\n".join(context_parts)

    async def query_batch(self, prompts: list[str], continue_on_error: bool = True) -> list[str]:
        """Process multiple queries in sequence.

        Args:
            prompts: List of prompts to process
            continue_on_error: Whether to continue if a query fails

        Returns:
            List of responses
        """
        responses = []

        for prompt in prompts:
            try:
                response = await self.query(prompt)
                responses.append(response)

            except Exception as e:
                logger.error(f"Error processing prompt: {e}")

                if continue_on_error:
                    responses.append(f"Error: {str(e)}")
                else:
                    raise

        return responses

    async def summarize_session(self) -> str:
        """Generate a summary of the session.

        Returns:
            Summary of the conversation
        """
        if not self._conversation_history:
            return "No conversation history to summarize"

        # Build summary prompt
        summary_prompt = "Please provide a concise summary of this conversation:\n\n"

        for entry in self._conversation_history:
            summary_prompt += f"Q: {entry['prompt']}\n"
            summary_prompt += f"A: {entry['response'][:200]}...\n\n"

        summary_prompt += "Summary:"

        # Get summary from AI
        response = await self.client.query_with_retry(summary_prompt)

        return response

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._conversation_history.clear()
        self._query_count = 0
        logger.debug("Conversation history cleared")

    @property
    def history(self) -> list[dict[str, Any]]:
        """Get the conversation history."""
        return self._conversation_history.copy()

    @property
    def query_count(self) -> int:
        """Get the number of queries in this session."""
        return self._query_count

    @property
    def session_info(self) -> dict[str, Any]:
        """Get session metadata and statistics."""
        return {
            **self._session_metadata,
            "current_query_count": self._query_count,
            "session_file": str(self._session_file) if self._session_file else None,
        }
