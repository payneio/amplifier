"""Message and request models for LLM chat interactions."""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class TextBlock:
    """Plain text content block."""

    text: str
    type: str = "text"


@dataclass
class ThinkingBlock:
    """Model thinking/scratchpad block."""

    thinking: str
    type: str = "thinking"


@dataclass
class RedactedThinkingBlock:
    """Redacted thinking block (opaque to consumers)."""

    data: str
    type: str = "redacted_thinking"


@dataclass
class ToolCallBlock:
    """Tool invocation block."""

    tool_use_id: str
    name: str
    input: dict = field(default_factory=dict)
    type: str = "tool_use"


@dataclass
class ToolResultBlock:
    """Result returned from a tool call."""

    tool_use_id: str
    content: Any = None
    is_error: bool = False
    type: str = "tool_result"


@dataclass
class ImageBlock:
    """Image content block."""

    source: dict = field(default_factory=dict)
    type: str = "image"


@dataclass
class ReasoningBlock:
    """Extended reasoning block."""

    reasoning: str
    type: str = "reasoning"


class Message(BaseModel):
    """A single message in a chat conversation."""

    model_config = ConfigDict(extra="allow")

    role: Literal["system", "developer", "user", "assistant", "function", "tool"]
    content: str | list[Any]
    name: str | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)
    metadata: dict | None = Field(default=None)


class ChatRequest(BaseModel):
    """Request payload for a chat completion."""

    messages: list[Message]
    model: str | None = Field(default=None)
    temperature: float | None = Field(default=None)
    max_tokens: int | None = Field(default=None)
    tools: list | None = Field(default=None)
    tool_choice: Any | None = Field(default=None)
