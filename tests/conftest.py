"""Shared pytest fixtures for deployment-builder tests."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from deployment_builder.config import Config


# Performance-optimized fixtures
@pytest.fixture(scope="session")
def shared_config():
    """Shared configuration for all tests - session scoped for performance."""

    config = {
        Config.GENERAL.value: {
            Config.NAME.value: "test-deployment",
            Config.VERSION.value: "1.0.0",
            Config.ENVIRONMENT.value: "test",
            Config.PREFIX.value: "test-project",
        },
    }

    return config


@pytest.fixture(scope="session")
def shared_temp_dir():
    """Shared temporary directory for session - created once and reused."""
    temp_dir = tempfile.mkdtemp(prefix="deployment_builder_tests_")
    yield Path(temp_dir)
    # Cleanup handled by autouse fixture


@pytest.fixture
def lazy_expensive_resource():
    """Lazy-loaded expensive resource - only created when needed."""

    def _get_resource():
        # Simulate expensive resource creation
        return {"expensive_data": "value", "created_at": "now"}

    return _get_resource


@pytest.fixture(scope="session")
def performance_metrics():
    """Session-scoped performance metrics collection."""
    metrics = {"test_count": 0, "total_duration": 0.0, "slow_tests": []}
    yield metrics
    # Print performance summary at the end
    if metrics["test_count"] > 0:
        avg_duration = metrics["total_duration"] / metrics["test_count"]
        print("\nPerformance Summary:")
        print(f"Total tests: {metrics['test_count']}")
        print(f"Average duration: {avg_duration:.3f}s")
        if metrics["slow_tests"]:
            print(f"Slowest tests: {metrics['slow_tests'][:5]}")


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
    config = {
        Config.GENERAL.value: {
            Config.NAME.value: "test-deployment",
            Config.VERSION.value: "1.0.0",
            Config.ENVIRONMENT.value: "test",
            Config.PREFIX.value: "test-project",
        },
    }
    return config


# ============================================================================
# Function-scoped fixtures for test isolation
# ============================================================================


@pytest.fixture
def service_item():
    """Create a service item for testing."""
    from deployment_builder.queue import ServiceItem

    service_config = {
        "kubeconfig": {"flag": "--kubeconfig=/path/to/kubeconfig"},
        "cmd": "kubectl apply -f manifest.yaml",
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
# Benchmark Fixtures
# ============================================================================


@pytest.fixture
def temp_benchmark_dir():
    """Create a temporary directory for benchmark tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir)


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
