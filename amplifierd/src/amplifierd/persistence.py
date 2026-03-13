"""Session persistence -- transcript and metadata hooks.

Registers hooks on tool:post and orchestrator:complete that write
transcript.jsonl and metadata.json incrementally during execution.

I/O functions (write_transcript, load_transcript, etc.) live in
amplifier_lib.session.persistence.  This module keeps only the hook
classes that depend on amplifier_core types.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from amplifier_lib.session.persistence import (
    load_metadata,
    load_transcript,
    write_metadata,
    write_transcript,
)

logger = logging.getLogger(__name__)

_PRIORITY = 900


class TranscriptSaveHook:
    """Persists transcript.jsonl incrementally during execution.

    Registered on tool:post (mid-turn durability) and
    orchestrator:complete (end-of-turn, catches no-tool turns).
    Debounces by message count.
    """

    def __init__(self, session: Any, session_dir: Path) -> None:
        self._session = session
        self._session_dir = session_dir
        self._last_count = 0

    async def __call__(self, event: str, data: dict[str, Any]) -> Any:
        from amplifier_core.models import HookResult

        try:
            # Workaround: tool:post fires before context update.
            # Yielding one tick lets the orchestrator add the result first.
            if event == "tool:post":
                await asyncio.sleep(0)

            context = self._session.coordinator.get("context")
            if not context or not hasattr(context, "get_messages"):
                return HookResult(action="continue")

            messages = await context.get_messages()
            count = len(messages)

            if count <= self._last_count:
                return HookResult(action="continue")

            await asyncio.to_thread(write_transcript, self._session_dir, list(messages))
            self._last_count = count

        except Exception:  # noqa: BLE001
            logger.warning("Transcript save failed", exc_info=True)

        return HookResult(action="continue")


class MetadataSaveHook:
    """Writes metadata.json on orchestrator:complete.

    Flushes initial metadata on first fire, then updates turn_count
    and last_updated on every subsequent turn.
    """

    def __init__(
        self,
        session: Any,
        session_dir: Path,
        initial_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._session = session
        self._session_dir = session_dir
        self._initial_metadata = initial_metadata

    async def __call__(self, event: str, data: dict[str, Any]) -> Any:
        from amplifier_core.models import HookResult

        try:
            context = self._session.coordinator.get("context")
            if not context or not hasattr(context, "get_messages"):
                return HookResult(action="continue")

            messages = await context.get_messages()
            turn_count = sum(1 for m in messages if isinstance(m, dict) and m.get("role") == "user")

            updates: dict[str, Any] = {
                "turn_count": turn_count,
                "last_updated": datetime.now(tz=UTC).isoformat(),
            }

            if self._initial_metadata is not None:
                updates = {**self._initial_metadata, **updates}
                self._initial_metadata = None

            write_metadata(self._session_dir, updates)

            # Bridge: emit prompt:complete so hooks-session-naming fires.
            # Some orchestrators (e.g. loop-streaming) only emit
            # orchestrator:complete but not prompt:complete.
            session_id = getattr(self._session, "session_id", None)
            if session_id:
                await self._session.coordinator.hooks.emit(
                    "prompt:complete",
                    {**data, "session_id": session_id},
                )
        except Exception:  # noqa: BLE001
            logger.warning("Metadata save failed", exc_info=True)

        return HookResult(action="continue")


def register_persistence_hooks(
    session: Any,
    session_dir: Path,
    initial_metadata: dict[str, Any] | None = None,
) -> None:
    """Register transcript and metadata persistence hooks on a session.

    Silently no-ops if hooks API is unavailable.
    """
    try:
        transcript_hook = TranscriptSaveHook(session, session_dir)
        metadata_hook = MetadataSaveHook(session, session_dir, initial_metadata)
        hooks = session.coordinator.hooks

        hooks.register(
            event="tool:post",
            handler=transcript_hook,
            priority=_PRIORITY,
            name="amplifierd-transcript:tool:post",
        )
        hooks.register(
            event="orchestrator:complete",
            handler=transcript_hook,
            priority=_PRIORITY,
            name="amplifierd-transcript:orchestrator:complete",
        )
        hooks.register(
            event="orchestrator:complete",
            handler=metadata_hook,
            priority=_PRIORITY,
            name="amplifierd-metadata:orchestrator:complete",
        )
        logger.debug("Persistence hooks registered -> %s", session_dir)
    except Exception:  # noqa: BLE001
        logger.debug("Could not register persistence hooks", exc_info=True)
