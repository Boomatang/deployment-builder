"""
Tests for the benchmark module.

This module tests the performance benchmarking and validation tools
for the service queue system.
"""

import pytest
import time
import tempfile
import shutil
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from datetime import datetime

from deployment_builder.benchmark import (
    BenchmarkResult,
    LoadTestConfig,
    PerformanceBenchmark,
    SystemValidator,
    get_benchmark,
    get_validator,
    run_full_validation,
)
from deployment_builder.queue import ServiceQueue, ServiceItem, ServiceStatus, ServiceConfig
from deployment_builder.config import DeploymentConfig


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
def test_benchmark_result_creation():
    """Test creating benchmark result."""
    result = BenchmarkResult(
        test_name="test_benchmark",
        duration=10.5,
        success_count=100,
        failure_count=5,
        total_operations=105,
        throughput=10.0,
        average_latency=1.0,
        min_latency=0.5,
        max_latency=2.0,
        p50_latency=1.0,
        p95_latency=1.8,
        p99_latency=1.9,
        memory_usage=50.0,
        cpu_usage=25.0,
        error_rate=0.05,
    )

    assert result.test_name == "test_benchmark"
    assert result.duration == 10.5
    assert result.success_count == 100
    assert result.failure_count == 5
    assert result.total_operations == 105
    assert result.throughput == 10.0
    assert result.average_latency == 1.0
    assert result.min_latency == 0.5
    assert result.max_latency == 2.0
    assert result.p50_latency == 1.0
    assert result.p95_latency == 1.8
    assert result.p99_latency == 1.9
    assert result.memory_usage == 50.0
    assert result.cpu_usage == 25.0
    assert result.error_rate == 0.05
    assert isinstance(result.timestamp, datetime)
    assert result.metadata == {}


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
def test_benchmark_result_defaults():
    """Test benchmark result with default values."""
    result = BenchmarkResult(
        test_name="test",
        duration=1.0,
        success_count=1,
        failure_count=0,
        total_operations=1,
        throughput=1.0,
        average_latency=1.0,
        min_latency=1.0,
        max_latency=1.0,
        p50_latency=1.0,
        p95_latency=1.0,
        p99_latency=1.0,
        memory_usage=1.0,
        cpu_usage=1.0,
        error_rate=0.0,
    )

    assert isinstance(result.timestamp, datetime)
    assert result.metadata == {}


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.config
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.unit
def test_load_test_config_creation():
    """Test creating load test config."""
    config = LoadTestConfig()

    assert config.num_services == 100
    assert config.num_workers == 4
    assert config.service_duration == 1.0
    assert config.failure_rate == 0.1
    assert config.load_balancer == "round_robin"
    assert config.batch_size == 5
    assert config.timeout == 30.0
    assert config.warmup_duration == 5.0
    assert config.test_duration == 60.0
    assert config.ramp_up_duration == 10.0
    assert config.ramp_down_duration == 10.0


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.config
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.unit
@pytest.mark.config
@pytest.mark.unit
def test_load_test_config_custom():
    """Test load test config with custom values."""
    config = LoadTestConfig(
        num_services=200,
        num_workers=8,
        service_duration=2.0,
        failure_rate=0.2,
        load_balancer="least_loaded",
        batch_size=10,
        timeout=60.0,
    )

    assert config.num_services == 200
    assert config.num_workers == 8
    assert config.service_duration == 2.0
    assert config.failure_rate == 0.2
    assert config.load_balancer == "least_loaded"
    assert config.batch_size == 10
    assert config.timeout == 60.0


