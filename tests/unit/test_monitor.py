"""Tests for progress monitoring and status display."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from deployment_builder.monitor import ProgressMonitor, StatusDisplay, ProgressStats, WorkerStats
from deployment_builder.queue import ServiceQueue, ServiceWorker, ServiceItem, ServiceStatus
from deployment_builder.config import ServiceConfig


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_progress_stats_creation():
    """Test creating progress stats."""
    stats = ProgressStats()
    assert stats.total_services == 0
    assert stats.completed_services == 0
    assert stats.failed_services == 0
    assert stats.completed_services == 0
    assert stats.start_time is None
    assert stats.end_time is None


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_completion_percentage():
    """Test completion percentage calculation."""
    stats = ProgressStats(total_services=10, completed_services=3, failed_services=2)
    assert stats.get_completion_percentage() == 50.0

    stats = ProgressStats(total_services=0)
    assert stats.get_completion_percentage() == 0.0


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_elapsed_time():
    """Test elapsed time calculation."""
    stats = ProgressStats()
    assert stats.get_elapsed_time() == 0.0

    start_time = datetime.now()
    stats.start_time = start_time
    time.sleep(0.1)
    elapsed = stats.get_elapsed_time()
    assert elapsed >= 0.1
    assert elapsed < 1.0


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_estimated_remaining_time():
    """Test estimated remaining time calculation."""
    stats = ProgressStats(total_services=10, completed_services=5, failed_services=0)
    stats.start_time = datetime.now() - timedelta(seconds=10)

    remaining = stats.get_estimated_remaining_time()
    assert remaining is not None
    assert remaining > 0

    # Test with no completed services
    stats.completed_services = 0
    assert stats.get_estimated_remaining_time() is None

    # Test with all services completed
    stats.completed_services = 10
    assert stats.get_estimated_remaining_time() == 0.0


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_worker_stats_creation():
    """Test creating worker stats."""
    stats = WorkerStats(worker_id=1)
    assert stats.worker_id == 1
    assert stats.is_running is False
    assert stats.current_service is None
    assert stats.current_cluster is None
    assert stats.services_completed == 0
    assert stats.services_failed == 0
    assert stats.total_work_time == 0.0
    assert stats.last_activity is None


# Using fresh_queue and mock_workers fixtures from conftest.py


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_progress_monitor_creation(fresh_queue, mock_workers):
    """Test creating progress monitor."""
    # Convert mock workers to ServiceWorker instances
    workers = [ServiceWorker(worker_id=i + 1, queue=fresh_queue) for i in range(2)]
    monitor = ProgressMonitor(fresh_queue, workers)

    assert monitor.queue == fresh_queue
    assert monitor.workers == workers
    assert monitor.monitoring is False
    assert monitor.monitor_thread is None
    assert len(monitor.worker_stats) == 2
    assert 1 in monitor.worker_stats
    assert 2 in monitor.worker_stats


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_start_stop_monitoring(fresh_queue, mock_workers):
    """Test starting and stopping monitoring."""
    # Convert mock workers to ServiceWorker instances
    workers = [ServiceWorker(worker_id=i + 1, queue=fresh_queue) for i in range(2)]
    monitor = ProgressMonitor(fresh_queue, workers)

    # Start monitoring
    monitor.start_monitoring()
    assert monitor.monitoring is True
    assert monitor.monitor_thread is not None
    assert monitor.stats.start_time is not None

    # Stop monitoring
    monitor.stop_monitoring()
    assert monitor.monitoring is False
    assert monitor.stats.end_time is not None


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_get_progress_summary(fresh_queue, mock_workers):
    """Test getting progress summary."""
    # Convert mock workers to ServiceWorker instances
    workers = [ServiceWorker(worker_id=i + 1, queue=fresh_queue) for i in range(2)]
    monitor = ProgressMonitor(fresh_queue, workers)

    # Mock queue status
    with patch.object(fresh_queue, "get_queue_status") as mock_status:
        mock_status.return_value = {
            "total_count": 10,
            "completed_count": 3,
            "failed_count": 1,
            "running_count": 2,
            "pending_count": 4,
            "retrying_count": 0,
        }

        summary = monitor.get_progress_summary()

        assert summary["total_services"] == 10
        assert summary["completed_services"] == 3
        assert summary["failed_services"] == 1
        assert summary["running_services"] == 2
        assert summary["pending_services"] == 4
        assert summary["retrying_services"] == 0
        assert summary["completion_percentage"] == 40.0
        assert summary["is_complete"] is False


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_get_worker_utilization(fresh_queue, mock_workers):
    """Test getting worker utilization."""
    # Convert mock workers to ServiceWorker instances
    workers = [ServiceWorker(worker_id=i + 1, queue=fresh_queue) for i in range(2)]
    monitor = ProgressMonitor(fresh_queue, workers)

    # Mock workers
    workers[0].is_running = True
    workers[0].current_item = MagicMock()
    workers[1].is_running = False
    workers[1].current_item = None

    utilization = monitor.get_worker_utilization()

    assert utilization["total_workers"] == 2
    assert utilization["active_workers"] == 1
    assert utilization["utilization_percentage"] == 50.0
    assert utilization["idle_workers"] == 1


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_get_estimated_completion(fresh_queue, mock_workers):
    """Test getting estimated completion time."""
    # Convert mock workers to ServiceWorker instances
    workers = [ServiceWorker(worker_id=i + 1, queue=fresh_queue) for i in range(2)]
    monitor = ProgressMonitor(fresh_queue, workers)

    # Set up stats for estimation
    monitor.stats.total_services = 10
    monitor.stats.completed_services = 5
    monitor.stats.start_time = datetime.now() - timedelta(seconds=10)

    completion = monitor.get_estimated_completion()
    assert completion is not None
    assert completion > datetime.now()


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_get_detailed_status(fresh_queue, mock_workers):
    """Test getting detailed status."""
    # Convert mock workers to ServiceWorker instances
    workers = [ServiceWorker(worker_id=i + 1, queue=fresh_queue) for i in range(2)]
    monitor = ProgressMonitor(fresh_queue, workers)

    # Mock queue status
    with patch.object(fresh_queue, "get_queue_status") as mock_status:
        mock_status.return_value = {
            "total_items": 5,
            "completed_items": 2,
            "failed_items": 0,
            "running_items": 1,
            "pending_items": 2,
            "retrying_items": 0,
        }

        details = monitor.get_detailed_status()

        assert "progress" in details
        assert "worker_utilization" in details
        assert "worker_details" in details
        assert len(details["worker_details"]) == 2
        assert details["worker_details"][0]["worker_id"] == 1
        assert details["worker_details"][1]["worker_id"] == 2


@pytest.fixture
def status_display_setup():
    """Create test setup with queue and workers for status display."""
    queue = ServiceQueue(max_workers=2)
    workers = [ServiceWorker(worker_id=i + 1, queue=queue) for i in range(2)]
    return queue, workers


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_status_display_creation(status_display_setup):
    """Test creating status display."""
    queue, workers = status_display_setup
    monitor = ProgressMonitor(queue, workers)
    display = StatusDisplay(monitor)

    assert display.monitor == monitor
    assert display.last_display_time == 0
    assert display.display_interval == 5.0


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_display_progress(status_display_setup):
    """Test displaying progress."""
    queue, workers = status_display_setup
    monitor = ProgressMonitor(queue, workers)
    display = StatusDisplay(monitor)

    # Mock monitor methods
    with (
        patch.object(monitor, "get_progress_summary") as mock_summary,
        patch.object(monitor, "get_worker_utilization") as mock_util,
    ):

        mock_summary.return_value = {
            "completion_percentage": 50.0,
            "completed_services": 5,
            "total_services": 10,
            "elapsed_time": 30.0,
        }
        mock_util.return_value = {
            "active_workers": 2,
            "total_workers": 4,
        }

        # Should not display immediately (time check)
        display.display_progress()

        # Should display after interval
        display.last_display_time = time.time() - 6.0
        with patch("builtins.print") as mock_print:
            display.display_progress()
            mock_print.assert_called_once()


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_display_worker_status(status_display_setup):
    """Test displaying worker status."""
    queue, workers = status_display_setup
    monitor = ProgressMonitor(queue, workers)
    display = StatusDisplay(monitor)

    with patch.object(monitor, "get_detailed_status") as mock_details:
        mock_details.return_value = {
            "worker_details": [
                {
                    "worker_id": 1,
                    "is_running": True,
                    "current_service": "test-service",
                    "current_cluster": "test-cluster",
                },
                {
                    "worker_id": 2,
                    "is_running": False,
                    "current_service": None,
                    "current_cluster": None,
                },
            ]
        }

        with patch("builtins.print") as mock_print:
            display.display_worker_status()
            assert mock_print.call_count >= 3  # Header + 2 workers


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_display_queue_status(status_display_setup):
    """Test displaying queue status."""
    queue, workers = status_display_setup
    monitor = ProgressMonitor(queue, workers)
    display = StatusDisplay(monitor)

    with patch.object(monitor, "get_progress_summary") as mock_summary:
        mock_summary.return_value = {
            "total_services": 10,
            "completed_services": 3,
            "failed_services": 1,
            "running_services": 2,
            "pending_services": 4,
            "retrying_services": 0,
        }

        with patch("builtins.print") as mock_print:
            display.display_queue_status()
            assert mock_print.call_count >= 7  # Header + 6 status lines


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.unit
def test_display_final_summary(status_display_setup):
    """Test displaying final summary."""
    queue, workers = status_display_setup
    monitor = ProgressMonitor(queue, workers)
    display = StatusDisplay(monitor)

    with (
        patch.object(monitor, "get_progress_summary") as mock_summary,
        patch.object(monitor, "get_worker_utilization") as mock_util,
    ):

        mock_summary.return_value = {
            "total_services": 10,
            "completed_services": 8,
            "failed_services": 1,
            "elapsed_time": 60.0,
        }
        mock_util.return_value = {
            "utilization_percentage": 75.0,
        }

        with patch("builtins.print") as mock_print:
            display.display_final_summary()
            assert mock_print.call_count >= 8  # Header + summary lines


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
def test_full_monitoring_workflow():
    """Test full monitoring workflow."""
    queue = ServiceQueue(max_workers=2)
    workers = [ServiceWorker(worker_id=i + 1, queue=queue) for i in range(2)]
    monitor = ProgressMonitor(queue, workers)

    # Add some service items first
    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    for i in range(5):
        item = ServiceItem(
            cluster_name=f"cluster-{i}",
            cluster_type="test",
            service_name=f"service-{i}",
            service_config=service_config,
        )
        queue.add_service_item(item)

    # Start monitoring after adding items
    monitor.start_monitoring()

    # Get initial status
    summary = monitor.get_progress_summary()
    assert summary["total_services"] == 5
    assert summary["pending_services"] == 5

    # Stop monitoring
    monitor.stop_monitoring()

    # Verify final state
    assert monitor.monitoring is False
    assert monitor.stats.end_time is not None
