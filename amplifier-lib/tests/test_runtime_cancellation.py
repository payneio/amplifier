"""Tests for CancellationToken in runtime.py."""

from __future__ import annotations

from amplifier_lib.runtime import CancellationToken


class TestCancellationTokenInitialState:
    """Verify default state after construction."""

    def test_not_cancelled(self) -> None:
        assert CancellationToken().is_cancelled is False

    def test_not_immediate(self) -> None:
        assert CancellationToken().is_immediate is False


class TestCancellationTokenCancel:
    """Verify cancel() sets flags correctly."""

    def test_graceful_sets_cancelled(self) -> None:
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled is True

    def test_graceful_leaves_immediate_false(self) -> None:
        token = CancellationToken()
        token.cancel()
        assert token.is_immediate is False

    def test_immediate_sets_both_flags(self) -> None:
        token = CancellationToken()
        token.cancel(immediate=True)
        assert token.is_cancelled is True
        assert token.is_immediate is True

    def test_double_cancel_is_safe(self) -> None:
        token = CancellationToken()
        token.cancel()
        token.cancel()
        assert token.is_cancelled is True

    def test_graceful_then_immediate(self) -> None:
        """Mirrors the Ctrl+C, Ctrl+C sequence."""
        token = CancellationToken()
        token.cancel()
        assert token.is_immediate is False
        token.cancel(immediate=True)
        assert token.is_immediate is True


class TestCancellationTokenReset:
    """Verify reset() clears all flags for reuse across turns."""

    def test_reset_clears_cancelled(self) -> None:
        token = CancellationToken()
        token.cancel()
        token.reset()
        assert token.is_cancelled is False

    def test_reset_clears_immediate(self) -> None:
        token = CancellationToken()
        token.cancel(immediate=True)
        token.reset()
        assert token.is_immediate is False

    def test_cancel_reset_cancel_cycle(self) -> None:
        """Token can be reused across interactive turns."""
        token = CancellationToken()
        token.cancel(immediate=True)
        token.reset()
        token.cancel()
        assert token.is_cancelled is True
        assert token.is_immediate is False


class TestCancellationTokenStubs:
    """Legacy stubs must not raise."""

    def test_register_tool_start(self) -> None:
        CancellationToken().register_tool_start("id-1", "bash")

    def test_register_tool_complete(self) -> None:
        CancellationToken().register_tool_complete("id-1")

    def test_register_child(self) -> None:
        parent, child = CancellationToken(), CancellationToken()
        parent.register_child(child)

    def test_unregister_child(self) -> None:
        parent, child = CancellationToken(), CancellationToken()
        parent.unregister_child(child)


class TestCancellationTokenAPIContract:
    """Guard against phantom-API regressions.

    The sigint_handler bug was caused by calling methods that never existed.
    These tests make the public API explicit so refactors that change method
    names will break a test rather than silently diverge from callers.
    """

    def test_has_cancel(self) -> None:
        assert callable(getattr(CancellationToken, "cancel", None))

    def test_has_reset(self) -> None:
        assert callable(getattr(CancellationToken, "reset", None))

    def test_no_request_graceful(self) -> None:
        assert not hasattr(CancellationToken(), "request_graceful")

    def test_no_request_immediate(self) -> None:
        assert not hasattr(CancellationToken(), "request_immediate")

    def test_no_running_tool_names(self) -> None:
        assert not hasattr(CancellationToken(), "running_tool_names")
