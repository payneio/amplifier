"""Core types for Amplifier — the ~5% that isn't reinventing Python.

Re-exports everything so consumers can use either:
    from amplifier_foundation.core import HookResult, ToolResult, HookRegistry
    from amplifier_foundation.core.models import HookResult
    from amplifier_foundation.core.hooks import HookRegistry
"""

from .hooks import HookRegistry
from .models import HookResult, ToolResult

__all__ = [
    "HookRegistry",
    "HookResult",
    "ToolResult",
]
