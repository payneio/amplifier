"""Approval request/response protocol types for human-in-the-loop gates."""

from dataclasses import dataclass, field


class ApprovalTimeoutError(Exception):
    """Raised when an approval request exceeds its timeout."""


@dataclass
class ApprovalRequest:
    """Request for human approval before executing a sensitive action."""

    tool_name: str
    action: str
    details: dict = field(default_factory=dict)
    risk_level: str = "medium"
    timeout: float | None = None

    def __post_init__(self) -> None:
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be greater than 0")


@dataclass
class ApprovalResponse:
    """Response to an approval request."""

    approved: bool
    reason: str | None = None
    remember: bool = False
