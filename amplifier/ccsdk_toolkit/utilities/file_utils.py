"""
File utilities for claude-code-sdk responses

Handles saving and loading SDK responses with defensive I/O for cloud sync issues.
"""

import logging
import time
from pathlib import Path
from typing import Any

from amplifier.utils.file_io import read_json
from amplifier.utils.file_io import write_json

logger = logging.getLogger(__name__)


def ensure_data_dir(base_path: Path | None = None) -> Path:
    """Ensure data directory exists and return path.

    Args:
        base_path: Optional base path. Defaults to ./data/ccsdk

    Returns:
        Path to data directory

    Example:
        >>> data_dir = ensure_data_dir()
        >>> session_file = data_dir / "session_001.json"
    """
    if base_path is None:
        base_path = Path("data/ccsdk")

    base_path = Path(base_path)
    base_path.mkdir(parents=True, exist_ok=True)

    return base_path


def save_response(
    response: Any,
    filepath: str | Path,
    format: str = "json",
    append: bool = False,
) -> Path:
    """Save SDK response with cloud-sync retry logic.

    Args:
        response: SDK response object
        filepath: Path to save file
        format: Output format ('json', 'txt', 'md')
        append: Append to existing file if True

    Returns:
        Path to saved file

    Raises:
        ValueError: For unsupported format
        OSError: After retry failures

    Example:
        >>> response = await client.query("Hello")
        >>> save_response(response, "output.json")
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Parse response based on type
    if hasattr(response, "__dict__"):
        data = vars(response)
    elif isinstance(response, dict):
        data = response
    elif isinstance(response, str):
        data = {"content": response, "timestamp": time.time()}
    else:
        data = {"content": str(response), "timestamp": time.time()}

    # Save based on format
    if format == "json":
        if append and filepath.exists():
            # Load existing data
            existing = read_json(filepath)
            if isinstance(existing, list):
                existing.append(data)
                write_json(existing, filepath)
            else:
                # Convert to list format
                write_json([existing, data], filepath)
        else:
            write_json(data, filepath)

    elif format == "txt" or format == "md":
        # Extract text content
        content = data.get("content", str(data))

        mode = "a" if append else "w"
        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                with open(filepath, mode, encoding="utf-8") as f:
                    if append and filepath.exists():
                        f.write("\n\n---\n\n")  # Separator
                    f.write(str(content))
                    f.flush()
                break
            except OSError as e:
                if e.errno == 5 and attempt < max_retries - 1:
                    if attempt == 0:
                        logger.warning(
                            f"File I/O error on {filepath} - retrying. "
                            "This may be due to cloud sync (OneDrive, Dropbox, etc.)"
                        )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

    else:
        raise ValueError(f"Unsupported format: {format}")

    logger.info(f"Saved response to {filepath}")
    return filepath


def load_conversation(filepath: str | Path) -> list[dict]:
    """Load saved conversation from file.

    Args:
        filepath: Path to conversation file

    Returns:
        List of conversation entries

    Example:
        >>> conversation = load_conversation("session.json")
        >>> for entry in conversation:
        ...     print(entry['content'])
    """
    filepath = Path(filepath)

    if not filepath.exists():
        logger.warning(f"Conversation file not found: {filepath}")
        return []

    data = read_json(filepath)

    # Ensure we return a list
    if isinstance(data, list):
        return data
    return [data]


def save_conversation(
    entries: list[dict],
    filepath: str | Path,
    overwrite: bool = True,
) -> Path:
    """Save conversation history to file.

    Args:
        entries: List of conversation entries
        filepath: Path to save file
        overwrite: Replace existing file if True

    Returns:
        Path to saved file

    Example:
        >>> conversation = [
        ...     {'role': 'user', 'content': 'Hello'},
        ...     {'role': 'assistant', 'content': 'Hi there!'}
        ... ]
        >>> save_conversation(conversation, "chat.json")
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite and filepath.exists():
        # Merge with existing
        existing = load_conversation(filepath)
        entries = existing + entries

    write_json(entries, filepath)
    logger.info(f"Saved {len(entries)} conversation entries to {filepath}")

    return filepath
