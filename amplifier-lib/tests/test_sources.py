"""Tests for source handlers."""

import tempfile
import zipfile
from pathlib import Path

import pytest
from amplifier_lib.paths.resolution import ParsedURI
from amplifier_lib.sources.file import FileSourceHandler
from amplifier_lib.sources.git import GitSourceHandler
from amplifier_lib.sources.http import HttpSourceHandler
from amplifier_lib.sources.zip import ZipSourceHandler


class TestGitSourceHandlerIntegrity:
    """Tests for GitSourceHandler._verify_clone_integrity."""

    def _make_handler(self) -> GitSourceHandler:
        return GitSourceHandler()

    def _make_clone(
        self, tmp_path: Path, root_files: dict[str, str] | None = None
    ) -> Path:
        """Create a fake clone directory with .git and optional files."""
        clone = tmp_path / "repo"
        clone.mkdir()
        (clone / ".git").mkdir()
        for name, content in (root_files or {}).items():
            (clone / name).write_text(content)
        return clone

    # -- Basic cases (no subpath) --

    def test_nonexistent_path_returns_false(self, tmp_path: Path) -> None:
        handler = self._make_handler()
        assert handler._verify_clone_integrity(tmp_path / "nope") is False

    def test_missing_git_dir_returns_false(self, tmp_path: Path) -> None:
        clone = tmp_path / "repo"
        clone.mkdir()
        (clone / "pyproject.toml").write_text("")
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is False

    def test_root_pyproject_passes(self, tmp_path: Path) -> None:
        clone = self._make_clone(tmp_path, {"pyproject.toml": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is True

    def test_root_setup_py_passes(self, tmp_path: Path) -> None:
        clone = self._make_clone(tmp_path, {"setup.py": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is True

    def test_root_setup_cfg_passes(self, tmp_path: Path) -> None:
        clone = self._make_clone(tmp_path, {"setup.cfg": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is True

    def test_root_bundle_md_passes(self, tmp_path: Path) -> None:
        clone = self._make_clone(tmp_path, {"bundle.md": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is True

    def test_root_bundle_yaml_passes(self, tmp_path: Path) -> None:
        clone = self._make_clone(tmp_path, {"bundle.yaml": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is True

    def test_empty_clone_fails(self, tmp_path: Path) -> None:
        """Clone with .git but no recognized files fails."""
        clone = self._make_clone(tmp_path)
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is False

    # -- Subpath cases (monorepo-style bundles) --

    def test_subpath_bundle_md_passes(self, tmp_path: Path) -> None:
        """bundle.md in subdirectory passes when subpath is provided."""
        clone = self._make_clone(tmp_path)
        sub = clone / "bundles" / "foundation"
        sub.mkdir(parents=True)
        (sub / "bundle.md").write_text("# Foundation bundle")
        handler = self._make_handler()
        assert (
            handler._verify_clone_integrity(clone, subpath="bundles/foundation") is True
        )

    def test_subpath_pyproject_passes(self, tmp_path: Path) -> None:
        """pyproject.toml in subdirectory passes when subpath is provided."""
        clone = self._make_clone(tmp_path)
        sub = clone / "packages" / "mylib"
        sub.mkdir(parents=True)
        (sub / "pyproject.toml").write_text("[project]\nname = 'mylib'")
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone, subpath="packages/mylib") is True

    def test_subpath_without_flag_fails(self, tmp_path: Path) -> None:
        """bundle.md only in subdirectory fails when subpath is NOT provided."""
        clone = self._make_clone(tmp_path)
        sub = clone / "bundles" / "foundation"
        sub.mkdir(parents=True)
        (sub / "bundle.md").write_text("")
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone) is False

    def test_subpath_nonexistent_subdir_falls_back_to_root(
        self, tmp_path: Path
    ) -> None:
        """If subpath dir doesn't exist, only root is checked."""
        clone = self._make_clone(tmp_path)
        handler = self._make_handler()
        # No root files, subpath doesn't exist -> fails
        assert handler._verify_clone_integrity(clone, subpath="nonexistent") is False

    def test_subpath_nonexistent_subdir_root_passes(self, tmp_path: Path) -> None:
        """If subpath dir doesn't exist but root has valid files, passes."""
        clone = self._make_clone(tmp_path, {"pyproject.toml": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone, subpath="nonexistent") is True

    def test_root_and_subpath_both_valid(self, tmp_path: Path) -> None:
        """Both root and subpath having valid files passes (root short-circuits)."""
        clone = self._make_clone(tmp_path, {"pyproject.toml": ""})
        sub = clone / "bundle"
        sub.mkdir()
        (sub / "bundle.md").write_text("")
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone, subpath="bundle") is True

    def test_empty_string_subpath_treated_as_no_subpath(self, tmp_path: Path) -> None:
        """Empty string subpath behaves like None."""
        clone = self._make_clone(tmp_path, {"bundle.yaml": ""})
        handler = self._make_handler()
        assert handler._verify_clone_integrity(clone, subpath="") is True


class TestFileSourceHandler:
    """Tests for FileSourceHandler."""

    def test_can_handle_file_uri(self) -> None:
        """Handles file:// URIs."""
        handler = FileSourceHandler()
        parsed = ParsedURI(
            scheme="file", host="", path="/some/path", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is True

    def test_can_handle_absolute_path(self) -> None:
        """Handles absolute paths (is_file=True when scheme=file)."""
        handler = FileSourceHandler()
        # Absolute paths get scheme="file" from parse_uri
        parsed = ParsedURI(
            scheme="file", host="", path="/absolute/path", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is True

    def test_cannot_handle_git(self) -> None:
        """Does not handle git URIs."""
        handler = FileSourceHandler()
        parsed = ParsedURI(
            scheme="git+https",
            host="github.com",
            path="/org/repo",
            ref="main",
            subpath="",
        )
        assert handler.can_handle(parsed) is False

    @pytest.mark.asyncio
    async def test_resolve_existing_file(self) -> None:
        """Resolves existing file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.yaml"
            test_file.write_text("name: test")

            handler = FileSourceHandler(base_path=Path(tmpdir))
            parsed = ParsedURI(
                scheme="file", host="", path=str(test_file), ref="", subpath=""
            )
            result = await handler.resolve(parsed, Path(tmpdir) / "cache")

            assert result.active_path == test_file
            # source_root is the parent directory for non-cached files
            assert result.source_root == test_file.parent

    @pytest.mark.asyncio
    async def test_resolve_with_subpath(self) -> None:
        """Resolves file path with subpath."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            subdir = base / "bundles" / "core"
            subdir.mkdir(parents=True)
            (subdir / "bundle.yaml").write_text("name: core")

            handler = FileSourceHandler(base_path=base)
            parsed = ParsedURI(
                scheme="file",
                host="",
                path=str(base / "bundles"),
                ref="",
                subpath="core",
            )
            result = await handler.resolve(parsed, base / "cache")

            assert result.active_path == subdir
            assert result.source_root == (base / "bundles").resolve()


class TestHttpSourceHandler:
    """Tests for HttpSourceHandler."""

    def test_can_handle_https(self) -> None:
        """Handles https:// URIs."""
        handler = HttpSourceHandler()
        parsed = ParsedURI(
            scheme="https", host="example.com", path="/bundle.yaml", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is True

    def test_can_handle_http(self) -> None:
        """Handles http:// URIs."""
        handler = HttpSourceHandler()
        parsed = ParsedURI(
            scheme="http", host="example.com", path="/bundle.yaml", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is True

    def test_cannot_handle_file(self) -> None:
        """Does not handle file:// URIs."""
        handler = HttpSourceHandler()
        parsed = ParsedURI(
            scheme="file", host="", path="/local/path", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is False

    def test_cannot_handle_git(self) -> None:
        """Does not handle git URIs."""
        handler = HttpSourceHandler()
        parsed = ParsedURI(
            scheme="git+https",
            host="github.com",
            path="/org/repo",
            ref="main",
            subpath="",
        )
        assert handler.can_handle(parsed) is False


class TestZipSourceHandler:
    """Tests for ZipSourceHandler."""

    def test_can_handle_zip_https(self) -> None:
        """Handles zip+https:// URIs."""
        handler = ZipSourceHandler()
        parsed = ParsedURI(
            scheme="zip+https",
            host="example.com",
            path="/bundle.zip",
            ref="",
            subpath="",
        )
        assert handler.can_handle(parsed) is True

    def test_can_handle_zip_file(self) -> None:
        """Handles zip+file:// URIs."""
        handler = ZipSourceHandler()
        parsed = ParsedURI(
            scheme="zip+file", host="", path="/local/bundle.zip", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is True

    def test_cannot_handle_plain_https(self) -> None:
        """Does not handle plain https:// URIs."""
        handler = ZipSourceHandler()
        parsed = ParsedURI(
            scheme="https", host="example.com", path="/bundle.yaml", ref="", subpath=""
        )
        assert handler.can_handle(parsed) is False

    def test_cannot_handle_git(self) -> None:
        """Does not handle git URIs."""
        handler = ZipSourceHandler()
        parsed = ParsedURI(
            scheme="git+https",
            host="github.com",
            path="/org/repo",
            ref="main",
            subpath="",
        )
        assert handler.can_handle(parsed) is False

    @pytest.mark.asyncio
    async def test_resolve_local_zip(self) -> None:
        """Resolves local zip file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            cache_dir = base / "cache"

            # Create a test zip file
            zip_path = base / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("bundle.yaml", "name: test-bundle\nversion: 1.0.0")
                zf.writestr("context/readme.md", "# Test Bundle")

            handler = ZipSourceHandler()
            parsed = ParsedURI(
                scheme="zip+file", host="", path=str(zip_path), ref="", subpath=""
            )
            result = await handler.resolve(parsed, cache_dir)

            assert result.active_path.exists()
            assert (result.active_path / "bundle.yaml").exists()
            assert (result.active_path / "context" / "readme.md").exists()

    @pytest.mark.asyncio
    async def test_resolve_local_zip_with_subpath(self) -> None:
        """Resolves local zip file with subpath."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            cache_dir = base / "cache"

            # Create a test zip file with nested structure
            zip_path = base / "bundles.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("foundation/bundle.yaml", "name: foundation")
                zf.writestr("foundation/context/readme.md", "# Foundation")
                zf.writestr("extended/bundle.yaml", "name: extended")

            handler = ZipSourceHandler()
            parsed = ParsedURI(
                scheme="zip+file",
                host="",
                path=str(zip_path),
                ref="",
                subpath="foundation",
            )
            result = await handler.resolve(parsed, cache_dir)

            assert result.active_path.exists()
            assert result.active_path.name == "foundation"
            assert (result.active_path / "bundle.yaml").exists()
            assert (
                result.source_root != result.active_path
            )  # subpath creates a subdirectory

    @pytest.mark.asyncio
    async def test_uses_cache(self) -> None:
        """Uses cached extraction on second resolve."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            cache_dir = base / "cache"

            # Create a test zip file
            zip_path = base / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("bundle.yaml", "name: test")

            handler = ZipSourceHandler()
            parsed = ParsedURI(
                scheme="zip+file", host="", path=str(zip_path), ref="", subpath=""
            )

            # First resolve - extracts
            result1 = await handler.resolve(parsed, cache_dir)

            # Delete original zip
            zip_path.unlink()

            # Second resolve - uses cache
            result2 = await handler.resolve(parsed, cache_dir)

            assert result1.active_path == result2.active_path
            assert result2.active_path.exists()
