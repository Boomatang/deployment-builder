"""Shared pytest fixtures for deployment-builder tests."""

import subprocess
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from deployment_builder.config import DeploymentConfig
from deployment_builder.queue import ServiceQueue
from deployment_builder.load_balancer import RoundRobinBalancer, LeastLoadedBalancer, PriorityBasedBalancer
from deployment_builder.monitor import ProgressMonitor, StatusDisplay
from deployment_builder.error_handler import ErrorHandler, RecoveryManager
from deployment_builder.benchmark import PerformanceBenchmark
from deployment_builder.optimization import (
    ConnectionPool, ServiceCache, BatchProcessor, ResourceOptimizer, PerformanceProfiler
)


@pytest.fixture
def examples_dir():
    """Path to the examples directory containing test configuration files."""
    return Path(__file__).parent.parent / "examples"


@pytest.fixture
def example_files():
    """List of example configuration files for testing."""
    return ["config.toml", "deployment.toml", "config.json", "deployment.yaml"]


@pytest.fixture
def cli_runner():
    """Fixture for running CLI commands with proper error handling."""

    def _run_command(command_args, expect_success=True):
        cmd = ["poetry", "run", "deploy"] + command_args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        if expect_success:
            assert result.returncode == 0, f"Command failed: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        else:
            assert result.returncode != 0, f"Command should have failed but succeeded: {cmd}\nSTDOUT: {result.stdout}"

        return result

    return _run_command


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "general": {"name": "test-deployment", "version": "1.0.0", "environment": "test", "prefix": "test-project"},
        "clusters": {"primary": {"count": 1}, "secondary": {"count": 0}},
    }


# ============================================================================
# Session-scoped fixtures for expensive, immutable resources
# ============================================================================

@pytest.fixture(scope="session")
def shared_config():
    """Shared configuration for all tests."""
    config = DeploymentConfig()
    config.general.name = "test-deployment"
    config.general.version = "1.0.0"
    config.general.environment = "test"
    config.general.prefix = "test-project"
    return config


# ============================================================================
# Function-scoped fixtures for test isolation
# ============================================================================

@pytest.fixture
def fresh_queue():
    """Fresh queue instance for each test."""
    return ServiceQueue(max_workers=2)


@pytest.fixture
def fresh_queue_large():
    """Fresh queue instance with more workers for load testing."""
    return ServiceQueue(max_workers=10)


@pytest.fixture
def service_item():
    """Create a service item for testing."""
    from deployment_builder.queue import ServiceItem
    
    service_config = {
        "kubeconfig": {"flag": "--kubeconfig=/path/to/kubeconfig"},
        "cmd": "kubectl apply -f manifest.yaml"
    }
    
    return ServiceItem(
        cluster_name="test-cluster",
        cluster_type="worker",
        service_name="test-service",
        service_config=service_config,
    )


@pytest.fixture
def mock_workers():
    """Create mock workers for testing."""
    workers = []
    for i in range(5):
        worker = MagicMock()
        worker.worker_id = f"worker_{i}"
        worker.active_tasks = 0
        worker.total_tasks = 0
        workers.append(worker)
    return workers


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    services = []
    for i in range(10):
        service = MagicMock()
        service.cluster_type = f"type{i % 3}"
        service.service_type = f"service{i % 2}"
        service.priority = i % 5
        service.service_name = f"service_{i}"
        service.cluster_name = f"cluster_{i % 3}"
        services.append(service)
    return services


# ============================================================================
# Load Balancer Fixtures
# ============================================================================

@pytest.fixture
def round_robin_balancer():
    """Create a round-robin load balancer."""
    return RoundRobinBalancer()


@pytest.fixture
def least_loaded_balancer():
    """Create a least-loaded load balancer."""
    return LeastLoadedBalancer()


@pytest.fixture
def priority_balancer():
    """Create a priority-based load balancer."""
    return PriorityBasedBalancer()


# ============================================================================
# Monitor Fixtures
# ============================================================================

@pytest.fixture
def progress_monitor(fresh_queue):
    """Create a progress monitor with a fresh queue."""
    return ProgressMonitor(fresh_queue)


@pytest.fixture
def status_display(fresh_queue):
    """Create a status display with a fresh queue."""
    return StatusDisplay(fresh_queue)


# ============================================================================
# Error Handler Fixtures
# ============================================================================

@pytest.fixture
def error_handler(fresh_queue):
    """Create an error handler with a fresh queue."""
    return ErrorHandler(fresh_queue)


@pytest.fixture
def recovery_manager(fresh_queue):
    """Create a recovery manager with a fresh queue."""
    error_handler = ErrorHandler(fresh_queue)
    return RecoveryManager(error_handler)


# ============================================================================
# Benchmark Fixtures
# ============================================================================

@pytest.fixture
def temp_benchmark_dir():
    """Create a temporary directory for benchmark tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def performance_benchmark(temp_benchmark_dir):
    """Create a performance benchmark with temporary directory."""
    return PerformanceBenchmark(temp_benchmark_dir)


# ============================================================================
# Optimization Fixtures
# ============================================================================

@pytest.fixture
def connection_pool():
    """Create a fresh connection pool."""
    return ConnectionPool()


@pytest.fixture
def service_cache():
    """Create a fresh service cache."""
    return ServiceCache()


@pytest.fixture
def batch_processor():
    """Create a fresh batch processor."""
    return BatchProcessor()


@pytest.fixture
def resource_optimizer():
    """Create a fresh resource optimizer."""
    return ResourceOptimizer()


@pytest.fixture
def performance_profiler():
    """Create a fresh performance profiler."""
    return PerformanceProfiler()


# ============================================================================
# Autouse fixtures for automatic cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_global_resources():
    """Automatically cleanup global resources after each test."""
    yield
    # Cleanup global optimization resources
    try:
        from deployment_builder.optimization import cleanup_optimization_resources
        cleanup_optimization_resources()
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def reset_threading():
    """Reset threading state after each test."""
    yield
    # Ensure all threads are cleaned up
    import threading
    for thread in threading.enumerate():
        if thread != threading.current_thread() and thread.is_alive():
            thread.join(timeout=1.0)


# ============================================================================
# Parametrized fixtures for testing multiple scenarios
# ============================================================================

@pytest.fixture(params=[1, 2, 5, 10])
def queue_worker_count(request):
    """Parametrized fixture for different queue worker counts."""
    return request.param


@pytest.fixture(params=["round_robin", "least_loaded", "priority"])
def load_balancer_type(request):
    """Parametrized fixture for different load balancer types."""
    return request.param


@pytest.fixture(params=[0.1, 0.5, 1.0, 2.0])
def timeout_value(request):
    """Parametrized fixture for different timeout values."""
    return request.param


# ============================================================================
# Composite fixtures
# ============================================================================

@pytest.fixture
def complete_test_setup(fresh_queue, error_handler, progress_monitor, connection_pool):
    """Complete test setup with all major components."""
    return {
        "queue": fresh_queue,
        "error_handler": error_handler,
        "progress_monitor": progress_monitor,
        "connection_pool": connection_pool,
    }


@pytest.fixture
def optimization_test_setup(resource_optimizer, performance_profiler, service_cache, batch_processor):
    """Complete optimization test setup."""
    return {
        "optimizer": resource_optimizer,
        "profiler": performance_profiler,
        "cache": service_cache,
        "batch_processor": batch_processor,
    }
