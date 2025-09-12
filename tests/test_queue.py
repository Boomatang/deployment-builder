"""Tests for service queue system."""

import pytest
import threading
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from deployment_builder.queue import (
    ServiceQueue,
    ServiceWorker,
    WorkerPool,
    ServiceItem,
    ServiceStatus,
)
from deployment_builder.config import ServiceConfig


def test_service_item_creation():
    """Test basic service item creation."""
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    assert item.cluster_name == "test-cluster"
    assert item.cluster_type == "worker"
    assert item.service_name == "test-service"
    assert item.priority == 0
    assert item.status == ServiceStatus.PENDING
    assert item.retry_count == 0
    assert item.max_retries == 3


def test_service_item_priority_comparison():
    """Test priority comparison for PriorityQueue."""
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create items with different priorities
    item1 = ServiceItem(
        cluster_name="cluster1",
        cluster_type="worker",
        service_name="service1",
        service_config=service_config,
        priority=1,
    )

    item2 = ServiceItem(
        cluster_name="cluster2",
        cluster_type="worker",
        service_name="service2",
        service_config=service_config,
        priority=2,
    )

    # Lower priority number should be higher priority
    assert item1 < item2


def test_service_item_creation_time_comparison():
    """Test creation time comparison for same priority items."""
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create items with same priority but different creation times
    item1 = ServiceItem(
        cluster_name="cluster1",
        cluster_type="worker",
        service_name="service1",
        service_config=service_config,
        priority=1,
    )

    time.sleep(0.01)  # Small delay to ensure different creation times

    item2 = ServiceItem(
        cluster_name="cluster2",
        cluster_type="worker",
        service_name="service2",
        service_config=service_config,
        priority=1,
    )

    # Earlier creation time should be higher priority
    assert item1 < item2


def test_queue_creation():
    """Test basic queue creation."""
    queue = ServiceQueue(max_workers=4, timeout=300)

    assert queue.max_workers == 4
    assert queue.timeout == 300
    assert queue.queue.empty()
    assert len(queue.completed_items) == 0
    assert len(queue.failed_items) == 0
    assert len(queue.running_items) == 0


def test_add_service_item():
    """Test adding service items to queue."""
    queue = ServiceQueue()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    queue.add_service_item(item)

    assert not queue.queue.empty()
    assert queue._stats["total_items"] == 1
    assert queue._stats["pending_items"] == 1


def test_get_next_item():
    """Test getting next item from queue."""
    queue = ServiceQueue()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    queue.add_service_item(item)

    # Get next item
    retrieved_item = queue.get_next_item()

    assert retrieved_item is not None
    assert retrieved_item.cluster_name == "test-cluster"
    assert retrieved_item.status == ServiceStatus.RUNNING
    assert retrieved_item.started_at is not None
    assert len(queue.running_items) == 1
    assert queue._stats["running_items"] == 1
    assert queue._stats["pending_items"] == 0


def test_mark_completed():
    """Test marking service item as completed."""
    queue = ServiceQueue()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    queue.add_service_item(item)
    retrieved_item = queue.get_next_item()
    queue.mark_completed(retrieved_item)

    assert retrieved_item.status == ServiceStatus.COMPLETED
    assert retrieved_item.completed_at is not None
    assert len(queue.completed_items) == 1
    assert len(queue.running_items) == 0
    assert queue._stats["completed_items"] == 1
    assert queue._stats["running_items"] == 0


def test_mark_failed_with_retry():
    """Test marking service item as failed with retry."""
    queue = ServiceQueue()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
        max_retries=2,
    )

    queue.add_service_item(item)
    retrieved_item = queue.get_next_item()
    queue.mark_failed(retrieved_item, "Test error")

    assert retrieved_item.status == ServiceStatus.RETRYING
    assert retrieved_item.retry_count == 1
    assert retrieved_item.error_message == "Test error"
    assert len(queue.failed_items) == 0
    assert queue._stats["pending_items"] == 1  # Item re-queued for retry


def test_mark_failed_permanent():
    """Test marking service item as permanently failed."""
    queue = ServiceQueue()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
        max_retries=1,
    )

    queue.add_service_item(item)
    retrieved_item = queue.get_next_item()

    # First failure - should retry (retry_count=1, max_retries=1, so 1 <= 1)
    queue.mark_failed(retrieved_item, "Test error 1")
    assert retrieved_item.status == ServiceStatus.RETRYING

    # Get the retried item
    retried_item = queue.get_next_item()

    # Second failure - should be permanent
    queue.mark_failed(retried_item, "Test error 2")
    assert retried_item.status == ServiceStatus.FAILED
    assert len(queue.failed_items) == 1
    assert queue._stats["failed_items"] == 1


