"""Session persistence I/O -- transcript and metadata read/write.

Pure I/O functions for reading and writing session transcript.jsonl and
metadata.json files. Hook classes that wire these into the session lifecycle
stay in the apps (they depend on amplifier_core types).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_EXCLUDED_ROLES = frozenset({"system", "developer"})
_TRANSCRIPT_FILENAME = "transcript.jsonl"
_METADATA_FILENAME = "metadata.json"

# Resolve sanitize_message once at import time.
try:
    from amplifier_lib.serialization import sanitize_message as _sanitize_message
except ImportError:
    _sanitize_message = None  # type: ignore[assignment]

# Resolve write_with_backup once at import time.
try:
    from amplifier_lib.io.files import write_with_backup as _write_with_backup
except ImportError:
    _write_with_backup = None  # type: ignore[assignment]


def _sanitize(msg: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a message for JSON persistence.

    Preserves content:null on tool-call messages (providers need it).
    """
    had_content_null = "content" in msg and msg["content"] is None
    sanitized = _sanitize_message(msg) if _sanitize_message is not None else msg
    if had_content_null and "content" not in sanitized:
        sanitized["content"] = None
    return sanitized


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using write_with_backup or fallback."""
    if _write_with_backup is not None:
        _write_with_backup(path, content)
    else:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)


def write_transcript(session_dir: Path, messages: list[dict[str, Any]]) -> None:
    """Write messages to transcript.jsonl, filtering system/developer roles.

    Full rewrite (not append) -- context compaction can change earlier messages.
    """
    lines: list[str] = []
    for msg in messages:
        try:
            msg_dict = (
                msg
                if isinstance(msg, dict)
                else getattr(msg, "model_dump", lambda _m=msg: _m)()
            )
            if msg_dict.get("role") in _EXCLUDED_ROLES:
                continue
            sanitized = _sanitize(msg_dict)
            lines.append(json.dumps(sanitized, ensure_ascii=False))
        except Exception:  # noqa: BLE001
            logger.debug("Skipping unserializable message", exc_info=True)

    content = "\n".join(lines) + "\n" if lines else ""
    session_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(session_dir / _TRANSCRIPT_FILENAME, content)


def write_metadata(session_dir: Path, metadata: dict[str, Any]) -> None:
    """Write metadata dict to metadata.json, merging with existing content."""
    if not session_dir.exists():
        return
    metadata_path = session_dir / _METADATA_FILENAME

    existing: dict[str, Any] = {}
    if metadata_path.exists():
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    merged = {**existing, **metadata}
    content = json.dumps(merged, indent=2, ensure_ascii=False)
    _atomic_write(metadata_path, content)


def load_transcript(session_dir: Path) -> list[dict[str, Any]]:
    """Load messages from transcript.jsonl in a session directory.

    Returns a list of message dicts. Raises FileNotFoundError
    if the transcript file does not exist.
    """
    transcript_path = session_dir / _TRANSCRIPT_FILENAME
    if not transcript_path.exists():
        raise FileNotFoundError(f"No transcript at {transcript_path}")
    messages: list[dict[str, Any]] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Skipping unreadable transcript line")
    return messages


def load_metadata(session_dir: Path) -> dict[str, Any]:
    """Load metadata.json from a session directory.

    Returns an empty dict if the file doesn't exist or is unreadable.
    """
    metadata_path = session_dir / _METADATA_FILENAME
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
