"""Hook registry with agent-specific emit semantics.

What's here and why:
- Action precedence: deny > ask_user > inject_context > modify > continue.
  This isn't generic pub/sub. Generic emitters process handlers linearly and
  return the last result. This one enforces a domain-specific precedence where
  security actions (deny, ask_user) always win over information-flow actions
  (inject_context) which always win over data mutation (modify).

- Multi-inject merging: When multiple hooks return inject_context on the same
  event, their injections are concatenated into a single context message. This
  prevents earlier hooks from being silently dropped — a real problem when you
  have a linter hook AND a todo-reminder hook both injecting on tool:post.

- Default fields (session_id, parent_id): Stamped on every event automatically.
  Together with the infrastructure-owned timestamp, forms the compound identity
  key (session_id, timestamp) for event uniqueness and ordering across the
  multi-agent session tree.

- CancelledError handling: asyncio.CancelledError is a BaseException (Python 3.9+).
  If a handler is cancelled, we log and continue so all handlers observe cleanup
  events like session:end. Generic emitters would let this propagate and skip
  remaining handlers.

What's NOT here:
- HookHandler dataclass with priority sorting — that's just sorted-list insertion,
  any event library does it. Included because the emit() logic depends on it,
  but it's not the novel part.
- list_handlers() — introspection utility, not novel.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import HookResult

logger = logging.getLogger(__name__)


@dataclass
class HookHandler:
    """Registered hook handler with priority. Not novel — just sorted insertion."""

    handler: Callable[[str, dict[str, Any]], Awaitable[HookResult]]
    priority: int = 0
    name: str | None = None

    def __lt__(self, other: "HookHandler") -> bool:
        return self.priority < other.priority


class HookRegistry:
    """Lifecycle hook registry with agent-specific emit semantics.

    The register/unregister part is standard. The novel part is emit():
    its action precedence, multi-inject merging, and infrastructure field
    stamping are specific to LLM agent orchestration.
    """

    def __init__(self):
        self._handlers: dict[str, list[HookHandler]] = defaultdict(list)
        self._defaults: dict[str, Any] = {}

    def register(
        self,
        event: str,
        handler: Callable[[str, dict[str, Any]], Awaitable[HookResult]],
        priority: int = 0,
        name: str | None = None,
    ) -> Callable[[], None]:
        """Register a handler. Returns an unregister function."""
        hook_handler = HookHandler(
            handler=handler, priority=priority, name=name or handler.__name__
        )
        self._handlers[event].append(hook_handler)
        self._handlers[event].sort()

        def unregister():
            if hook_handler in self._handlers[event]:
                self._handlers[event].remove(hook_handler)

        return unregister

    # Alias
    on = register

    def set_default_fields(self, **defaults):
        """Set fields merged into every emit() call (e.g. session_id, parent_id)."""
        self._defaults = defaults

    async def emit(self, event: str, data: dict[str, Any]) -> HookResult:
        """Emit an event with agent-specific action precedence.

        This is the non-trivial part. The semantics are:

        1. Merge default fields (session_id, parent_id) with event data
        2. Stamp infrastructure timestamp
        3. Execute handlers sequentially by priority
        4. Short-circuit on deny (security: nothing overrides a deny)
        5. Collect all inject_context results for merging
        6. Capture first ask_user (can't merge approval prompts)
        7. Chain modify actions (each handler sees previous handler's changes)
        8. Apply precedence: deny > ask_user > inject_context > modify > continue

        Why not just return the last handler's result?
        Because in an agent loop, a security hook saying "deny" must not be
        overridden by a later logging hook saying "continue". And multiple
        context injections must merge, not clobber.
        """
        handlers = self._handlers.get(event, [])

        if not handlers:
            return HookResult(action="continue", data=data)

        # Merge defaults + explicit data. Explicit wins.
        current_data = {**self._defaults, **(data or {})}
        # Infrastructure-owned timestamp for event identity.
        current_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        special_result = None
        inject_context_results: list[HookResult] = []

        for hook_handler in handlers:
            try:
                result = await hook_handler.handler(event, current_data)

                if not isinstance(result, HookResult):
                    continue

                # Deny short-circuits immediately (highest precedence)
                if result.action == "deny":
                    return result

                # Chain modify actions
                if result.action == "modify" and result.data is not None:
                    current_data = result.data

                # Collect inject_context for merging
                if result.action == "inject_context" and result.context_injection:
                    inject_context_results.append(result)

                # Capture first ask_user (can't merge approvals)
                if result.action == "ask_user" and special_result is None:
                    special_result = result

            except asyncio.CancelledError:
                # Don't let cancellation skip remaining handlers.
                # Critical for cleanup events like session:end.
                logger.error(
                    f"CancelledError in hook '{hook_handler.name}' for '{event}'"
                )
            except Exception as e:
                logger.error(f"Error in hook '{hook_handler.name}' for '{event}': {e}")

        # Merge multiple inject_context results
        if inject_context_results:
            merged = self._merge_inject_context(inject_context_results)
            # ask_user takes precedence over inject_context (security > info)
            if special_result is None:
                special_result = merged

        if special_result:
            return special_result

        return HookResult(action="continue", data=current_data)

    def _merge_inject_context(self, results: list[HookResult]) -> HookResult:
        """Merge multiple inject_context results into one.

        When a linter hook AND a todo-reminder hook both inject on tool:post,
        we concatenate rather than dropping one. Uses settings (role, ephemeral)
        from the first result.
        """
        if len(results) == 1:
            return results[0]

        combined = "\n\n".join(
            r.context_injection for r in results if r.context_injection
        )
        first = results[0]
        return HookResult(
            action="inject_context",
            context_injection=combined,
            context_injection_role=first.context_injection_role,
            ephemeral=first.ephemeral,
            suppress_output=first.suppress_output,
        )

    async def emit_and_collect(
        self, event: str, data: dict[str, Any], timeout: float = 1.0
    ) -> list[Any]:
        """Emit and collect result.data from all handlers (for decision reduction).

        Unlike emit() which enforces action precedence, this just aggregates.
        Used for decision events where multiple hooks propose candidates
        (e.g. tool resolution, agent selection).
        """
        handlers = self._handlers.get(event, [])
        if not handlers:
            return []

        responses = []
        for hook_handler in handlers:
            try:
                result = await asyncio.wait_for(
                    hook_handler.handler(event, data), timeout=timeout
                )
                if isinstance(result, HookResult) and result.data is not None:
                    responses.append(result.data)
            except TimeoutError:
                logger.warning(f"Handler '{hook_handler.name}' timed out")
            except asyncio.CancelledError:
                logger.error(f"CancelledError in '{hook_handler.name}' for '{event}'")
            except Exception as e:
                logger.error(f"Error in '{hook_handler.name}' for '{event}': {e}")

        return responses

    def list_handlers(self, event: str | None = None) -> dict[str, list[str]]:
        """List registered handler names, optionally filtered by event."""
        if event:
            handlers = self._handlers.get(event, [])
            return {event: [h.name for h in handlers if h.name is not None]}
        return {
            evt: [h.name for h in handlers if h.name is not None]
            for evt, handlers in self._handlers.items()
        }
