"""SessionManager - Manage session persistence and resume

This helper uses the SDK client through composition to manage
persistent sessions that can be saved and resumed.
"""

import json
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Session:
    """Represents a persistent session"""

    session_id: str
    name: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any]
    data: dict[str, Any]


class SessionManager:
    """Manage session persistence and resume.

    Uses the SDK client through composition to create, save, and
    restore sessions for long-running or resumable workflows.
    """

    def __init__(self, client: Any, session_dir: Path | str | None = None):
        """Initialize with an SDK client.

        Args:
            client: Initialized ClaudeSDKClient instance
            session_dir: Directory to store sessions (default: ./sessions)
        """
        self.client = client
        self.session_dir = Path(session_dir) if session_dir else Path("sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.current_session: Session | None = None
        self.session_history: list[dict[str, Any]] = []

    def create_session(self, name: str, metadata: dict[str, Any] | None = None) -> Session:
        """Create a new named session.

        Args:
            name: Human-readable session name
            metadata: Optional metadata for the session

        Returns:
            Created Session object
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        session = Session(
            session_id=session_id, name=name, created_at=now, updated_at=now, metadata=metadata or {}, data={}
        )

        self.current_session = session
        self._add_to_history("created", session_id, name)

        # Auto-save on creation
        self.save_session()

        return session

    def load_session(self, session_id: str) -> Session:
        """Load an existing session.

        Args:
            session_id: ID of session to load

        Returns:
            Loaded Session object

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        session_file = self.session_dir / f"{session_id}.json"

        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        session = Session(**data)
        self.current_session = session
        self._add_to_history("loaded", session_id, session.name)

        return session

    def save_session(self) -> None:
        """Save current session to disk.

        Raises:
            ValueError: If no active session
        """
        if not self.current_session:
            raise ValueError("No active session to save")

        self.current_session.updated_at = datetime.now().isoformat()

        session_file = self.session_dir / f"{self.current_session.session_id}.json"

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.current_session), f, indent=2, ensure_ascii=False)

        self._add_to_history("saved", self.current_session.session_id, self.current_session.name)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all available sessions.

        Returns:
            List of session summaries
        """
        sessions = []

        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Create summary
                summary = {
                    "session_id": data["session_id"],
                    "name": data["name"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "metadata": data.get("metadata", {}),
                    "data_keys": list(data.get("data", {}).keys()),
                }
                sessions.append(summary)

            except (json.JSONDecodeError, KeyError):
                # Skip corrupted session files
                continue

        # Sort by updated time, most recent first
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: ID of session to delete

        Returns:
            True if deleted, False if not found
        """
        session_file = self.session_dir / f"{session_id}.json"

        if session_file.exists():
            session_file.unlink()

            # Clear current session if it's the one being deleted
            if self.current_session and self.current_session.session_id == session_id:
                self.current_session = None

            self._add_to_history("deleted", session_id, "")
            return True

        return False

    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Get data from current session.

        Args:
            key: Data key to retrieve
            default: Default value if key not found

        Returns:
            Session data value or default
        """
        if not self.current_session:
            return default

        return self.current_session.data.get(key, default)

    def set_session_data(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Set data in current session.

        Args:
            key: Data key to set
            value: Value to store
            auto_save: Whether to automatically save session

        Raises:
            ValueError: If no active session
        """
        if not self.current_session:
            raise ValueError("No active session")

        self.current_session.data[key] = value

        if auto_save:
            self.save_session()

    def update_session_metadata(self, metadata: dict[str, Any], auto_save: bool = True) -> None:
        """Update session metadata.

        Args:
            metadata: Metadata to merge with existing
            auto_save: Whether to automatically save session

        Raises:
            ValueError: If no active session
        """
        if not self.current_session:
            raise ValueError("No active session")

        self.current_session.metadata.update(metadata)

        if auto_save:
            self.save_session()

    def clear_current_session(self) -> None:
        """Clear the current session without deleting from disk."""
        self.current_session = None

    def get_session_summary(self) -> dict[str, Any] | None:
        """Get summary of current session.

        Returns:
            Session summary or None if no active session
        """
        if not self.current_session:
            return None

        return {
            "session_id": self.current_session.session_id,
            "name": self.current_session.name,
            "created_at": self.current_session.created_at,
            "updated_at": self.current_session.updated_at,
            "metadata": self.current_session.metadata,
            "data_keys": list(self.current_session.data.keys()),
            "data_size": len(json.dumps(self.current_session.data)),
        }

    def export_session(self, filepath: Path | str) -> None:
        """Export current session to a file.

        Args:
            filepath: Path to export session to

        Raises:
            ValueError: If no active session
        """
        if not self.current_session:
            raise ValueError("No active session to export")

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(self.current_session), f, indent=2, ensure_ascii=False)

    def import_session(self, filepath: Path | str, override_id: bool = True) -> Session:
        """Import a session from a file.

        Args:
            filepath: Path to import session from
            override_id: Whether to generate new ID for imported session

        Returns:
            Imported Session object
        """
        filepath = Path(filepath)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        if override_id:
            data["session_id"] = str(uuid.uuid4())
            data["updated_at"] = datetime.now().isoformat()

        session = Session(**data)
        self.current_session = session

        # Save to session directory
        self.save_session()

        return session

    def _add_to_history(self, action: str, session_id: str, session_name: str) -> None:
        """Add entry to session history.

        Args:
            action: Action performed
            session_id: Session ID
            session_name: Session name
        """
        self.session_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "session_id": session_id,
                "session_name": session_name,
            }
        )

        # Keep only last 100 history entries
        if len(self.session_history) > 100:
            self.session_history = self.session_history[-100:]
