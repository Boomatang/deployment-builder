"""Tests for load balancing strategies."""

import pytest
from unittest.mock import MagicMock

from deployment_builder.load_balancer import (
    LoadBalancer,
    RoundRobinBalancer,
    LeastLoadedBalancer,
    PriorityBasedBalancer,
    create_load_balancer,
)
from deployment_builder.queue import ServiceWorker, ServiceItem, ServiceStatus
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
def test_round_robin_selection():
    """Test round-robin worker selection."""
    balancer = RoundRobinBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = True
        workers.append(worker)

    # Create service item
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    # Test round-robin selection
    selected_workers = []
    for _ in range(6):  # Test multiple selections
        selected_worker = balancer.select_worker(item, workers)
        selected_workers.append(selected_worker.worker_id)

    # Should cycle through workers: 0, 1, 2, 0, 1, 2
    expected = [0, 1, 2, 0, 1, 2]
    assert selected_workers == expected


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
def test_round_robin_with_non_running_workers():
    """Test round-robin selection with some non-running workers."""
    balancer = RoundRobinBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers (only first two are running)
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = i < 2  # Only first two are running
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    # Test round-robin selection
    selected_workers = []
    for _ in range(4):  # Test multiple selections
        selected_worker = balancer.select_worker(item, workers)
        selected_workers.append(selected_worker.worker_id)

    # Should cycle through only running workers: 0, 1, 0, 1
    expected = [0, 1, 0, 1]
    assert selected_workers == expected


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
def test_round_robin_no_workers():
    """Test round-robin selection with no workers."""
    balancer = RoundRobinBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    with pytest.raises(ValueError, match="No workers available"):
        balancer.select_worker(item, [])


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
def test_round_robin_no_running_workers():
    """Test round-robin selection with no running workers."""
    balancer = RoundRobinBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers (none are running)
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = False
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    with pytest.raises(ValueError, match="No running workers available"):
        balancer.select_worker(item, workers)


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
def test_least_loaded_idle_workers():
    """Test least loaded selection with idle workers."""
    balancer = LeastLoadedBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers (some idle, some busy)
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = True
        worker.current_item = None if i == 0 else MagicMock()  # First worker is idle
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    # Should select the idle worker
    selected_worker = balancer.select_worker(item, workers)
    assert selected_worker.worker_id == 0


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
def test_least_loaded_all_busy():
    """Test least loaded selection when all workers are busy."""
    balancer = LeastLoadedBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers (all busy)
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = True
        worker.current_item = MagicMock()  # All workers are busy
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    # Should select the first available worker
    selected_worker = balancer.select_worker(item, workers)
    assert selected_worker.worker_id == 0


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
def test_least_loaded_no_workers():
    """Test least loaded selection with no workers."""
    balancer = LeastLoadedBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    with pytest.raises(ValueError, match="No workers available"):
        balancer.select_worker(item, [])


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
def test_priority_based_high_priority_idle():
    """Test priority-based selection for high priority items with idle workers."""
    base_balancer = RoundRobinBalancer()
    balancer = PriorityBasedBalancer(base_balancer=base_balancer)
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers (some idle, some busy)
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = True
        worker.current_item = None if i == 0 else MagicMock()  # First worker is idle
        workers.append(worker)

    # High priority item (priority < 5)
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
        priority=3,
    )

    # Should select idle worker for high priority item
    selected_worker = balancer.select_worker(item, workers)
    assert selected_worker.worker_id == 0


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
def test_priority_based_normal_priority():
    """Test priority-based selection for normal priority items."""
    base_balancer = RoundRobinBalancer()
    balancer = PriorityBasedBalancer(base_balancer=base_balancer)
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = True
        worker.current_item = MagicMock()  # All workers are busy
        workers.append(worker)

    # Normal priority item (priority >= 5)
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
        priority=5,
    )

    # Should use base balancer (round-robin)
    selected_worker = balancer.select_worker(item, workers)
    assert selected_worker.worker_id == 0  # First in round-robin


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
def test_priority_based_default_balancer():
    """Test priority-based balancer with default base balancer."""
    balancer = PriorityBasedBalancer()  # No base balancer specified
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create mock workers
    workers = []
    for i in range(3):
        worker = MagicMock()
        worker.worker_id = i
        worker.is_running = True
        worker.current_item = None
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
        priority=5,
    )

    # Should work with default round-robin balancer
    selected_worker = balancer.select_worker(item, workers)
    assert selected_worker.worker_id == 0


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
def test_create_round_robin_balancer():
    """Test creating round-robin balancer."""
    balancer = create_load_balancer("round_robin")
    assert isinstance(balancer, RoundRobinBalancer)


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
def test_create_least_loaded_balancer():
    """Test creating least loaded balancer."""
    balancer = create_load_balancer("least_loaded")
    assert isinstance(balancer, LeastLoadedBalancer)


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
def test_create_priority_based_balancer():
    """Test creating priority-based balancer."""
    balancer = create_load_balancer("priority_based")
    assert isinstance(balancer, PriorityBasedBalancer)


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
def test_create_unsupported_balancer():
    """Test creating unsupported balancer."""
    with pytest.raises(ValueError, match="Unsupported load balancing strategy"):
        create_load_balancer("unsupported_strategy")


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
def test_create_balancer_case_sensitive():
    """Test that balancer creation is case sensitive."""
    with pytest.raises(ValueError, match="Unsupported load balancing strategy"):
        create_load_balancer("ROUND_ROBIN")  # Should be lowercase


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
def test_round_robin_with_real_workers():
    """Test round-robin balancer with real worker objects."""
    balancer = RoundRobinBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create real worker objects
    from deployment_builder.queue import ServiceQueue

    queue = ServiceQueue()
    workers = []
    for i in range(3):
        worker = ServiceWorker(i, queue)
        worker.is_running = True
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    # Test multiple selections
    selected_workers = []
    for _ in range(6):
        selected_worker = balancer.select_worker(item, workers)
        selected_workers.append(selected_worker.worker_id)

    # Should cycle through workers: 0, 1, 2, 0, 1, 2
    expected = [0, 1, 2, 0, 1, 2]
    assert selected_workers == expected


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
def test_least_loaded_with_real_workers():
    """Test least loaded balancer with real worker objects."""
    balancer = LeastLoadedBalancer()
    service_config = ServiceConfig(cmd="kubectl get pods", kubeconfig_flag="--kubeconfig")

    # Create real worker objects
    from deployment_builder.queue import ServiceQueue

    queue = ServiceQueue()
    workers = []
    for i in range(3):
        worker = ServiceWorker(i, queue)
        worker.is_running = True
        worker.current_item = None if i == 0 else MagicMock()  # First worker is idle
        workers.append(worker)

    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )

    # Should select the idle worker
    selected_worker = balancer.select_worker(item, workers)
    assert selected_worker.worker_id == 0