# Using performance_benchmark and temp_benchmark_dir fixtures from conftest.py


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
def test_benchmark_creation(performance_benchmark, temp_benchmark_dir):
    """Test creating performance benchmark."""
    assert performance_benchmark.output_dir == Path(temp_benchmark_dir)
    assert performance_benchmark.results == []
    assert performance_benchmark._lock is not None


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
def test_create_test_services(performance_benchmark):
    """Test creating test services."""

    services = performance_benchmark._create_test_services(5, 1.0)

    assert len(services) == 5
    for i, service in enumerate(services):
        assert service.service_name == f"service_{i}"
        assert service.cluster_name == f"test-cluster-service_{i}"
        assert service.cluster_type == "test"
        assert service.estimated_duration == 1.0

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
def test_create_test_service_with_failure(performance_benchmark):
    """Test creating test service with failure."""

    service = performance_benchmark._create_test_service("test_service", 1.0, True)

    assert service.service_name == "test_service"
    assert service.cluster_name == "test-cluster-test_service"
    assert service.cluster_type == "test"
    assert service.estimated_duration == 1.0
    assert service.service_config.cmd == "false"  # Should fail

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
def test_create_test_service_without_failure(performance_benchmark):
    """Test creating test service without failure."""

    service = performance_benchmark._create_test_service("test_service", 1.0, False)

    assert service.service_name == "test_service"
    assert service.cluster_name == "test-cluster-test_service"
    assert service.cluster_type == "test"
    assert service.estimated_duration == 1.0
    assert "sleep 1.0" in service.service_config.cmd  # Should succeed

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
def test_get_memory_usage(performance_benchmark):
    """Test getting memory usage."""

    memory = performance_benchmark._get_memory_usage()

    assert isinstance(memory, float)
    assert memory >= 0


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
def test_result_to_dict(performance_benchmark):
    """Test converting result to dictionary."""

    result = BenchmarkResult(
        test_name="test",
        duration=1.0,
        success_count=1,
        failure_count=0,
        total_operations=1,
        throughput=1.0,
        average_latency=1.0,
        min_latency=1.0,
        max_latency=1.0,
        p50_latency=1.0,
        p95_latency=1.0,
        p99_latency=1.0,
        memory_usage=1.0,
        cpu_usage=1.0,
        error_rate=0.0,
        metadata={"test": "value"},
    )

    result_dict = performance_benchmark._result_to_dict(result)

    assert isinstance(result_dict, dict)
    assert result_dict["test_name"] == "test"
    assert result_dict["duration"] == 1.0
    assert result_dict["metadata"] == '{"test": "value"}'


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
def test_save_results(performance_benchmark, temp_benchmark_dir):
    """Test saving results to files."""

    result = BenchmarkResult(
        test_name="test",
        duration=1.0,
        success_count=1,
        failure_count=0,
        total_operations=1,
        throughput=1.0,
        average_latency=1.0,
        min_latency=1.0,
        max_latency=1.0,
        p50_latency=1.0,
        p95_latency=1.0,
        p99_latency=1.0,
        memory_usage=1.0,
        cpu_usage=1.0,
        error_rate=0.0,
    )

    performance_benchmark._save_results([result])

    # Check that files were created
    json_files = list(Path(temp_benchmark_dir).glob("benchmark_results_*.json"))
    csv_files = list(Path(temp_benchmark_dir).glob("benchmark_results_*.csv"))

    assert len(json_files) == 1
    assert len(csv_files) == 1


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
def test_generate_report(performance_benchmark, temp_benchmark_dir):
    """Test generating benchmark report."""

    result = BenchmarkResult(
        test_name="test_benchmark",
        duration=10.0,
        success_count=100,
        failure_count=5,
        total_operations=105,
        throughput=10.5,
        average_latency=1.0,
        min_latency=0.5,
        max_latency=2.0,
        p50_latency=1.0,
        p95_latency=1.8,
        p99_latency=1.9,
        memory_usage=50.0,
        cpu_usage=25.0,
        error_rate=0.05,
    )

    report = performance_benchmark.generate_report([result])

    assert isinstance(report, str)
    assert "SERVICE QUEUE SYSTEM PERFORMANCE BENCHMARK REPORT" in report
    assert "test_benchmark" in report
    assert "10.50 ops/sec" in report
    assert "100" in report
    assert "5" in report

