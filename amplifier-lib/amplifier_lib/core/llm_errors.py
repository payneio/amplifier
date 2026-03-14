"""LLM error hierarchy for provider-agnostic error handling."""


class LLMError(Exception):
    """Base class for all LLM provider errors."""

    def __init__(
        self,
        message: str = "",
        *,
        provider: str = "",
        model: str = "",
        status_code: int | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
        delay_multiplier: float = 1.0,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after
        self.delay_multiplier = delay_multiplier


class RateLimitError(LLMError):
    """Request rate limit exceeded. Retryable by default."""

    def __init__(self, message: str = "", **kwargs) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class AuthenticationError(LLMError):
    """Invalid or missing API credentials."""


class AccessDeniedError(AuthenticationError):
    """Credentials valid but access to the requested resource is denied."""


class ContextLengthError(LLMError):
    """Prompt exceeds the model's context window."""


class ContentFilterError(LLMError):
    """Request blocked by provider content policy."""


class ProviderUnavailableError(LLMError):
    """Provider service is unavailable or returned a server error."""


class LLMTimeoutError(LLMError):
    """Request to the provider timed out."""


class NotFoundError(LLMError):
    """Requested model or resource was not found."""


class StreamError(LLMError):
    """Error occurred during streaming response."""


class InvalidToolCallError(LLMError):
    """Provider returned a malformed or invalid tool call."""

    def __init__(
        self,
        message: str = "",
        *,
        tool_name: str | None = None,
        raw_arguments: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        self.raw_arguments = raw_arguments


class InvalidRequestError(LLMError):
    """Request was malformed or invalid."""


class AbortError(LLMError):
    """Request was aborted by the client or policy."""


class ConfigurationError(LLMError):
    """Invalid client or provider configuration."""


class NetworkError(LLMError):
    """Network-level failure reaching the provider."""


class QuotaExceededError(LLMError):
    """Account quota or spending limit exceeded."""
