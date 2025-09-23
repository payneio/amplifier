"""Mock SDK Client for testing without API keys.

This module provides a mock implementation of the ClaudeSDKClient
that mimics the behavior of the real SDK for testing purposes.
"""

import asyncio
import json
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MockResponse:
    """Mock response object matching SDK response structure."""

    content: str
    metadata: dict[str, Any] | None = None
    error: str | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {
                "timestamp": datetime.now().isoformat(),
                "model": "claude-3-opus-20240229",
                "usage": {"input_tokens": random.randint(10, 100), "output_tokens": random.randint(50, 500)},
            }


class MockSDKClient:
    """Mock implementation of ClaudeSDKClient for testing."""

    def __init__(
        self,
        api_key: str = "mock-key",
        fail_after: int | None = None,
        response_delay: float = 0.0,
        error_probability: float = 0.0,
        malformed_json_probability: float = 0.0,
    ):
        """Initialize mock client with configurable behavior.

        Args:
            api_key: Mock API key
            fail_after: Number of queries before failing
            response_delay: Delay before returning response
            error_probability: Probability of returning an error
            malformed_json_probability: Probability of returning malformed JSON
        """
        self.api_key = api_key
        self.fail_after = fail_after
        self.response_delay = response_delay
        self.error_probability = error_probability
        self.malformed_json_probability = malformed_json_probability
        self.query_count = 0
        self.conversation_history = []
        self.is_connected = False

    async def connect(self) -> None:
        """Mock connection to SDK."""
        await asyncio.sleep(0.01)  # Simulate connection time
        self.is_connected = True

    async def disconnect(self) -> None:
        """Mock disconnection from SDK."""
        self.is_connected = False

    async def query(
        self, prompt: str, system_prompt: str | None = None, max_tokens: int = 4096, temperature: float = 0.7, **kwargs
    ) -> MockResponse:
        """Mock query to Claude API.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional parameters

        Returns:
            MockResponse object with generated content
        """
        self.query_count += 1

        # Check if we should fail
        if self.fail_after and self.query_count >= self.fail_after:
            raise ConnectionError("Mock connection failed")

        # Add response delay
        if self.response_delay:
            await asyncio.sleep(self.response_delay)

        # Check for random error
        if random.random() < self.error_probability:
            return MockResponse(content="", error="Mock API error: Rate limit exceeded")

        # Store in conversation history
        self.conversation_history.append({"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()})

        # Generate mock response based on prompt
        response = self._generate_mock_response(prompt, system_prompt)

        # Check for malformed JSON
        if random.random() < self.malformed_json_probability:
            response = self._make_malformed_json(response)

        # Store response in history
        self.conversation_history.append(
            {"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()}
        )

        return MockResponse(content=response)

    async def stream_query(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Mock streaming query to Claude API.

        Args:
            prompt: User prompt
            **kwargs: Additional parameters

        Yields:
            Chunks of generated content
        """
        response = await self.query(prompt, **kwargs)

        # Simulate streaming by yielding words
        words = response.content.split()
        for word in words:
            await asyncio.sleep(0.01)  # Simulate streaming delay
            yield word + " "

    def _generate_mock_response(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a mock response based on the prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt

        Returns:
            Generated mock response
        """
        # Handle different types of prompts
        prompt_lower = prompt.lower()

        if "json" in prompt_lower or "data" in prompt_lower:
            # Return JSON response
            return json.dumps(
                {
                    "status": "success",
                    "data": {
                        "message": "Mock response for: " + prompt[:50],
                        "timestamp": datetime.now().isoformat(),
                        "items": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}],
                    },
                },
                indent=2,
            )

        if "code" in prompt_lower or "function" in prompt_lower:
            # Return code response
            return """```python
def mock_function(param):
    \"\"\"Mock function generated for testing.\"\"\"
    result = f"Processing: {param}"
    return {"status": "success", "result": result}
```"""

        if "analyze" in prompt_lower or "synthesize" in prompt_lower:
            # Return analytical response
            return f"""Based on the analysis of the provided content:

1. **Key Finding**: The prompt requests analysis of: {prompt[:30]}...
2. **Insight**: This appears to be a test scenario
3. **Recommendation**: Continue with the testing process

Summary: Mock analysis complete with test data."""

        if "error" in prompt_lower:
            # Trigger an error response
            return "Error: Mock error triggered by prompt"

        # Default response
        return f"Mock response to: {prompt[:100]}... This is a test response generated by MockSDKClient."

    def _make_malformed_json(self, response: str) -> str:
        """Make a response with malformed JSON.

        Args:
            response: Original response

        Returns:
            Response with malformed JSON
        """
        malformed_types = [
            # Markdown wrapped JSON
            f"```json\n{response}\n```\nHere's the JSON data you requested.",
            # Extra text before JSON
            f"Let me provide that data for you:\n\n{response}",
            # Invalid JSON syntax
            response.replace('"', "'"),  # Single quotes instead of double
            # Truncated JSON
            response[: len(response) // 2] + "...",
            # Extra commas
            response.replace("}", ",}"),
        ]

        return random.choice(malformed_types)

    def reset(self) -> None:
        """Reset the mock client state."""
        self.query_count = 0
        self.conversation_history = []
        self.is_connected = False

    def get_metrics(self) -> dict[str, Any]:
        """Get mock metrics for testing.

        Returns:
            Dictionary of metrics
        """
        return {
            "total_queries": self.query_count,
            "conversation_length": len(self.conversation_history),
            "is_connected": self.is_connected,
            "total_tokens": sum(random.randint(50, 500) for _ in range(self.query_count)),
        }


class MockSDKClientWithErrors(MockSDKClient):
    """Mock client that simulates various error conditions."""

    def __init__(self, error_sequence: list[str] | None = None, **kwargs):
        """Initialize with specific error sequence.

        Args:
            error_sequence: List of error types to trigger in order
            **kwargs: Additional parameters for base class
        """
        super().__init__(**kwargs)
        self.error_sequence = error_sequence or []
        self.error_index = 0

    async def query(self, prompt: str, **kwargs) -> MockResponse:
        """Query with controlled error behavior.

        Args:
            prompt: User prompt
            **kwargs: Additional parameters

        Returns:
            MockResponse or raises error
        """
        if self.error_index < len(self.error_sequence):
            error_type = self.error_sequence[self.error_index]
            self.error_index += 1

            if error_type == "timeout":
                raise TimeoutError("Mock timeout")
            if error_type == "connection":
                raise ConnectionError("Mock connection error")
            if error_type == "api":
                return MockResponse(content="", error="API Error: Invalid request")
            if error_type == "rate_limit":
                return MockResponse(content="", error="Rate limit exceeded")

        return await super().query(prompt, **kwargs)


def create_mock_client(**kwargs) -> MockSDKClient:
    """Factory function to create mock clients.

    Args:
        **kwargs: Parameters for MockSDKClient

    Returns:
        Configured MockSDKClient instance
    """
    return MockSDKClient(**kwargs)


def create_error_client(error_sequence: list[str], **kwargs) -> MockSDKClientWithErrors:
    """Factory function to create error-simulating clients.

    Args:
        error_sequence: Sequence of errors to simulate
        **kwargs: Additional parameters

    Returns:
        Configured MockSDKClientWithErrors instance
    """
    return MockSDKClientWithErrors(error_sequence, **kwargs)