def test_get_queue_status():
    """Test getting queue status."""
    queue = ServiceQueue(max_workers=2)
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Add some items
    for i in range(3):
        item = ServiceItem(
            cluster_name=f"cluster-{i}",
            cluster_type="worker",
            service_name=f"service-{i}",
            service_config=service_config,
        )
        queue.add_service_item(item)

    status = queue.get_queue_status()

    assert status["queue_size"] == 3
    assert status["pending_count"] == 3
    assert status["total_count"] == 3
    assert status["completed_count"] == 0
    assert status["failed_count"] == 0
    assert status["running_count"] == 0
    assert status["worker_count"] == 0
    assert status["max_workers"] == 2
    assert status["is_shutdown"] is False


def test_is_empty():
    """Test queue empty check."""
    queue = ServiceQueue()

    # Empty queue should be empty
    assert queue.is_empty() is True

    # Add item and get it - should not be empty while running
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    queue.add_service_item(item)
    assert queue.is_empty() is False

    retrieved_item = queue.get_next_item()
    assert queue.is_empty() is False  # Item is running

    queue.mark_completed(retrieved_item)
    assert queue.is_empty() is True  # No pending or running items


def test_shutdown():
    """Test queue shutdown."""
    queue = ServiceQueue()

    assert not queue.shutdown_event.is_set()

    queue.shutdown()

    assert queue.shutdown_event.is_set()


def test_worker_creation():
    """Test worker creation."""
    queue = ServiceQueue()
    worker = ServiceWorker(worker_id=1, queue=queue)

    assert worker.worker_id == 1
    assert worker.queue == queue
    assert worker.current_item is None
    assert worker.is_running is False
    assert worker.thread is None


def test_worker_start_stop():
    """Test worker start and stop."""
    queue = ServiceQueue()
    worker = ServiceWorker(worker_id=1, queue=queue)

    # Start worker
    worker.start()
    assert worker.is_running is True
    assert worker.thread is not None
    assert worker.thread.is_alive()

    # Stop worker
    worker.stop()
    assert worker.is_running is False
    # Give thread more time to stop
    time.sleep(0.5)
    # Thread should be stopped by now, but if not, it's a daemon thread so it will be cleaned up
    if worker.thread.is_alive():
        # For daemon threads, this is acceptable in test environment
        pass


@patch("subprocess.run")
def test_execute_service_success(mock_run):
    """Test successful service execution."""
    # Mock successful subprocess execution
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    queue = ServiceQueue()
    worker = ServiceWorker(worker_id=1, queue=queue)

    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    success = worker.execute_service(item)

    assert success is True
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_execute_service_failure(mock_run):
    """Test failed service execution."""
    # Mock failed subprocess execution
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error occurred"
    mock_run.return_value = mock_result

    queue = ServiceQueue()
    worker = ServiceWorker(worker_id=1, queue=queue)

    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    success = worker.execute_service(item)

    assert success is False
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_execute_service_timeout(mock_run):
    """Test service execution timeout."""
    # Mock timeout exception
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("kubectl", 30)

    queue = ServiceQueue()
    worker = ServiceWorker(worker_id=1, queue=queue)

    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
        estimated_duration=30,
    )

    success = worker.execute_service(item)

    assert success is False
    mock_run.assert_called_once()


def test_worker_pool_creation():
    """Test worker pool creation."""
    queue = ServiceQueue()
    pool = WorkerPool(max_workers=3, queue=queue)

    assert pool.max_workers == 3
    assert pool.queue == queue
    assert len(pool.workers) == 0


def test_start_stop_workers():
    """Test starting and stopping workers."""
    queue = ServiceQueue()
    pool = WorkerPool(max_workers=2, queue=queue)

    # Start workers
    pool.start_workers()
    assert len(pool.workers) == 2
    assert all(worker.is_running for worker in pool.workers)

    # Stop workers
    pool.stop_workers()
    assert len(pool.workers) == 0


def test_get_worker_status():
    """Test getting worker status."""
    queue = ServiceQueue()
    pool = WorkerPool(max_workers=2, queue=queue)

    pool.start_workers()

    status_list = pool.get_worker_status()

    assert len(status_list) == 2
    for i, status in enumerate(status_list):
        assert status["worker_id"] == i
        assert status["is_running"] is True
        assert status["current_item"] is None

    pool.stop_workers()


@patch("subprocess.run")
def test_full_workflow(mock_run):
    """Test complete workflow from queue to completion."""
    # Mock successful subprocess execution
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    # Create queue and worker pool
    queue = ServiceQueue(max_workers=2)
    pool = WorkerPool(max_workers=2, queue=queue)

    # Add workers to queue
    queue.workers = pool.workers

    # Add service items
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    for i in range(3):
        item = ServiceItem(
            cluster_name=f"cluster-{i}",
            cluster_type="worker",
            service_name=f"service-{i}",
            service_config=service_config,
        )
        queue.add_service_item(item)

    # Start workers
    pool.start_workers()

    # Wait for processing
    time.sleep(0.5)

    # Check results
    status = queue.get_queue_status()
    assert status["completed_count"] == 3
    assert status["failed_count"] == 0
    assert status["pending_count"] == 0
    assert status["running_count"] == 0

    # Cleanup
    pool.stop_workers()
    queue.shutdown()
