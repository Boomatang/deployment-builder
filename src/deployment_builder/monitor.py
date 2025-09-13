"""Progress monitoring and status display for service queue system."""

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .logging_config import get_logger
from .queue import ServiceQueue, ServiceWorker

logger = get_logger()


@dataclass
class ProgressStats:
    """Progress statistics for monitoring."""

    total_services: int = 0
    completed_services: int = 0
    failed_services: int = 0
    running_services: int = 0
    pending_services: int = 0
    retrying_services: int = 0

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def get_completion_percentage(self) -> float:
        """Get completion percentage."""
        if self.total_services == 0:
            return 0.0
        return (self.completed_services + self.failed_services) / self.total_services * 100

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()

    def get_estimated_remaining_time(self) -> Optional[float]:
        """Get estimated remaining time in seconds."""
        if self.completed_services == 0 or self.start_time is None:
            return None

        elapsed = self.get_elapsed_time()
        remaining_services = self.total_services - self.completed_services - self.failed_services

        if remaining_services <= 0:
            return 0.0

        # Estimate based on average time per service
        avg_time_per_service = elapsed / self.completed_services
        return remaining_services * avg_time_per_service


@dataclass
class WorkerStats:
    """Worker statistics for monitoring."""

    worker_id: int
    is_running: bool = False
    current_service: Optional[str] = None
    current_cluster: Optional[str] = None
    services_completed: int = 0
    services_failed: int = 0
    total_work_time: float = 0.0
    last_activity: Optional[datetime] = None


class ProgressMonitor:
    """Monitor progress of service execution."""

    def __init__(self, queue: ServiceQueue, workers: List[ServiceWorker]):
        """Initialize progress monitor.

        Args:
            queue: Service queue to monitor
            workers: List of workers to monitor
        """
        self.queue = queue
        self.workers = workers
        self.stats = ProgressStats()
        self.worker_stats: Dict[int, WorkerStats] = {}
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Initialize worker stats
        for worker in workers:
            self.worker_stats[worker.worker_id] = WorkerStats(worker_id=worker.worker_id)

    def start_monitoring(self) -> None:
        """Start progress monitoring."""
        if self.monitoring:
            return

        self.monitoring = True
        self.stop_event.clear()
        self.stats.start_time = datetime.now()

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("Started progress monitoring")

    def stop_monitoring(self) -> None:
        """Stop progress monitoring."""
        if not self.monitoring:
            return

        self.monitoring = False
        self.stop_event.set()
        self.stats.end_time = datetime.now()

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        logger.info("Stopped progress monitoring")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self.stop_event.is_set():
            try:
                self._update_stats()
                time.sleep(1.0)  # Update every second
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                break

    def _update_stats(self) -> None:
        """Update progress statistics."""
        # Update queue stats
        queue_status = self.queue.get_queue_status()
        self.stats.total_services = queue_status.get("total_count", 0)
        self.stats.completed_services = queue_status.get("completed_count", 0)
        self.stats.failed_services = queue_status.get("failed_count", 0)
        self.stats.running_services = queue_status.get("running_count", 0)
        self.stats.pending_services = queue_status.get("pending_count", 0)
        self.stats.retrying_services = queue_status.get("retrying_count", 0)

        # Update total services from queue if not set
        if self.stats.total_services == 0:
            self.stats.total_services = (
                len(self.queue.completed_items)
                + len(self.queue.failed_items)
                + len(self.queue.running_items)
                + self.queue.queue.qsize()
            )

        # Update worker stats
        for worker in self.workers:
            worker_stat = self.worker_stats[worker.worker_id]
            worker_stat.is_running = worker.is_running
            worker_stat.current_service = worker.current_item.service_name if worker.current_item else None
            worker_stat.current_cluster = worker.current_item.cluster_name if worker.current_item else None

            if worker.current_item:
                worker_stat.last_activity = datetime.now()

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary.

        Returns:
            Dictionary with progress information
        """
        self._update_stats()

        return {
            "total_services": self.stats.total_services,
            "completed_services": self.stats.completed_services,
            "failed_services": self.stats.failed_services,
            "running_services": self.stats.running_services,
            "pending_services": self.stats.pending_services,
            "retrying_services": self.stats.retrying_services,
            "completion_percentage": self.stats.get_completion_percentage(),
            "elapsed_time": self.stats.get_elapsed_time(),
            "estimated_remaining_time": self.stats.get_estimated_remaining_time(),
            "is_complete": self.stats.completed_services + self.stats.failed_services >= self.stats.total_services,
        }

    def get_worker_utilization(self) -> Dict[str, float]:
        """Get worker utilization statistics.

        Returns:
            Dictionary with worker utilization info
        """
        self._update_stats()

        total_workers = len(self.workers)
        active_workers = sum(1 for worker in self.workers if worker.is_running and worker.current_item)

        return {
            "total_workers": total_workers,
            "active_workers": active_workers,
            "utilization_percentage": (active_workers / total_workers * 100) if total_workers > 0 else 0.0,
            "idle_workers": total_workers - active_workers,
        }

    def get_estimated_completion(self) -> Optional[datetime]:
        """Estimate completion time.

        Returns:
            Estimated completion datetime or None if cannot estimate
        """
        remaining_time = self.stats.get_estimated_remaining_time()
        if remaining_time is None:
            return None

        return datetime.now() + timedelta(seconds=remaining_time)

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status information.

        Returns:
            Dictionary with detailed status
        """
        self._update_stats()

        # Worker details
        worker_details = []
        for worker in self.workers:
            worker_stat = self.worker_stats[worker.worker_id]
            worker_details.append(
                {
                    "worker_id": worker_stat.worker_id,
                    "is_running": worker_stat.is_running,
                    "current_service": worker_stat.current_service,
                    "current_cluster": worker_stat.current_cluster,
                    "services_completed": worker_stat.services_completed,
                    "services_failed": worker_stat.services_failed,
                    "last_activity": worker_stat.last_activity.isoformat() if worker_stat.last_activity else None,
                }
            )

        return {
            "progress": self.get_progress_summary(),
            "worker_utilization": self.get_worker_utilization(),
            "worker_details": worker_details,
            "estimated_completion": (
                self.get_estimated_completion().isoformat() if self.get_estimated_completion() else None
            ),
        }


