"""BatchProcessor - Process multiple items with progress tracking

This helper uses the SDK client through composition to process
batches of items with concurrency control and progress tracking.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from collections.abc import Coroutine
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single item"""

    item_id: str
    status: str  # "success", "error", "skipped"
    result: Any | None = None
    error: str | None = None
    processing_time: float = 0.0
    timestamp: str = ""


class BatchProcessor:
    """Process multiple items with progress tracking.

    Uses the SDK client through composition to handle batch processing
    with concurrency control, progress tracking, and error handling.
    """

    def __init__(self, client: Any, max_concurrent: int = 5):
        """Initialize with an SDK client.

        Args:
            client: Initialized ClaudeSDKClient instance
            max_concurrent: Maximum concurrent processing tasks
        """
        self.client = client
        self.max_concurrent = max_concurrent
        self.results: list[ProcessingResult] = []
        self.metadata: dict[str, Any] = {
            "started_at": None,
            "completed_at": None,
            "total_items": 0,
            "processed_items": 0,
            "successful_items": 0,
            "failed_items": 0,
            "skipped_items": 0,
        }

    async def process_items(
        self,
        items: list[Any],
        processor_func: Callable[[Any, Any], Coroutine[Any, Any, Any]],
        item_id_func: Callable[[Any], str] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ProcessingResult]:
        """Process a list of items with the given processor function.

        Args:
            items: List of items to process
            processor_func: Async function that processes a single item
            item_id_func: Optional function to extract ID from item
            progress_callback: Optional callback for progress updates

        Returns:
            List of processing results
        """
        self.metadata["started_at"] = datetime.now().isoformat()
        self.metadata["total_items"] = len(items)
        self.results = []

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_with_semaphore(item: Any, index: int) -> ProcessingResult:
            async with semaphore:
                return await self._process_single_item(item, index, processor_func, item_id_func, progress_callback)

        # Process all items concurrently with semaphore control
        tasks = [process_with_semaphore(item, index) for index, item in enumerate(items)]

        self.results = await asyncio.gather(*tasks)

        # Update metadata
        self.metadata["completed_at"] = datetime.now().isoformat()
        self.metadata["processed_items"] = len(self.results)
        self.metadata["successful_items"] = sum(1 for r in self.results if r.status == "success")
        self.metadata["failed_items"] = sum(1 for r in self.results if r.status == "error")
        self.metadata["skipped_items"] = sum(1 for r in self.results if r.status == "skipped")

        return self.results

    async def _process_single_item(
        self,
        item: Any,
        index: int,
        processor_func: Callable[[Any, Any], Coroutine[Any, Any, Any]],
        item_id_func: Callable[[Any], str] | None,
        progress_callback: Callable[[int, int], None] | None,
    ) -> ProcessingResult:
        """Process a single item with error handling.

        Args:
            item: Item to process
            index: Item index
            processor_func: Processing function
            item_id_func: Function to extract item ID
            progress_callback: Progress callback

        Returns:
            ProcessingResult for this item
        """
        # Generate item ID
        if item_id_func:
            item_id = item_id_func(item)
        else:
            item_id = f"item_{index}"

        start_time = asyncio.get_event_loop().time()
        result = ProcessingResult(item_id=item_id, status="processing", timestamp=datetime.now().isoformat())

        try:
            # Process the item
            processed_result = await processor_func(self.client, item)
            result.status = "success"
            result.result = processed_result

        except Exception as e:
            logger.error(f"Error processing {item_id}: {e}")
            result.status = "error"
            result.error = str(e)

        finally:
            result.processing_time = asyncio.get_event_loop().time() - start_time

            # Update progress
            if progress_callback:
                completed = sum(1 for r in self.results if r.status != "processing")
                progress_callback(completed + 1, self.metadata["total_items"])

        return result

    async def process_files(
        self,
        file_pattern: str,
        processor_func: Callable[[Any, Path], Coroutine[Any, Any, Any]],
        base_dir: Path | str = ".",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ProcessingResult]:
        """Process files matching a pattern.

        Args:
            file_pattern: Glob pattern for files (e.g., "**/*.txt")
            processor_func: Async function to process each file
            base_dir: Base directory for file search
            progress_callback: Optional progress callback

        Returns:
            List of processing results
        """
        base_dir = Path(base_dir)
        files = list(base_dir.glob(file_pattern))

        if not files:
            logger.warning(f"No files found matching pattern: {file_pattern}")
            return []

        logger.info(f"Found {len(files)} files to process")

        # Use file path as ID
        def file_id_func(file_path: Path) -> str:
            return str(file_path.relative_to(base_dir))

        return await self.process_items(
            files, processor_func, item_id_func=file_id_func, progress_callback=progress_callback
        )

    def get_results(self) -> list[ProcessingResult]:
        """Get all processing results.

        Returns:
            List of all processing results
        """
        return self.results

    def get_successful_results(self) -> list[ProcessingResult]:
        """Get only successful processing results.

        Returns:
            List of successful results
        """
        return [r for r in self.results if r.status == "success"]

    def get_failed_results(self) -> list[ProcessingResult]:
        """Get only failed processing results.

        Returns:
            List of failed results
        """
        return [r for r in self.results if r.status == "error"]

    def save_results(self, filepath: Path | str) -> None:
        """Save processing results to file.

        Args:
            filepath: Path to save results
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {"metadata": self.metadata, "results": [asdict(r) for r in self.results]}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(self.results)} results to {filepath}")

    def get_summary(self) -> dict[str, Any]:
        """Get processing summary.

        Returns:
            Dictionary with processing statistics
        """
        if self.metadata["started_at"] and self.metadata["completed_at"]:
            start = datetime.fromisoformat(self.metadata["started_at"])
            end = datetime.fromisoformat(self.metadata["completed_at"])
            duration = (end - start).total_seconds()
        else:
            duration = 0

        return {
            **self.metadata,
            "processing_duration": duration,
            "average_processing_time": (
                sum(r.processing_time for r in self.results) / len(self.results) if self.results else 0
            ),
            "success_rate": (
                self.metadata["successful_items"] / self.metadata["total_items"] * 100
                if self.metadata["total_items"] > 0
                else 0
            ),
        }
