"""Module discovery and loading for Amplifier plugins."""

import importlib
import importlib.metadata
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class ModuleValidationError(Exception):
    """Raised when a module fails validation during load."""


@dataclass
class ModuleInfo:
    """Metadata for a discoverable Amplifier module."""

    name: str
    module_type: str = ""
    entry_point: str = ""
    source: str = ""
    version: str = ""
    description: str = ""


class ModuleLoader:
    """Discovers and loads Amplifier plugin modules.

    Uses importlib.metadata entry_points for discovery and
    importlib.import_module for loading. Tracks loaded modules
    for cleanup.
    """

    _ENTRY_POINT_GROUP = "amplifier.modules"

    def __init__(
        self,
        coordinator: Any = None,
        search_paths: list[str] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._search_paths: list[str] = search_paths or []
        self._loaded: dict[str, Callable] = {}

    async def discover(self) -> list[ModuleInfo]:
        """Discover available modules via entry points.

        Returns a list of ModuleInfo for every entry point registered
        under the 'amplifier.modules' group.
        """
        modules: list[ModuleInfo] = []

        try:
            eps = importlib.metadata.entry_points(group=self._ENTRY_POINT_GROUP)
        except Exception as exc:  # pragma: no cover
            logger.warning("Entry point discovery failed: %s", exc)
            return modules

        for ep in eps:
            # Entry point name convention: "<type>.<name>" or just "<name>"
            parts = ep.name.split(".", 1)
            module_type = parts[0] if len(parts) == 2 else ""
            name = parts[1] if len(parts) == 2 else parts[0]

            dist_version = ""
            try:
                if ep.dist is not None:
                    dist_version = ep.dist.version
            except Exception:
                pass

            modules.append(
                ModuleInfo(
                    name=name,
                    module_type=module_type,
                    entry_point=ep.value,
                    source="entry_point",
                    version=dist_version,
                )
            )

        return modules

    async def load(
        self,
        module_id: str,
        config: dict[str, Any] | None = None,
        source_hint: str | None = None,
        coordinator: Any = None,
    ) -> Callable:
        """Load and return a module callable by its dotted path.

        Args:
            module_id: Dotted import path, e.g. 'mypackage.tools:mount'.
            config: Optional configuration passed during initialisation.
            source_hint: Optional hint about the module source (unused,
                reserved for future routing logic).
            coordinator: Override the coordinator set at construction time.

        Returns:
            The loaded callable (typically a mount function).

        Raises:
            ModuleValidationError: If the module cannot be imported or the
                attribute is not found.
        """
        if module_id in self._loaded:
            return self._loaded[module_id]

        try:
            if ":" in module_id:
                module_path, attr = module_id.rsplit(":", 1)
            else:
                module_path, attr = module_id.rsplit(".", 1)

            mod = importlib.import_module(module_path)
            callable_obj = getattr(mod, attr)
        except (ImportError, AttributeError, ValueError) as exc:
            raise ModuleValidationError(
                f"Cannot load module '{module_id}': {exc}"
            ) from exc

        self._loaded[module_id] = callable_obj
        return callable_obj

    async def initialize(
        self,
        module: Callable,
        coordinator: Any = None,
    ) -> Callable | None:
        """Initialize a loaded module callable.

        If the module exposes an async ``initialize`` method it is called
        with the coordinator.  Returns the result (often the same callable,
        sometimes a configured instance).
        """
        coord = coordinator or self._coordinator
        init_fn = getattr(module, "initialize", None)
        if init_fn is None:
            return module

        try:
            result = init_fn(coordinator=coord)
            # Support both sync and async initializers
            if hasattr(result, "__await__"):
                result = await result
            return result
        except Exception as exc:
            logger.warning("Module initialization failed: %s", exc)
            return module

    def cleanup(self) -> None:
        """Release references to all loaded modules."""
        self._loaded.clear()
