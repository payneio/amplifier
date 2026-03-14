"""Session runtime — AmplifierSession, Coordinator, and module loading.

Uses core types from amplifier_lib.core:
  - amplifier_lib.core.models.HookResult (action protocol)
  - amplifier_lib.core.hooks.HookRegistry (emit with action precedence)

Everything else is plain Python: a dict-with-methods coordinator, importlib-based
module loading, and a thin session lifecycle wrapper.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.metadata
import inspect
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from amplifier_lib.core.hooks import HookRegistry
from amplifier_lib.core.models import HookResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cancellation token — trivial flag object
# ---------------------------------------------------------------------------


@dataclass
class CancellationToken:
    is_cancelled: bool = False
    is_immediate: bool = False

    def cancel(self, immediate: bool = False) -> None:
        self.is_cancelled = True
        self.is_immediate = immediate

    def reset(self) -> None:
        """Reset flags so the token can be reused across interactive turns."""
        self.is_cancelled = False
        self.is_immediate = False

    # -- Legacy API stubs (unused, kept for module compatibility) --

    def register_tool_start(self, tool_call_id: str, tool_name: str) -> None:
        """No-op stub: reserved for future graceful cancellation tracking."""

    def register_tool_complete(self, tool_call_id: str) -> None:
        """No-op stub: reserved for future graceful cancellation tracking."""

    def register_child(self, child: "CancellationToken") -> None:
        """No-op stub: reserved for future child session cancellation propagation."""

    def unregister_child(self, child: "CancellationToken") -> None:
        """No-op stub: reserved for future child session cancellation propagation."""


# ---------------------------------------------------------------------------
# Coordinator — the "dict with methods" that modules mount into
# ---------------------------------------------------------------------------


class Coordinator:
    """Module registry with mount points, capabilities, and hooks.

    This is the object passed to every module's ``mount(coordinator, config)``
    function. Modules use it to register themselves and discover each other.
    """

    def __init__(
        self,
        session: Any = None,
        approval_system: Any = None,
        display_system: Any = None,
    ):
        self.mount_points: dict[str, Any] = {
            "orchestrator": None,
            "providers": {},
            "tools": {},
            "context": None,
            "hooks": HookRegistry(),
            # Extension slots — modules can mount arbitrary named slots
        }
        self.session = session
        self.approval_system = approval_system
        self.display_system = display_system
        self.cancellation = CancellationToken()
        self.loader: Any = None
        self.config: dict[str, Any] = {}

        # Capability store (arbitrary key-value for inter-module communication)
        self._capabilities: dict[str, Any] = {}
        self._cleanup_fns: list[Any] = []

        # Injection budget tracking
        self.injection_size_limit: int | None = None
        self.injection_budget_per_turn: int | None = None
        self._current_turn_injections: int = 0

    @property
    def session_id(self) -> str | None:
        """Session ID (delegated to the owning AmplifierSession)."""
        return getattr(self.session, "session_id", None)

    @property
    def hooks(self) -> HookRegistry:
        return self.mount_points["hooks"]

    async def mount(
        self, mount_point: str, module: Any, name: str | None = None
    ) -> None:
        if mount_point not in self.mount_points:
            # Extension slot — create it
            self.mount_points[mount_point] = module
            return

        value = self.mount_points[mount_point]

        if isinstance(value, dict):
            # Multi-module slot (providers, tools)
            if name is None:
                name = getattr(module, "name", None)
                if name is None:
                    raise ValueError(
                        f"Name required for multi-module slot '{mount_point}'"
                    )
            value[name] = module
        else:
            # Single-module slot (orchestrator, context) or extension
            self.mount_points[mount_point] = module

    async def unmount(self, mount_point: str, name: str | None = None) -> None:
        if mount_point not in self.mount_points:
            return
        value = self.mount_points[mount_point]
        if isinstance(value, dict) and name:
            value.pop(name, None)
        else:
            self.mount_points[mount_point] = None

    def get(self, mount_point: str, name: str | None = None) -> Any:
        if mount_point not in self.mount_points:
            return None
        value = self.mount_points[mount_point]
        if isinstance(value, dict):
            return value.get(name) if name else value
        return value

    def register_contributor(self, channel: str, name: str, callback: Any) -> None:
        """Register a contributor callback for a named channel.

        Calls the callback immediately and extends the channel's current list.
        Equivalent to register_capability(channel, value) for static values.
        """
        current: list[Any] = list(self._capabilities.get(channel) or [])
        if callable(callback):
            try:
                new_items = callback()
                if isinstance(new_items, (list, tuple)):
                    current.extend(new_items)
            except Exception as e:
                logger.debug(
                    f"register_contributor callback failed for channel "
                    f"'{channel}' (contributor '{name}'): {e}"
                )
        elif isinstance(callback, (list, tuple)):
            current.extend(callback)
        self._capabilities[channel] = current

    def register_capability(self, name: str, value: Any) -> None:
        self._capabilities[name] = value

    def get_capability(self, name: str, default: Any = None) -> Any:
        return self._capabilities.get(name, default)

    def register_cleanup(self, cleanup_fn: Any) -> None:
        self._cleanup_fns.append(cleanup_fn)

    async def cleanup(self) -> None:
        first_fatal = None
        for fn in reversed(self._cleanup_fns):
            try:
                if callable(fn):
                    if inspect.iscoroutinefunction(fn):
                        await fn()
                    else:
                        result = fn()
                        if inspect.iscoroutine(result):
                            await result
            except BaseException as e:
                logger.error(f"Error during cleanup: {e}")
                if first_fatal is None and not isinstance(e, Exception):
                    first_fatal = e
        if first_fatal is not None:
            raise first_fatal

    async def process_hook_result(
        self, result: HookResult, event: str, hook_name: str = "unknown"
    ) -> HookResult:
        """Route hook result actions to appropriate subsystems."""
        # Context injection
        if result.action == "inject_context" and result.context_injection:
            content = result.context_injection
            if not result.ephemeral:
                context = self.mount_points.get("context")
                if context and hasattr(context, "add_message"):
                    await context.add_message(
                        {
                            "role": result.context_injection_role,
                            "content": content,
                            "metadata": {
                                "source": "hook",
                                "hook_name": hook_name,
                                "event": event,
                                "timestamp": datetime.now().isoformat(),
                            },
                        }
                    )

        # Approval request
        if result.action == "ask_user":
            if self.approval_system is None:
                return HookResult(action="deny", reason="No approval system available")
            try:
                decision = await self.approval_system.request_approval(
                    prompt=result.approval_prompt or "Allow this operation?",
                    options=result.approval_options or ["Allow", "Deny"],
                    timeout=result.approval_timeout,
                    default=result.approval_default,
                )
                if decision == "Deny":
                    return HookResult(
                        action="deny", reason=f"User denied: {result.approval_prompt}"
                    )
                return HookResult(action="continue")
            except Exception:
                if result.approval_default == "deny":
                    return HookResult(
                        action="deny", reason="Approval timeout — denied by default"
                    )
                return HookResult(action="continue")

        # User message
        if result.user_message and self.display_system:
            source = getattr(result, "user_message_source", None) or hook_name
            self.display_system.show_message(
                message=result.user_message,
                level=result.user_message_level,
                source=f"hook:{source}",
            )

        return result


# ---------------------------------------------------------------------------
# Module loading — importlib.metadata.entry_points + importlib.import_module
# ---------------------------------------------------------------------------


def _load_entry_point(module_id: str) -> Any | None:
    """Find mount function via entry points."""
    try:
        for ep in importlib.metadata.entry_points(group="amplifier.modules"):
            if ep.name == module_id:
                return ep.load()
    except Exception as e:
        logger.debug(f"Entry point lookup failed for '{module_id}': {e}")
    return None


def _load_filesystem(module_id: str) -> Any | None:
    """Find mount function via importlib.import_module."""
    try:
        module_name = f"amplifier_module_{module_id.replace('-', '_')}"
        module = importlib.import_module(module_name)
        if hasattr(module, "mount"):
            return module.mount
    except Exception as e:
        logger.debug(f"Filesystem import failed for '{module_id}': {e}")
    return None


async def _load_module(
    module_id: str,
    config: dict[str, Any],
    coordinator: Coordinator,
    source_hint: str | dict | None = None,
) -> Any:
    """Load a module and return its mount function (with config bound).

    Resolution order:
    1. Source resolver (if mounted) — handles git, local, package sources
    2. Entry points — installed packages
    3. importlib.import_module — filesystem discovery
    """
    raw_fn = None

    # Try source resolver first (foundation mounts BundleModuleResolver here)
    source_resolver = None
    with contextlib.suppress(Exception):
        source_resolver = coordinator.get("module-source-resolver")

    if source_resolver is not None:
        try:
            if hasattr(source_resolver, "async_resolve"):
                source = await source_resolver.async_resolve(
                    module_id, source_hint=source_hint, profile_hint=source_hint
                )
            else:
                source = source_resolver.resolve(
                    module_id, source_hint=source_hint, profile_hint=source_hint
                )
            module_path = source.resolve()
            path_str = str(module_path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
        except Exception as e:
            logger.debug(f"Source resolution failed for '{module_id}': {e}")

    # Try entry points → filesystem
    raw_fn = _load_entry_point(module_id) or _load_filesystem(module_id)

    if raw_fn is None:
        raise ValueError(f"Module '{module_id}' not found")

    logger.info(f"[module:mount] {module_id}")

    async def mount_with_config(coord: Coordinator, fn=raw_fn) -> Any:
        return await fn(coord, config)

    return mount_with_config


# ---------------------------------------------------------------------------
# Session — the lifecycle wrapper
# ---------------------------------------------------------------------------


class AmplifierSession:
    """Session lifecycle: loads modules, calls the orchestrator, manages cleanup.
    """

    def __init__(
        self,
        config: dict[str, Any],
        session_id: str | None = None,
        parent_id: str | None = None,
        approval_system: Any = None,
        display_system: Any = None,
        is_resumed: bool = False,
    ):
        if not config:
            raise ValueError("Configuration is required")

        self._is_resumed = is_resumed
        self.session_id = session_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.config = config
        self._initialized = False
        self._added_paths: list[str] = []

        self.coordinator = Coordinator(
            session=self,
            approval_system=approval_system,
            display_system=display_system,
        )
        self.coordinator.config = config

        # Propagate session/parent IDs to all hook events
        self.coordinator.hooks.set_default_fields(
            session_id=self.session_id, parent_id=self.parent_id
        )

    async def initialize(self) -> None:
        """Load and mount all configured modules."""
        if self._initialized:
            return

        coord = self.coordinator

        # --- Orchestrator (required) ---
        orch_spec = self.config.get("session", {}).get("orchestrator", "loop-basic")
        if isinstance(orch_spec, dict):
            orch_id = orch_spec.get("module", "loop-basic")
            orch_source = orch_spec.get("source")
            orch_config = orch_spec.get("config", {})
        else:
            orch_id = orch_spec
            orch_source = self.config.get("session", {}).get("orchestrator_source")
            orch_config = self.config.get("orchestrator", {}).get("config", {})

        try:
            mount_fn = await _load_module(
                orch_id, orch_config, coord, source_hint=orch_source
            )
            cleanup = await mount_fn(coord)
            if cleanup:
                coord.register_cleanup(cleanup)
        except Exception as e:
            raise RuntimeError(f"Cannot initialize without orchestrator: {e}") from e

        # --- Context manager (required) ---
        ctx_spec = self.config.get("session", {}).get("context", "context-simple")
        if isinstance(ctx_spec, dict):
            ctx_id = ctx_spec.get("module", "context-simple")
            ctx_source = ctx_spec.get("source")
            ctx_config = ctx_spec.get("config", {})
        else:
            ctx_id = ctx_spec
            ctx_source = self.config.get("session", {}).get("context_source")
            ctx_config = self.config.get("context", {}).get("config", {})

        try:
            mount_fn = await _load_module(
                ctx_id, ctx_config, coord, source_hint=ctx_source
            )
            cleanup = await mount_fn(coord)
            if cleanup:
                coord.register_cleanup(cleanup)
        except Exception as e:
            raise RuntimeError(f"Cannot initialize without context manager: {e}") from e

        # --- Providers ---
        # Multi-instance validation
        module_counts: dict[str, int] = {}
        no_id_counts: dict[str, int] = {}
        for pc in self.config.get("providers", []):
            mid = pc.get("module", "")
            if mid:
                module_counts[mid] = module_counts.get(mid, 0) + 1
                if not pc.get("instance_id"):
                    no_id_counts[mid] = no_id_counts.get(mid, 0) + 1
        for mid, count in no_id_counts.items():
            if module_counts.get(mid, 0) > 1 and count > 1:
                raise ValueError(
                    f"Multi-instance providers require explicit 'instance_id'. "
                    f"Found {count} entries for '{mid}' without instance_id."
                )

        for pc in self.config.get("providers", []):
            mid = pc.get("module")
            if not mid:
                continue
            instance_id = pc.get("instance_id")
            try:
                # Snapshot existing provider before mount (for multi-instance remap)
                existing = None
                if instance_id:
                    default_name = (
                        mid.removeprefix("provider-")
                        if mid.startswith("provider-")
                        else mid
                    )
                    existing = (coord.get("providers") or {}).get(default_name)

                mount_fn = await _load_module(
                    mid, pc.get("config", {}), coord, source_hint=pc.get("source")
                )
                cleanup = await mount_fn(coord)
                if cleanup:
                    coord.register_cleanup(cleanup)

                # Multi-instance remapping
                if instance_id:
                    default_name = (
                        mid.removeprefix("provider-")
                        if mid.startswith("provider-")
                        else mid
                    )
                    providers = coord.get("providers") or {}
                    if default_name in providers and default_name != instance_id:
                        new_instance = providers[default_name]
                        await coord.mount("providers", new_instance, name=instance_id)
                        if existing is not None and existing is not new_instance:
                            await coord.mount("providers", existing, name=default_name)
                        else:
                            await coord.unmount("providers", name=default_name)
            except Exception as e:
                logger.warning(f"Failed to load provider '{mid}': {e}", exc_info=True)

        # --- Tools ---
        for tc in self.config.get("tools", []):
            mid = tc.get("module")
            if not mid:
                continue
            try:
                mount_fn = await _load_module(
                    mid, tc.get("config", {}), coord, source_hint=tc.get("source")
                )
                cleanup = await mount_fn(coord)
                if cleanup:
                    coord.register_cleanup(cleanup)
            except Exception as e:
                logger.warning(f"Failed to load tool '{mid}': {e}", exc_info=True)

        # --- Hooks ---
        for hc in self.config.get("hooks", []):
            mid = hc.get("module")
            if not mid:
                continue
            try:
                mount_fn = await _load_module(
                    mid, hc.get("config", {}), coord, source_hint=hc.get("source")
                )
                cleanup = await mount_fn(coord)
                if cleanup:
                    coord.register_cleanup(cleanup)
            except Exception as e:
                logger.warning(f"Failed to load hook '{mid}': {e}", exc_info=True)

        # Emit session:fork if child session
        if self.parent_id:
            await coord.hooks.emit(
                "session:fork",
                {
                    "parent": self.parent_id,
                    "session_id": self.session_id,
                },
            )

        self._initialized = True
        logger.info(f"Session {self.session_id} initialized")

    async def execute(self, prompt: str) -> str:
        """Execute a prompt via the mounted orchestrator."""
        if not self._initialized:
            await self.initialize()

        coord = self.coordinator

        # Emit session lifecycle event
        event = "session:resume" if self._is_resumed else "session:start"
        await coord.hooks.emit(
            event,
            {
                "session_id": self.session_id,
                "parent_id": self.parent_id,
            },
        )

        orchestrator = coord.get("orchestrator")
        if not orchestrator:
            raise RuntimeError("No orchestrator module mounted")
        context = coord.get("context")
        if not context:
            raise RuntimeError("No context manager mounted")
        providers = coord.get("providers")
        if not providers:
            raise RuntimeError("No providers mounted")
        tools = coord.get("tools") or {}
        hooks = coord.get("hooks")

        try:
            result = await orchestrator.execute(
                prompt=prompt,
                context=context,
                providers=providers,
                tools=tools,
                hooks=hooks,
                coordinator=coord,
            )

            if coord.cancellation.is_cancelled:
                await coord.hooks.emit(
                    "cancel:completed",
                    {
                        "was_immediate": coord.cancellation.is_immediate,
                    },
                )
            return result

        except BaseException as e:
            if coord.cancellation.is_cancelled:
                await coord.hooks.emit(
                    "cancel:completed",
                    {
                        "was_immediate": coord.cancellation.is_immediate,
                        "error": str(e),
                    },
                )
                raise
            logger.error(f"Execution failed: {e}")
            raise

    async def cleanup(self) -> None:
        """Emit session:end and run all module cleanup functions."""
        try:
            if self._initialized:
                with contextlib.suppress(Exception):
                    await self.coordinator.hooks.emit(
                        "session:end",
                        {
                            "session_id": self.session_id,
                        },
                    )
            await self.coordinator.cleanup()
        finally:
            # Remove sys.path additions
            for p in reversed(self._added_paths):
                with contextlib.suppress(ValueError):
                    sys.path.remove(p)
            self._added_paths.clear()

    async def __aenter__(self) -> AmplifierSession:
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.cleanup()
