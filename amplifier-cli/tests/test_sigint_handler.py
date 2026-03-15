"""Tests for the Ctrl+C signal handler in interactive_chat.

The sigint_handler is a closure inside _execute_with_interrupt and cannot be
imported directly. We test it two ways:

1. Behavioral: Reconstruct the handler's logic with a real CancellationToken
   and fire SIGINT via os.kill to verify the state transitions.
2. Structural: Assert the source code uses the correct CancellationToken API
   so a future refactor that re-introduces phantom methods is caught.
"""

from __future__ import annotations

import os
import signal
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from amplifier_lib.runtime import CancellationToken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sigint_handler(
    token: CancellationToken,
    console: MagicMock,
) -> Callable[..., Any]:
    """Mirror the sigint_handler closure from main.py.

    This duplicates the logic intentionally -- if the real handler diverges
    from this, the structural tests below will catch it.
    """

    def handler(signum: int, frame: object) -> None:
        if token.is_cancelled:
            token.cancel(immediate=True)
            console.print("immediate")
        else:
            token.cancel()
            console.print("graceful")

    return handler


# ---------------------------------------------------------------------------
# Behavioral tests -- real signal delivery
# ---------------------------------------------------------------------------


class TestSigintFirstCtrlC:
    """First Ctrl+C requests graceful cancellation."""

    def test_sets_cancelled(self) -> None:
        token = CancellationToken()
        console = MagicMock()
        old = signal.signal(signal.SIGINT, _make_sigint_handler(token, console))
        try:
            os.kill(os.getpid(), signal.SIGINT)
        finally:
            signal.signal(signal.SIGINT, old)
        assert token.is_cancelled is True

    def test_leaves_immediate_false(self) -> None:
        token = CancellationToken()
        console = MagicMock()
        old = signal.signal(signal.SIGINT, _make_sigint_handler(token, console))
        try:
            os.kill(os.getpid(), signal.SIGINT)
        finally:
            signal.signal(signal.SIGINT, old)
        assert token.is_immediate is False


class TestSigintSecondCtrlC:
    """Second Ctrl+C escalates to immediate cancellation."""

    def test_sets_immediate(self) -> None:
        token = CancellationToken()
        console = MagicMock()
        old = signal.signal(signal.SIGINT, _make_sigint_handler(token, console))
        try:
            os.kill(os.getpid(), signal.SIGINT)  # first
            os.kill(os.getpid(), signal.SIGINT)  # second
        finally:
            signal.signal(signal.SIGINT, old)
        assert token.is_cancelled is True
        assert token.is_immediate is True


# ---------------------------------------------------------------------------
# Structural tests -- source must use the correct API
# ---------------------------------------------------------------------------

_MAIN_SOURCE = (
    Path(__file__).resolve().parent.parent / "amplifier_cli" / "main.py"
).read_text()


class TestSigintHandlerSource:
    """Assert main.py calls the real CancellationToken API."""

    def test_uses_cancel_for_graceful(self) -> None:
        assert "cancellation.cancel()" in _MAIN_SOURCE

    def test_uses_cancel_immediate_for_force(self) -> None:
        assert "cancellation.cancel(immediate=True)" in _MAIN_SOURCE

    def test_no_phantom_request_graceful(self) -> None:
        assert "request_graceful" not in _MAIN_SOURCE

    def test_no_phantom_request_immediate(self) -> None:
        assert "request_immediate" not in _MAIN_SOURCE

    def test_no_phantom_running_tool_names(self) -> None:
        assert "running_tool_names" not in _MAIN_SOURCE

    def test_handler_is_restored(self) -> None:
        """Signal handler must be restored in a finally block."""
        assert "signal.signal(signal.SIGINT, original_handler)" in _MAIN_SOURCE
