"""Service queue system with parallel processing for deployment-builder tool."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from queue import PriorityQueue, Empty
import threading
import time
import logging
from .config import ServiceConfig

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status of a service item in the queue."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class ServiceItem:
    """Represents a service item to be executed in the queue."""

    cluster_name: str
    cluster_type: str
    service_name: str
    service_config: ServiceConfig
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    status: ServiceStatus = ServiceStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other):
        """Priority comparison for PriorityQueue (higher priority = lower number)."""
        if not isinstance(other, ServiceItem):
            return NotImplemented
        # First compare by priority (lower number = higher priority)
        if self.priority != other.priority:
            return self.priority < other.priority
        # Then by creation time (earlier = higher priority)
        return self.created_at < other.created_at


class ServiceQueue:
    """Thread-safe service queue with priority support."""

    def __init__(self, max_workers: int = 4, timeout: int = 300):
        """Initialize the service queue.

        Args:
            max_workers: Maximum number of workers that can process items
            timeout: Timeout in seconds for queue operations
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.queue = PriorityQueue()
        self.completed_items: List[ServiceItem] = []
        self.failed_items: List[ServiceItem] = []
        self.running_items: List[ServiceItem] = []
        self.workers: List["ServiceWorker"] = []
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        self._stats = {
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "running_items": 0,
            "pending_items": 0,
        }

    def add_service_item(self, item: ServiceItem) -> None:
        """Add service item to queue with priority.

        Args:
            item: Service item to add to the queue
        """
        with self.lock:
            self.queue.put(item)
            self._stats["total_items"] += 1
            self._stats["pending_items"] += 1
            logger.debug(f"Added service item {item.service_name} for cluster {item.cluster_name} to queue")

    def get_next_item(self) -> Optional[ServiceItem]:
        """Get next service item from queue.

        Returns:
            Next service item to process, or None if queue is empty or shutdown
        """
        try:
            # Use timeout to allow checking shutdown event
            item = self.queue.get(timeout=1.0)
            if item is not None:
                with self.lock:
                    item.status = ServiceStatus.RUNNING
                    item.started_at = datetime.now()
                    self.running_items.append(item)
                    self._stats["running_items"] += 1
                    self._stats["pending_items"] -= 1
                    logger.debug(
                        f"Retrieved service item {item.service_name} for cluster {item.cluster_name} from queue"
                    )
            return item
        except Empty:
            # Check if we should shutdown
            if self.shutdown_event.is_set():
                return None
            # Continue waiting
            return self.get_next_item()

    def mark_completed(self, item: ServiceItem) -> None:
        """Mark service item as completed.

        Args:
            item: Service item that completed successfully
        """
        with self.lock:
            item.status = ServiceStatus.COMPLETED
            item.completed_at = datetime.now()
            if item in self.running_items:
                self.running_items.remove(item)
            self.completed_items.append(item)
            self._stats["completed_items"] += 1
            self._stats["running_items"] -= 1
            logger.info(f"Service item {item.service_name} for cluster {item.cluster_name} completed successfully")

    def mark_failed(self, item: ServiceItem, error: str) -> None:
        """Mark service item as failed.

        Args:
            item: Service item that failed
            error: Error message describing the failure
        """
        with self.lock:
            item.error_message = error
            item.retry_count += 1

            if item in self.running_items:
                self.running_items.remove(item)

            # Check if we should retry
            if item.retry_count <= item.max_retries:
                item.status = ServiceStatus.RETRYING
                # Re-queue the item for retry
                self.queue.put(item)
                self._stats["pending_items"] += 1
                logger.warning(
                    f"Service item {item.service_name} for cluster {item.cluster_name} failed, retrying ({item.retry_count}/{item.max_retries}): {error}"
                )
            else:
                item.status = ServiceStatus.FAILED
                self.failed_items.append(item)
                self._stats["failed_items"] += 1
                logger.error(
                    f"Service item {item.service_name} for cluster {item.cluster_name} failed permanently after {item.retry_count} retries: {error}"
                )

            self._stats["running_items"] -= 1

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics.

        Returns:
            Dictionary containing queue status and statistics
        """
        with self.lock:
            return {
                "queue_size": self.queue.qsize(),
                "completed_count": len(self.completed_items),
                "failed_count": len(self.failed_items),
                "running_count": len(self.running_items),
                "pending_count": self._stats["pending_items"],
                "total_count": self._stats["total_items"],
                "worker_count": len(self.workers),
                "max_workers": self.max_workers,
                "is_shutdown": self.shutdown_event.is_set(),
            }

    def shutdown(self) -> None:
        """Shutdown the queue and signal all workers to stop."""
        logger.info("Shutting down service queue")
        self.shutdown_event.set()

        # Stop all workers
        for worker in self.workers:
            worker.stop()

        # Wait for workers to finish
        for worker in self.workers:
            if worker.thread and worker.thread.is_alive():
                worker.thread.join(timeout=5.0)

    def is_empty(self) -> bool:
        """Check if queue is empty and no items are running.

        Returns:
            True if queue is empty and no items are running
        """
        with self.lock:
            return self.queue.empty() and len(self.running_items) == 0 and not self.shutdown_event.is_set()


class ServiceWorker:
    """Worker thread that processes service items from the queue."""

    def __init__(self, worker_id: int, queue: ServiceQueue):
        """Initialize the service worker.

        Args:
            worker_id: Unique identifier for this worker
            queue: Service queue to process items from
        """
        self.worker_id = worker_id
        self.queue = queue
        self.current_item: Optional[ServiceItem] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start worker thread."""
        if self.thread and self.thread.is_alive():
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self.is_running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self.run, name=f"ServiceWorker-{self.worker_id}")
        self.thread.daemon = True
        self.thread.start()
        logger.debug(f"Started worker {self.worker_id}")

    def stop(self) -> None:
        """Stop worker thread."""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning(f"Worker {self.worker_id} did not stop gracefully")

        logger.debug(f"Stopped worker {self.worker_id}")

    def run(self) -> None:
        """Main worker loop."""
        logger.debug(f"Worker {self.worker_id} started processing")

        while self.is_running and not self.queue.shutdown_event.is_set() and not self._stop_event.is_set():
            try:
                # Get next item from queue
                item = self.queue.get_next_item()
                if item is None:
                    # Shutdown or no items available
                    break

                self.current_item = item
                logger.debug(f"Worker {self.worker_id} processing {item.service_name} for cluster {item.cluster_name}")

                # Execute the service
                success = self.execute_service(item)

                if success:
                    self.queue.mark_completed(item)
                else:
                    self.queue.mark_failed(item, f"Service execution failed")

                self.current_item = None

            except Exception as e:
                logger.error(f"Worker {self.worker_id} encountered error: {e}")
                if self.current_item:
                    self.queue.mark_failed(self.current_item, str(e))
                    self.current_item = None

        logger.debug(f"Worker {self.worker_id} finished processing")

    def execute_service(self, item: ServiceItem) -> bool:
        """Execute a single service item.

        Args:
            item: Service item to execute

        Returns:
            True if service executed successfully, False otherwise
        """
        try:
            # Build the command
            cmd_parts = [item.service_config.cmd]
            if item.service_config.kubeconfig_flag:
                # Find the kubeconfig file for this cluster
                kubeconfig_path = f"kubeconfigs/{item.cluster_name}.kubeconfig"
                cmd_parts.extend([item.service_config.kubeconfig_flag, kubeconfig_path])

            # Execute the command
            import subprocess

            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=item.estimated_duration or 300)

            if result.returncode == 0:
                logger.info(f"Service {item.service_name} for cluster {item.cluster_name} executed successfully")
                return True
            else:
                logger.error(
                    f"Service {item.service_name} for cluster {item.cluster_name} failed with return code {result.returncode}: {result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(
                f"Service {item.service_name} for cluster {item.cluster_name} timed out after {item.estimated_duration or 300} seconds"
            )
            return False
        except Exception as e:
            logger.error(f"Service {item.service_name} for cluster {item.cluster_name} failed with exception: {e}")
            return False