@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_queue_throughput(mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test queue throughput benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 10, "failed_count": 1, "total_count": 11}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_queue_throughput(config)

    assert result.test_name == "queue_throughput"
    assert result.success_count == 10
    assert result.failure_count == 1
    assert result.total_operations == 11
    assert result.throughput > 0


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_worker_efficiency(mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test worker efficiency benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 10, "failed_count": 0, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    # Mock worker status
    mock_worker_pool.get_worker_status.return_value = [
        {"total_time": 5.0, "completed_count": 5},
        {"total_time": 5.0, "completed_count": 5},
    ]

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_worker_efficiency(config)

    assert result.test_name == "worker_efficiency"
    assert result.success_count == 10
    assert result.failure_count == 0
    assert result.total_operations == 10
    assert "utilization" in result.metadata


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_load_balancing(mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test load balancing benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 10, "failed_count": 0, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    # Mock worker status
    mock_worker_pool.get_worker_status.return_value = [{"completed_count": 5}, {"completed_count": 5}]

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_load_balancing(config)

    assert result.test_name == "load_balancing"
    assert result.success_count == 10
    assert result.failure_count == 0
    assert result.total_operations == 10
    assert "load_balancer" in result.metadata
    assert "balance" in result.metadata


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.ErrorHandler")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ErrorHandler")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ErrorHandler")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ErrorHandler")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_error_handling(mock_error_handler_class, mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test error handling benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_error_handler = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool
    mock_error_handler_class.return_value = mock_error_handler

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 8, "failed_count": 2, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    # Mock error handler
    mock_error_handler.get_error_statistics.return_value = {"error_rates": {"total": 0.1}}

    config = LoadTestConfig(num_services=10, num_workers=2, failure_rate=0.2)
    result = performance_benchmark._benchmark_error_handling(config)

    assert result.test_name == "error_handling"
    assert result.success_count == 8
    assert result.failure_count == 2
    assert result.total_operations == 10
    assert "recovery_rate" in result.metadata


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_memory_usage(mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test memory usage benchmark."""

    # psutil is handled gracefully in the benchmark code

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 10, "failed_count": 0, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_memory_usage(config)

    assert result.test_name == "memory_usage"
    assert result.success_count == 10
    assert result.failure_count == 0
    assert result.total_operations == 10
    assert "initial_memory" in result.metadata
    assert "max_memory" in result.metadata


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_concurrent_operations(mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test concurrent operations benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 10, "failed_count": 0, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_concurrent_operations(config)

    assert result.test_name == "concurrent_operations"
    assert result.success_count == 10
    assert result.failure_count == 0
    assert result.total_operations == 10
    assert "concurrent_adds" in result.metadata


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_scalability(mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test scalability benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 10, "failed_count": 0, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_scalability(config)

    assert result.test_name == "scalability"
    assert result.total_operations == 10
    assert "scalability" in result.metadata
    assert "results" in result.metadata


@patch("deployment_builder.benchmark.WorkerPool")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.ErrorHandler")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ErrorHandler")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ErrorHandler")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.ErrorHandler")
@patch("deployment_builder.benchmark.ServiceQueue")
@patch("deployment_builder.benchmark.WorkerPool")
def test_benchmark_recovery_time(mock_error_handler_class, mock_queue_class, mock_worker_pool_class, performance_benchmark):
    """Test recovery time benchmark."""

    # Mock queue and worker pool
    mock_queue = MagicMock()
    mock_worker_pool = MagicMock()
    mock_error_handler = MagicMock()
    mock_queue_class.return_value = mock_queue
    mock_worker_pool_class.return_value = mock_worker_pool
    mock_error_handler_class.return_value = mock_error_handler

    # Mock queue status
    mock_queue.get_queue_status.return_value = {"completed_count": 8, "failed_count": 2, "total_count": 10}
    mock_queue.is_empty.return_value = True
    mock_queue.wait_for_completion.return_value = None

    # Mock error handler
    mock_error_handler.get_error_statistics.return_value = {
        "circuit_breakers": {"cluster1": {"state": "OPEN"}, "cluster2": {"state": "CLOSED"}}
    }

    config = LoadTestConfig(num_services=10, num_workers=2)
    result = performance_benchmark._benchmark_recovery_time(config)

    assert result.test_name == "recovery_time"
    assert result.success_count == 8
    assert result.failure_count == 2
    assert result.total_operations == 10
    assert "recovery_time" in result.metadata
    assert "circuit_breakers" in result.metadata


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
def test_validator_creation():
    """Test creating system validator."""
    validator = SystemValidator()

    assert validator.validation_results == []


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
def test_validate_queue_functionality():
    """Test queue functionality validation."""
    validator = SystemValidator()

    result = validator._validate_queue_functionality()

    assert result["name"] == "queue_functionality"
    assert result["passed"] is True
    assert "Queue functionality working correctly" in result["message"]
    assert "operations_tested" in result["details"]


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
def test_validate_worker_management():
    """Test worker management validation."""
    validator = SystemValidator()

    result = validator._validate_worker_management()

    assert result["name"] == "worker_management"
    assert result["passed"] is True
    assert "Worker management working correctly" in result["message"]
    assert result["details"]["workers_created"] == 2


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
def test_validate_load_balancing():
    """Test load balancing validation."""
    validator = SystemValidator()

    result = validator._validate_load_balancing()

    assert result["name"] == "load_balancing"
    assert result["passed"] is True
    assert "Load balancing strategies working correctly" in result["message"]
    assert "strategies_tested" in result["details"]


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
def test_validate_execution_planning():
    """Test execution planning validation."""
    validator = SystemValidator()

    result = validator._validate_execution_planning()

    assert result["name"] == "execution_planning"
    assert result["passed"] is True
    assert "Execution planning working correctly" in result["message"]
    assert result["details"]["services_planned"] == 5


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
def test_validate_monitoring():
    """Test monitoring validation."""
    validator = SystemValidator()

    result = validator._validate_monitoring()

    assert result["name"] == "monitoring"
    assert result["passed"] is True
    assert "Monitoring system working correctly" in result["message"]
    assert result["details"]["monitoring_started"] is True


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
def test_validate_error_handling():
    """Test error handling validation."""
    validator = SystemValidator()

    result = validator._validate_error_handling()

    assert result["name"] == "error_handling"
    assert result["passed"] is True
    assert "Error handling system working correctly" in result["message"]
    assert result["details"]["errors_handled"] == 1


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
def test_validate_optimization():
    """Test optimization validation."""
    validator = SystemValidator()

    result = validator._validate_optimization()

    assert result["name"] == "optimization"
    assert result["passed"] is True
    assert "Optimization system working correctly" in result["message"]
    assert result["details"]["components_tested"] == 5


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
def test_validate_integration():
    """Test integration validation."""
    validator = SystemValidator()

    result = validator._validate_integration()

    assert result["name"] == "integration"
    assert result["passed"] is True
    assert "System integration working correctly" in result["message"]
    assert result["details"]["end_to_end_test"] is True


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
def test_generate_validation_report():
    """Test generating validation report."""
    validator = SystemValidator()

    # Add some test results
    validator.validation_results = [
        {"name": "test1", "passed": True, "message": "Test 1 passed", "details": {"key": "value"}},
        {"name": "test2", "passed": False, "message": "Test 2 failed", "details": {"error": "test error"}},
    ]

    report = validator.generate_validation_report(validator.validation_results)

    assert isinstance(report, str)
    assert "SERVICE QUEUE SYSTEM VALIDATION REPORT" in report
    assert "test1" in report
    assert "test2" in report
    assert "PASS" in report
    assert "FAIL" in report
    assert "Success Rate: 50.0%" in report


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
def test_get_benchmark():
    """Test getting global benchmark instance."""
    benchmark = get_benchmark("test_output")

    assert isinstance(benchmark, PerformanceBenchmark)
    assert benchmark.output_dir == Path("test_output")


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
def test_get_validator():
    """Test getting global validator instance."""
    validator = get_validator()

    assert isinstance(validator, SystemValidator)


@patch("deployment_builder.benchmark.Path")
@patch("deployment_builder.benchmark.get_validator")
@patch("deployment_builder.benchmark.get_benchmark")
@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.slow
@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.get_benchmark")
@patch("deployment_builder.benchmark.get_validator")
@patch("deployment_builder.benchmark.Path")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.get_benchmark")
@patch("deployment_builder.benchmark.get_validator")
@patch("deployment_builder.benchmark.Path")
@pytest.mark.slow
@pytest.mark.unit
@patch("deployment_builder.benchmark.get_benchmark")
@patch("deployment_builder.benchmark.get_validator")
@patch("deployment_builder.benchmark.Path")
def test_run_full_validation(mock_get_benchmark, mock_get_validator, mock_path):
    """Test running full validation."""
    # Mock validator
    mock_validator = MagicMock()
    mock_validator.run_validation_suite.return_value = [{"name": "test", "passed": True}]
    mock_validator.generate_validation_report.return_value = "validation report"
    mock_get_validator.return_value = mock_validator

    # Mock benchmark
    mock_benchmark = MagicMock()
    mock_benchmark.run_benchmark_suite.return_value = [MagicMock()]
    mock_benchmark.generate_report.return_value = "benchmark report"
    mock_get_benchmark.return_value = mock_benchmark

    # Mock path
    mock_path.return_value.mkdir.return_value = None
    mock_path.return_value.__truediv__.return_value = "test_file.txt"

    result = run_full_validation()

    assert "validation_results" in result
    assert "benchmark_results" in result
    assert "validation_report" in result
    assert "benchmark_report" in result
    assert "timestamp" in result


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
def test_benchmark_suite_integration():
    """Test full benchmark suite integration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        benchmark = PerformanceBenchmark(temp_dir)
        config = LoadTestConfig(num_services=5, num_workers=2, service_duration=0.1)

        # This will run actual benchmarks but with small numbers
        results = benchmark.run_benchmark_suite(config)

        assert len(results) > 0
        for result in results:
            assert isinstance(result, BenchmarkResult)
            assert result.test_name is not None
            assert result.duration >= 0
            assert result.throughput >= 0


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
def test_validation_suite_integration():
    """Test full validation suite integration."""
    validator = SystemValidator()

    # This will run actual validations
    results = validator.run_validation_suite()

    assert len(results) > 0
    for result in results:
        assert "name" in result
        assert "passed" in result
        assert "message" in result
        assert "details" in result


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
def test_full_validation_integration():
    """Test full validation and benchmarking integration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the benchmark to avoid long execution
        with patch("deployment_builder.benchmark.PerformanceBenchmark.run_benchmark_suite") as mock_benchmark:
            mock_benchmark.return_value = [MagicMock()]

            result = run_full_validation()

            assert "validation_results" in result
            assert "benchmark_results" in result
            assert "validation_report" in result
            assert "benchmark_report" in result
            assert "timestamp" in result
