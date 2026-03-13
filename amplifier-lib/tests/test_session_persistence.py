"""Tests for amplifier_lib.session.persistence."""

import json
from pathlib import Path

import pytest


class TestWriteTranscript:
    def test_writes_jsonl(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_transcript

        messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        write_transcript(tmp_path, messages)
        lines = (tmp_path / "transcript.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["content"] == "hello"

    def test_filters_system_roles(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_transcript

        messages = [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "hello"},
        ]
        write_transcript(tmp_path, messages)
        lines = (tmp_path / "transcript.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["role"] == "user"

    def test_filters_developer_roles(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_transcript

        messages = [
            {"role": "developer", "content": "internal"},
            {"role": "user", "content": "hello"},
        ]
        write_transcript(tmp_path, messages)
        lines = (tmp_path / "transcript.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1


class TestLoadTranscript:
    def test_loads_messages(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import load_transcript

        (tmp_path / "transcript.jsonl").write_text('{"role": "user", "content": "hello"}\n')
        messages = load_transcript(tmp_path)
        assert len(messages) == 1

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import load_transcript

        with pytest.raises(FileNotFoundError):
            load_transcript(tmp_path)


class TestWriteMetadata:
    def test_writes_json(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_metadata

        write_metadata(tmp_path, {"session_id": "abc", "turn_count": 1})
        data = json.loads((tmp_path / "metadata.json").read_text())
        assert data["session_id"] == "abc"

    def test_merges_with_existing(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import write_metadata

        write_metadata(tmp_path, {"session_id": "abc", "name": "chat"})
        write_metadata(tmp_path, {"turn_count": 3})
        data = json.loads((tmp_path / "metadata.json").read_text())
        assert data["name"] == "chat"
        assert data["turn_count"] == 3


class TestLoadMetadata:
    def test_missing_returns_empty(self, tmp_path: Path) -> None:
        from amplifier_lib.session.persistence import load_metadata

        assert load_metadata(tmp_path) == {}