class WorkerPool:
    """Manages a pool of service workers."""

    def __init__(self, max_workers: int, queue: ServiceQueue):
        """Initialize the worker pool.

        Args:
            max_workers: Maximum number of workers to create
            queue: Service queue for workers to process
        """
        self.max_workers = max_workers
        self.queue = queue
        self.workers: List[ServiceWorker] = []

    def start_workers(self) -> None:
        """Start all workers."""
        logger.info(f"Starting {self.max_workers} workers")

        for i in range(self.max_workers):
            worker = ServiceWorker(i, self.queue)
            self.workers.append(worker)
            worker.start()

        logger.info(f"Started {len(self.workers)} workers")

    def stop_workers(self) -> None:
        """Stop all workers."""
        logger.info(f"Stopping {len(self.workers)} workers")

        for worker in self.workers:
            worker.stop()

        self.workers.clear()
        logger.info("All workers stopped")

    def get_worker_status(self) -> List[Dict[str, Any]]:
        """Get status of all workers.

        Returns:
            List of dictionaries containing worker status information
        """
        status_list = []
        for worker in self.workers:
            status = {
                "worker_id": worker.worker_id,
                "is_running": worker.is_running,
                "current_item": (
                    {
                        "cluster_name": worker.current_item.cluster_name,
                        "service_name": worker.current_item.service_name,
                        "status": worker.current_item.status.value,
                    }
                    if worker.current_item
                    else None
                ),
            }
            status_list.append(status)
        return status_list
