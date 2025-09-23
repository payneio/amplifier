"""StreamingQuery context manager for streaming responses with progress tracking.

This module provides a focused context manager for streaming AI responses
with optional progress indicators and clean resource management.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from amplifier.ccsdk_toolkit.client import ClaudeCodeSDKClient
else:
    ClaudeCodeSDKClient = Any

logger = logging.getLogger(__name__)


class StreamingQuery:
    """Context manager for streaming AI responses with progress tracking.

    This context manager provides a clean interface for streaming responses
    from the AI with optional progress indicators and proper cleanup.

    Example:
        ```python
        async with StreamingQuery(client, show_progress=True) as query:
            response = await query.ask("Analyze this code")
            # Or stream chunks
            async for chunk in query.stream("Generate documentation"):
                print(chunk, end="")
        ```

    Attributes:
        client: Initialized Claude Code SDK client
        show_progress: Whether to show progress indicators
        buffer_size: Size of internal buffer for streaming
    """

    def __init__(self, client: ClaudeCodeSDKClient, show_progress: bool = True, buffer_size: int = 1024):
        """Initialize the StreamingQuery context manager.

        Args:
            client: Initialized SDK client
            show_progress: Whether to show progress indicators
            buffer_size: Size of internal streaming buffer
        """
        self.client = client
        self.show_progress = show_progress
        self.buffer_size = buffer_size

        self._progress_tracker: Any | None = None
        self._active_streams: list[AsyncIterator] = []
        self._response_buffer: list[str] = []

    async def __aenter__(self) -> "StreamingQuery":
        """Enter the context manager and set up streaming resources.

        Returns:
            Self for use in async with statement
        """
        logger.debug("Entering StreamingQuery context")

        # Initialize progress tracking if needed
        if self.show_progress:
            # Simple progress tracking for streaming
            self._progress_tracker = True
            logger.info("Starting streaming response")

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Exit the context manager and clean up streaming resources.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        logger.debug("Exiting StreamingQuery context")

        # Clean up any active streams
        for stream in self._active_streams:
            try:
                if hasattr(stream, "aclose"):
                    await stream.aclose()  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")

        # Clean up progress tracking
        if self._progress_tracker:
            logger.info("Streaming complete")

        # Clear buffers
        self._response_buffer.clear()
        self._active_streams.clear()

    async def ask(self, prompt: str, **kwargs: Any) -> str:
        """Send a query and get complete response with optional streaming display.

        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the query

        Returns:
            Complete response text
        """
        response_parts = []

        # Stream the response with progress
        async for chunk in self.stream(prompt, **kwargs):
            response_parts.append(chunk)

            if self.show_progress and self._progress_tracker:
                # Update progress with chunk count
                logger.debug(f"Streaming response ({len(response_parts)} chunks)")

        return "".join(response_parts)

    async def stream(self, prompt: str, chunk_callback: Any | None = None, **kwargs: Any) -> AsyncIterator[str]:
        """Stream response chunks as they arrive.

        Args:
            prompt: The prompt to send
            chunk_callback: Optional callback for each chunk
            **kwargs: Additional arguments for the query

        Yields:
            Response chunks as they arrive
        """
        try:
            # Check if client supports streaming
            if hasattr(self.client, "stream_query"):
                stream = self.client.stream_query(prompt, **kwargs)
            else:
                # Fallback to non-streaming with simulated chunks
                logger.debug("Client doesn't support streaming, using fallback")
                stream = self._simulate_streaming(prompt, **kwargs)

            # Track this stream
            self._active_streams.append(stream)

            # Stream chunks
            chunk_count = 0
            async for chunk in stream:
                chunk_count += 1

                # Update progress
                if self._progress_tracker and chunk_count % 10 == 0:
                    logger.debug(f"Streaming chunk {chunk_count}")

                # Call callback if provided
                if chunk_callback:
                    await chunk_callback(chunk) if asyncio.iscoroutinefunction(chunk_callback) else chunk_callback(
                        chunk
                    )

                # Buffer the chunk
                self._response_buffer.append(chunk)

                yield chunk

        finally:
            # Remove from active streams
            if stream in self._active_streams:
                self._active_streams.remove(stream)

    async def _simulate_streaming(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Simulate streaming for clients without native streaming support.

        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the query

        Yields:
            Simulated response chunks
        """
        # Get complete response
        response = await self.client.query_with_retry(prompt, **kwargs)

        # Simulate streaming by yielding in chunks
        words = response.split()
        chunk_size = max(1, len(words) // 10)  # Aim for ~10 chunks

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk = " ".join(chunk_words)

            if i + chunk_size < len(words):
                chunk += " "  # Add space between chunks

            yield chunk

            # Small delay to simulate streaming
            await asyncio.sleep(0.05)

    async def ask_with_context(self, prompt: str, context: dict[str, Any], **kwargs: Any) -> str:
        """Send a query with additional context.

        Args:
            prompt: The main prompt
            context: Additional context to include
            **kwargs: Additional arguments

        Returns:
            Complete response text
        """
        # Format prompt with context
        context_lines = [f"{key}: {value}" for key, value in context.items()]
        full_prompt = f"{prompt}\n\nContext:\n" + "\n".join(context_lines)

        return await self.ask(full_prompt, **kwargs)

    async def multi_turn_conversation(self, prompts: list[str], continue_on_error: bool = False) -> list[str]:
        """Have a multi-turn conversation with context preservation.

        Args:
            prompts: List of prompts to send sequentially
            continue_on_error: Whether to continue if a prompt fails

        Returns:
            List of responses for each prompt
        """
        responses = []
        conversation_context = []

        for i, prompt in enumerate(prompts, 1):
            if self._progress_tracker:
                logger.debug(f"Processing prompt {i}/{len(prompts)}")

            try:
                # Include conversation history in prompt
                if conversation_context:
                    context_prompt = "\n".join(
                        [
                            "Previous conversation:",
                            *[f"Q: {q}\nA: {a}" for q, a in conversation_context],
                            "",
                            f"Current question: {prompt}",
                        ]
                    )
                else:
                    context_prompt = prompt

                # Get response
                response = await self.ask(context_prompt)
                responses.append(response)

                # Update conversation context
                conversation_context.append((prompt, response))

            except Exception as e:
                logger.error(f"Error in prompt {i}: {e}")

                if continue_on_error:
                    responses.append(f"Error: {str(e)}")
                else:
                    raise

        return responses

    @property
    def buffered_response(self) -> str:
        """Get the complete buffered response so far."""
        return "".join(self._response_buffer)

    def clear_buffer(self) -> None:
        """Clear the response buffer."""
        self._response_buffer.clear()
