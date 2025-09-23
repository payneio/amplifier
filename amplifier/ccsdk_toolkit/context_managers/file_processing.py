"""FileProcessor context manager for batch file processing with Claude Code SDK.

This module provides a focused context manager for file discovery and batch
processing operations, integrating with the SDK's helpers and utilities.
"""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import TypeVar
from typing import Union

if TYPE_CHECKING:
    from amplifier.ccsdk_toolkit.client import ClaudeCodeSDKClient
else:
    # For runtime when client may not be available
    ClaudeCodeSDKClient = Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProcessorFunction(Protocol):
    """Protocol for file processing functions."""

    async def __call__(self, file_path: Path, content: str) -> Any:
        """Process a single file."""
        pass


class FileProcessor:
    """Context manager for batch file processing with progress tracking.

    This context manager provides a clean interface for discovering and processing
    files in batches, with automatic progress tracking and resource cleanup.

    Example:
        ```python
        async with FileProcessor(client, pattern="**/*.md") as processor:
            results = await processor.process_batch(analysis_func)
        ```

    Attributes:
        client: Initialized Claude Code SDK client
        pattern: Glob pattern for file discovery
        root_dir: Root directory for file search
        batch_size: Number of files to process in parallel
        show_progress: Whether to show progress tracking
    """

    def __init__(
        self,
        client: ClaudeCodeSDKClient,
        pattern: str = "**/*.py",
        root_dir: Union[str, Path] | None = None,
        batch_size: int = 5,
        show_progress: bool = True,
    ):
        """Initialize the FileProcessor context manager.

        Args:
            client: Initialized SDK client
            pattern: Glob pattern for file discovery (default: "**/*.py")
            root_dir: Root directory for search (default: current directory)
            batch_size: Number of files to process in parallel
            show_progress: Whether to show progress indicators
        """
        self.client = client
        self.pattern = pattern
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.batch_size = batch_size
        self.show_progress = show_progress

        self._progress_tracker: Any | None = None
        self._discovered_files: list[Path] = []
        self._results: dict[Path, Any] = {}
        self._errors: dict[Path, Exception] = {}

    async def __aenter__(self) -> "FileProcessor":
        """Enter the context manager and set up resources.

        Returns:
            Self for use in async with statement
        """
        logger.debug(f"Entering FileProcessor context for pattern: {self.pattern}")

        # Discover files
        self._discovered_files = self._discover_files()
        logger.info(f"Discovered {len(self._discovered_files)} files to process")

        # Initialize progress tracking if needed
        if self.show_progress and self._discovered_files:
            # Simple progress tracking - could be replaced with actual progress bar
            logger.info(f"Will process {len(self._discovered_files)} files")

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Exit the context manager and clean up resources.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        logger.debug("Exiting FileProcessor context")

        # Clean up progress tracking
        if self._progress_tracker:
            pass  # Cleanup if using actual progress tracker

        # Log summary
        if self._results or self._errors:
            logger.info(f"Processing complete: {len(self._results)} succeeded, {len(self._errors)} failed")

        # Clear state
        self._discovered_files.clear()
        self._results.clear()
        self._errors.clear()

    def _discover_files(self) -> list[Path]:
        """Discover files matching the pattern.

        Returns:
            List of discovered file paths
        """
        files = list(self.root_dir.glob(self.pattern))

        # Filter out directories and non-files
        files = [f for f in files if f.is_file()]

        # Sort for consistent ordering
        files.sort()

        return files

    async def process_batch(
        self, processor_func: ProcessorFunction, filter_func: Callable[[Path], bool] | None = None
    ) -> dict[Path, Any]:
        """Process discovered files in batches.

        Args:
            processor_func: Async function to process each file
            filter_func: Optional filter to select files for processing

        Returns:
            Dictionary mapping file paths to results
        """
        if not self.client:
            raise RuntimeError("FileProcessor not properly initialized")

        # Apply filter if provided
        files_to_process = self._discovered_files
        if filter_func:
            files_to_process = [f for f in files_to_process if filter_func(f)]
            logger.debug(f"Filtered to {len(files_to_process)} files")

        if not files_to_process:
            logger.warning("No files to process after filtering")
            return {}

        # Create processing tasks
        async def process_file(file_path: Path) -> tuple[Path, Any]:
            """Process a single file with error handling."""
            try:
                content = file_path.read_text(encoding="utf-8")
                result = await processor_func(file_path, content)

                # Update progress
                if self.show_progress:
                    logger.debug(f"Processed {file_path}")

                return file_path, result

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self._errors[file_path] = e

                # Update progress
                if self.show_progress:
                    logger.debug(f"Processed {file_path}")

                raise

        # Process in batches
        for i in range(0, len(files_to_process), self.batch_size):
            batch = files_to_process[i : i + self.batch_size]
            batch_tasks = [process_file(f) for f in batch]

            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Collect results
            for result in batch_results:
                if isinstance(result, Exception):
                    continue  # Already logged in process_file
                # Type narrowing - result is not Exception here
                file_path, file_result = result  # type: ignore[misc]
                self._results[file_path] = file_result

        return self._results

    async def process_with_prompt(
        self, prompt_template: str, filter_func: Callable[[Path], bool] | None = None
    ) -> dict[Path, str]:
        """Process files using a prompt template.

        Args:
            prompt_template: Template with {file_path} and {content} placeholders
            filter_func: Optional filter for file selection

        Returns:
            Dictionary mapping file paths to AI responses
        """

        async def process_with_ai(file_path: Path, content: str) -> str:
            """Process file with AI using prompt template."""
            prompt = prompt_template.format(file_path=str(file_path), content=content)
            response = await self.client.query_with_retry(prompt)
            return response

        return await self.process_batch(process_with_ai, filter_func)

    @property
    def discovered_files(self) -> list[Path]:
        """Get list of discovered files."""
        return self._discovered_files.copy()

    @property
    def results(self) -> dict[Path, Any]:
        """Get processing results."""
        return self._results.copy()

    @property
    def errors(self) -> dict[Path, Exception]:
        """Get processing errors."""
        return self._errors.copy()

    @property
    def summary(self) -> dict[str, Any]:
        """Get processing summary statistics."""
        return {
            "total_discovered": len(self._discovered_files),
            "processed": len(self._results),
            "failed": len(self._errors),
            "success_rate": (len(self._results) / len(self._discovered_files) if self._discovered_files else 0),
        }