class StatusDisplay:
    """Display status information during execution."""

    def __init__(self, monitor: ProgressMonitor):
        """Initialize status display.

        Args:
            monitor: Progress monitor to display status for
        """
        self.monitor = monitor
        self.last_display_time = 0
        self.display_interval = 5.0  # Display every 5 seconds

    def display_progress(self) -> None:
        """Display current progress."""
        current_time = time.time()
        if current_time - self.last_display_time < self.display_interval:
            return

        self.last_display_time = current_time

        summary = self.monitor.get_progress_summary()
        utilization = self.monitor.get_worker_utilization()

        # Clear line and display progress
        print(
            f"\rProgress: {summary['completion_percentage']:.1f}% "
            f"({summary['completed_services']}/{summary['total_services']}) "
            f"| Workers: {utilization['active_workers']}/{utilization['total_workers']} "
            f"| Elapsed: {summary['elapsed_time']:.1f}s",
            end="",
            flush=True,
        )

    def display_worker_status(self) -> None:
        """Display worker status."""
        details = self.monitor.get_detailed_status()

        print("\nWorker Status:")
        print("-" * 50)
        for worker in details["worker_details"]:
            status = "RUNNING" if worker["is_running"] else "IDLE"
            current = (
                f" ({worker['current_service']} on {worker['current_cluster']})" if worker["current_service"] else ""
            )
            print(f"Worker {worker['worker_id']}: {status}{current}")

    def display_queue_status(self) -> None:
        """Display queue status."""
        summary = self.monitor.get_progress_summary()

        print("\nQueue Status:")
        print("-" * 30)
        print(f"Total: {summary['total_services']}")
        print(f"Completed: {summary['completed_services']}")
        print(f"Failed: {summary['failed_services']}")
        print(f"Running: {summary['running_services']}")
        print(f"Pending: {summary['pending_services']}")
        print(f"Retrying: {summary['retrying_services']}")

    def display_final_summary(self) -> None:
        """Display final execution summary."""
        summary = self.monitor.get_progress_summary()
        utilization = self.monitor.get_worker_utilization()

        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total services: {summary['total_services']}")
        print(f"Completed: {summary['completed_services']}")
        print(f"Failed: {summary['failed_services']}")
        print(f"Success rate: {summary['completed_services'] / summary['total_services'] * 100:.1f}%")
        print(f"Total time: {summary['elapsed_time']:.1f} seconds")
        print(f"Worker utilization: {utilization['utilization_percentage']:.1f}%")
        print("=" * 60)
