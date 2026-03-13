"""The non-trivial data models from amplifier-core.

What's here and why:
- _sanitize_for_llm: Solves a real operational bug where tool output containing
  control characters (\\x00-\\x1f) or lone UTF-16 surrogates crashes LLM APIs
  (Anthropic returns "Internal server error"). This is domain-specific knowledge
  that Python's stdlib doesn't give you.

- ToolResult.get_serialized_output: JSON serialization + sanitization for LLM
  consumption. The model_post_init auto-populates output from error when tool
  authors forget — defense-in-depth for a common module author mistake.

- HookResult: The genuinely novel part of amplifier-core. This isn't a generic
  pub/sub result — it's a domain-specific protocol for hooks to participate in
  an LLM agent's cognitive loop. No existing Python library expresses:
  "inject text into the LLM's context as an ephemeral system message, merge
  multiple injections from different hooks, show a different message to the
  user, and request approval with timeout and safe defaults."

  Action precedence (deny > ask_user > inject_context > modify > continue)
  is enforced by HookRegistry.emit(), not here — this is just the data model.

What's NOT here:
- ToolCall, ProviderResponse, AgentResult, ModuleInfo, SessionStatus — these
  are plain Pydantic models with no logic. Any app would define its own.
"""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field


def _sanitize_for_llm(text: str) -> str:
    """Sanitize text for safe transmission to LLM APIs.

    Removes control characters that cause API errors while preserving
    common whitespace (tab, newline, carriage return). Also strips
    lone UTF-16 surrogates (invalid in JSON).

    Why this exists: Anthropic returns "Internal server error" when tool
    results contain \\x00-\\x1f control chars from source code or LSP
    responses. This was a real production bug, not a hypothetical.
    """
    # Remove control chars except tab (\\x09), newline (\\x0a), CR (\\x0d)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Remove lone UTF-16 surrogates (invalid in JSON, cause API errors)
    sanitized = re.sub(r"[\ud800-\udfff]", "", sanitized)
    return sanitized


class ToolResult(BaseModel):
    """Result from tool execution, with LLM-safe serialization."""

    success: bool = Field(default=True)
    output: Any | None = Field(default=None)
    error: dict[str, Any] | None = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        """Auto-populate output from error when tools forget to set it.

        Many tools return ToolResult(success=False, error={"message": "..."})
        without setting output. The output field is the primary channel the
        AI reads — without it, error details are invisible to the agent.
        """
        if not self.success and self.output is None and self.error:
            message = self.error.get("message")
            if message:
                self.output = message

    def get_serialized_output(self) -> str:
        """Serialize output for LLM context, with sanitization.

        Returns JSON for dict/list (proper for LLM parsing), string otherwise.
        Sanitizes to remove control characters that crash LLM APIs.
        """
        if self.output is not None:
            if isinstance(self.output, (dict, list)):
                result = json.dumps(self.output)
            else:
                result = str(self.output)
            return _sanitize_for_llm(result)

        if not self.success:
            msg = self.error.get("message", "Unknown error") if self.error else "Failed"
            return f"Error: {msg}"

        return "Success"

    def __str__(self) -> str:
        if self.success:
            return str(self.output) if self.output else "Success"
        if self.error:
            return f"Error: {self.error.get('message', 'Unknown error')}"
        return "Failed"


class HookResult(BaseModel):
    """Result from hook execution — the novel domain model.

    This is NOT a generic event result. It's a protocol for hooks to
    participate in an LLM agent's cognitive loop:

    - inject_context: Add text to the agent's conversation context
      (enables automated feedback loops, e.g. linter injects errors
      that the agent sees and fixes within the same turn)
    - ask_user: Request approval with timeout and safe defaults
      (enables dynamic permission logic beyond static tool policies)
    - ephemeral: Injection is temporary (only for current LLM call,
      not stored in history — for transient state like todo reminders)
    - append_to_last_tool_result: Attach injection to the tool result
      instead of creating a new message (contextual reminders)
    - suppress_output / user_message: Control what the user sees
      vs what the agent sees (separate channels)

    Action precedence (enforced by HookRegistry.emit()):
      deny > ask_user > inject_context > modify > continue
    """

    # --- Core action ---
    action: Literal["continue", "deny", "modify", "inject_context", "ask_user"] = Field(
        default="continue",
    )

    # --- Existing fields (generic pub/sub would have these) ---
    data: dict[str, Any] | None = Field(default=None)
    reason: str | None = Field(default=None)

    # --- Context injection (novel) ---
    context_injection: str | None = Field(default=None)
    context_injection_role: Literal["system", "user", "assistant"] = Field(
        default="system",
    )
    ephemeral: bool = Field(default=False)
    append_to_last_tool_result: bool = Field(default=False)

    # --- Approval gates (novel) ---
    approval_prompt: str | None = Field(default=None)
    approval_options: list[str] | None = Field(default=None)
    approval_timeout: float = Field(default=300.0)
    approval_default: Literal["allow", "deny"] = Field(default="deny")

    # --- Output control (novel) ---
    suppress_output: bool = Field(default=False)
    user_message: str | None = Field(default=None)
    user_message_level: Literal["info", "warning", "error"] = Field(default="info")
    user_message_source: str | None = Field(default=None)


class ModelInfo(BaseModel):
    """Model metadata for provider models."""

    id: str
    display_name: str = ""
    context_window: int = 0
    max_output_tokens: int = 0
    capabilities: list[str] = Field(default_factory=list)
    defaults: dict[str, Any] = Field(default_factory=dict)
