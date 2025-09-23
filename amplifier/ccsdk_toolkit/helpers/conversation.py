"""ConversationManager - Manages multi-turn conversations with context

This helper uses the SDK client through composition to manage conversation
history and context for multi-turn interactions.
"""

import json
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier.ccsdk_toolkit.utilities import query_with_retry


@dataclass
class ConversationTurn:
    """Single turn in a conversation"""

    timestamp: str
    user_message: str
    assistant_response: str
    metadata: dict[str, Any] | None = None


class ConversationManager:
    """Manages multi-turn conversations with context.

    Uses the SDK client through composition to maintain conversation
    history and provide context-aware queries.
    """

    def __init__(self, client: Any):
        """Initialize with an SDK client.

        Args:
            client: Initialized ClaudeSDKClient instance
        """
        self.client = client
        self.conversation_turns: list[ConversationTurn] = []
        self.metadata: dict[str, Any] = {"created_at": datetime.now().isoformat(), "turn_count": 0}

    def add_turn(self, user_message: str, assistant_response: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a conversation turn.

        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            metadata: Optional metadata for this turn
        """
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            assistant_response=assistant_response,
            metadata=metadata,
        )
        self.conversation_turns.append(turn)
        self.metadata["turn_count"] += 1
        self.metadata["last_updated"] = turn.timestamp

    def get_context(self, max_turns: int | None = None) -> str:
        """Get conversation history as formatted context.

        Args:
            max_turns: Maximum number of recent turns to include

        Returns:
            Formatted conversation history
        """
        turns_to_include = self.conversation_turns
        if max_turns is not None and max_turns > 0:
            turns_to_include = self.conversation_turns[-max_turns:]

        if not turns_to_include:
            return ""

        context_parts = ["Previous conversation:"]
        for turn in turns_to_include:
            context_parts.append(f"\nUser: {turn.user_message}")
            context_parts.append(f"Assistant: {turn.assistant_response}")

        return "\n".join(context_parts)

    async def query_with_context(
        self, prompt: str, max_context_turns: int | None = None, save_turn: bool = True
    ) -> str:
        """Query with conversation context.

        Args:
            prompt: User's new query
            max_context_turns: Maximum turns to include in context
            save_turn: Whether to save this turn to history

        Returns:
            Assistant's response
        """
        # Build prompt with context
        context = self.get_context(max_context_turns)
        if context:
            full_prompt = f"{context}\n\nUser: {prompt}"
        else:
            full_prompt = prompt

        # Query using utilities for retry logic
        response = await query_with_retry(self.client, full_prompt, max_retries=3)

        # Save turn if requested
        if save_turn:
            self.add_turn(prompt, response)

        return response

    def save_to_file(self, filepath: Path | str) -> None:
        """Save conversation to file.

        Args:
            filepath: Path to save conversation
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {"metadata": self.metadata, "conversation": [asdict(turn) for turn in self.conversation_turns]}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filepath: Path | str) -> None:
        """Load conversation from file.

        Args:
            filepath: Path to load conversation from
        """
        filepath = Path(filepath)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        self.metadata = data.get("metadata", {})
        self.conversation_turns = [ConversationTurn(**turn) for turn in data.get("conversation", [])]

    def clear(self) -> None:
        """Clear conversation history."""
        self.conversation_turns = []
        self.metadata = {"created_at": datetime.now().isoformat(), "turn_count": 0}

    def get_summary(self) -> dict[str, Any]:
        """Get conversation summary.

        Returns:
            Dictionary with conversation metadata and statistics
        """
        return {
            **self.metadata,
            "total_user_chars": sum(len(t.user_message) for t in self.conversation_turns),
            "total_assistant_chars": sum(len(t.assistant_response) for t in self.conversation_turns),
            "average_turn_length": (
                sum(len(t.user_message) + len(t.assistant_response) for t in self.conversation_turns)
                / len(self.conversation_turns)
                if self.conversation_turns
                else 0
            ),
        }
