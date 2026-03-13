"""Core types for Amplifier — the ~5% that isn't reinventing Python.

Re-exports everything so consumers can use either:
    from amplifier_lib.core import HookResult, ToolResult, HookRegistry
    from amplifier_lib.core.models import HookResult
    from amplifier_lib.core.hooks import HookRegistry
"""

from .approval import ApprovalRequest, ApprovalResponse, ApprovalTimeoutError
from .hooks import HookRegistry
from .llm_errors import (
    AuthenticationError,
    ConfigurationError,
    ContentFilterError,
    ContextLengthError,
    InvalidToolCallError,
    LLMError,
    LLMTimeoutError,
    NetworkError,
    NotFoundError,
    ProviderUnavailableError,
    QuotaExceededError,
    RateLimitError,
    StreamError,
)
from .loader import ModuleInfo, ModuleLoader, ModuleValidationError
from .message_models import ChatRequest, Message
from .models import HookResult, ModelInfo, ToolResult
from .validation import (
    ContextValidator,
    HookValidator,
    OrchestratorValidator,
    ProviderValidator,
    ToolValidator,
    ValidationCheck,
    ValidationResult,
)

__all__ = [
    # models
    "HookResult",
    "ToolResult",
    "ModelInfo",
    # hooks
    "HookRegistry",
    # llm_errors
    "LLMError",
    "RateLimitError",
    "AuthenticationError",
    "ContextLengthError",
    "ContentFilterError",
    "ProviderUnavailableError",
    "LLMTimeoutError",
    "NotFoundError",
    "StreamError",
    "InvalidToolCallError",
    "ConfigurationError",
    "NetworkError",
    "QuotaExceededError",
    # approval
    "ApprovalRequest",
    "ApprovalResponse",
    "ApprovalTimeoutError",
    # message_models
    "Message",
    "ChatRequest",
    # loader
    "ModuleLoader",
    "ModuleValidationError",
    "ModuleInfo",
    # validation
    "ToolValidator",
    "HookValidator",
    "ContextValidator",
    "OrchestratorValidator",
    "ProviderValidator",
    "ValidationResult",
    "ValidationCheck",
]
