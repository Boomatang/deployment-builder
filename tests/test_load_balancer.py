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


class TestRoundRobinBalancer:
    """Test RoundRobinBalancer functionality."""

    def test_round_robin_selection(self):
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

    def test_round_robin_with_non_running_workers(self):
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

    def test_round_robin_no_workers(self):
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

    def test_round_robin_no_running_workers(self):
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


class TestLeastLoadedBalancer:
    """Test LeastLoadedBalancer functionality."""

    def test_least_loaded_idle_workers(self):
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

    def test_least_loaded_all_busy(self):
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

    def test_least_loaded_no_workers(self):
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


class TestPriorityBasedBalancer:
    """Test PriorityBasedBalancer functionality."""

    def test_priority_based_high_priority_idle(self):
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

    def test_priority_based_normal_priority(self):
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

    def test_priority_based_default_balancer(self):
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


class TestCreateLoadBalancer:
    """Test load balancer factory function."""

    def test_create_round_robin_balancer(self):
        """Test creating round-robin balancer."""
        balancer = create_load_balancer("round_robin")
        assert isinstance(balancer, RoundRobinBalancer)

    def test_create_least_loaded_balancer(self):
        """Test creating least loaded balancer."""
        balancer = create_load_balancer("least_loaded")
        assert isinstance(balancer, LeastLoadedBalancer)

    def test_create_priority_based_balancer(self):
        """Test creating priority-based balancer."""
        balancer = create_load_balancer("priority_based")
        assert isinstance(balancer, PriorityBasedBalancer)

    def test_create_unsupported_balancer(self):
        """Test creating unsupported balancer."""
        with pytest.raises(ValueError, match="Unsupported load balancing strategy"):
            create_load_balancer("unsupported_strategy")

    def test_create_balancer_case_sensitive(self):
        """Test that balancer creation is case sensitive."""
        with pytest.raises(ValueError, match="Unsupported load balancing strategy"):
            create_load_balancer("ROUND_ROBIN")  # Should be lowercase


class TestLoadBalancerIntegration:
    """Integration tests for load balancers."""

    def test_round_robin_with_real_workers(self):
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

    def test_least_loaded_with_real_workers(self):
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
