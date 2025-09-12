"""
Tests for the error handling module.

This module tests the error handling, recovery mechanisms, and circuit breaker
functionality for robust service execution.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

from deployment_builder.error_handler import (
    ErrorSeverity,
    ErrorType,
    ErrorContext,
    CircuitBreakerState,
    ErrorHandler,
    RecoveryManager,
    get_error_handler,
    get_recovery_manager,
    cleanup_error_handling,
)
from deployment_builder.queue import ServiceQueue, ServiceItem, ServiceStatus, ServiceConfig


def test_error_severity_values():
    """Test error severity enum values."""
    assert ErrorSeverity.LOW.value == "low"
    assert ErrorSeverity.MEDIUM.value == "medium"
    assert ErrorSeverity.HIGH.value == "high"
    assert ErrorSeverity.CRITICAL.value == "critical"


def test_error_type_values():
    """Test error type enum values."""
    assert ErrorType.NETWORK.value == "network"
    assert ErrorType.AUTHENTICATION.value == "authentication"
    assert ErrorType.TIMEOUT.value == "timeout"
    assert ErrorType.CONFIGURATION.value == "configuration"
    assert ErrorType.RESOURCE.value == "resource"
    assert ErrorType.UNKNOWN.value == "unknown"


def test_error_context_creation():
    """Test creating error context."""
    context = ErrorContext(
        error_type=ErrorType.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        service_name="test-service",
        cluster_name="test-cluster",
        error_message="Connection failed",
    )

    assert context.error_type == ErrorType.NETWORK
    assert context.severity == ErrorSeverity.MEDIUM
    assert context.service_name == "test-service"
    assert context.cluster_name == "test-cluster"
    assert context.error_message == "Connection failed"
    assert context.retry_count == 0
    assert context.max_retries == 3
    assert context.backoff_delay == 1.0
    assert context.is_recoverable is True
    assert isinstance(context.timestamp, datetime)
    assert context.metadata == {}


def test_error_context_defaults():
    """Test error context with default values."""
    context = ErrorContext(
        error_type=ErrorType.UNKNOWN,
        severity=ErrorSeverity.LOW,
        service_name="test",
        cluster_name="test",
        error_message="test",
    )

    assert context.retry_count == 0
    assert context.max_retries == 3
    assert context.backoff_delay == 1.0
    assert context.is_recoverable is True
    assert context.metadata == {}


def test_circuit_breaker_state_creation():
    """Test creating circuit breaker state."""
    state = CircuitBreakerState()

    assert state.failure_count == 0
    assert state.last_failure_time is None
    assert state.state == "CLOSED"
    assert state.failure_threshold == 5
    assert state.recovery_timeout == 60.0
    assert state.success_threshold == 3
    assert state.consecutive_successes == 0


def test_circuit_breaker_state_custom():
    """Test circuit breaker state with custom values."""
    state = CircuitBreakerState(failure_count=3, state="OPEN", failure_threshold=10, recovery_timeout=120.0)

    assert state.failure_count == 3
    assert state.state == "OPEN"
    assert state.failure_threshold == 10
    assert state.recovery_timeout == 120.0


@pytest.fixture
def error_handler_setup():
    """Create test setup with queue and error handler."""
    queue = ServiceQueue(max_workers=2)
    error_handler = ErrorHandler(queue)
    return queue, error_handler


def test_error_handler_creation(error_handler_setup):
    """Test creating error handler."""
    queue, error_handler = error_handler_setup

    assert error_handler.queue == queue
    assert error_handler.error_history == []
    assert error_handler.circuit_breakers == {}
    assert len(error_handler.retry_strategies) == 6
    assert len(error_handler.error_handlers) == 6
    assert error_handler._recovery_callbacks == []


def test_classify_error(error_handler_setup):
    """Test error classification."""
    queue, error_handler = error_handler_setup

    # Test network error
    error = ConnectionError("Network unreachable")
    error_type = error_handler._classify_error(error)
    assert error_type == ErrorType.NETWORK

    # Test authentication error
    error = PermissionError("Access denied")
    error_type = error_handler._classify_error(error)
    assert error_type == ErrorType.AUTHENTICATION

    # Test timeout error
    error = TimeoutError("Operation timed out")
    error_type = error_handler._classify_error(error)
    assert error_type == ErrorType.TIMEOUT

    # Test configuration error
    error = ValueError("Invalid configuration")
    error_type = error_handler._classify_error(error)
    assert error_type == ErrorType.CONFIGURATION

    # Test resource error
    error = MemoryError("Out of memory")
    error_type = error_handler._classify_error(error)
    assert error_type == ErrorType.RESOURCE

    # Test unknown error
    error = RuntimeError("Unknown error")
    error_type = error_handler._classify_error(error)
    assert error_type == ErrorType.UNKNOWN


def test_determine_severity(error_handler_setup):
    """Test severity determination."""
    queue, error_handler = error_handler_setup

    # Test configuration error (should be HIGH)
    error = ValueError("Invalid config")
    severity = error_handler._determine_severity(error, ErrorType.CONFIGURATION)
    assert severity == ErrorSeverity.HIGH

    # Test authentication error (should be HIGH)
    error = PermissionError("Access denied")
    severity = error_handler._determine_severity(error, ErrorType.AUTHENTICATION)
    assert severity == ErrorSeverity.HIGH

    # Test timeout error (should be LOW)
    error = TimeoutError("Timeout")
    severity = error_handler._determine_severity(error, ErrorType.TIMEOUT)
    assert severity == ErrorSeverity.LOW

    # Test network error (should be MEDIUM)
    error = ConnectionError("Network error")
    severity = error_handler._determine_severity(error, ErrorType.NETWORK)
    assert severity == ErrorSeverity.MEDIUM


def test_is_recoverable(error_handler_setup):
    """Test recoverability determination."""
    queue, error_handler = error_handler_setup

    # Test configuration error (should not be recoverable)
    error = ValueError("Invalid config")
    is_recoverable = error_handler._is_recoverable(error, ErrorType.CONFIGURATION)
    assert is_recoverable is False

    # Test network error (should be recoverable)
    error = ConnectionError("Network error")
    is_recoverable = error_handler._is_recoverable(error, ErrorType.NETWORK)
    assert is_recoverable is True

    # Test authentication error (should be recoverable)
    error = PermissionError("Access denied")
    is_recoverable = error_handler._is_recoverable(error, ErrorType.AUTHENTICATION)
    assert is_recoverable is True


def test_should_retry(error_handler_setup):
    """Test retry decision logic."""
    queue, error_handler = error_handler_setup

    # Create service item
    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="test",
        service_name="test-service",
        service_config=service_config,
        max_retries=3,
    )

    # Test retry when under max retries
    item.retry_count = 1
    should_retry = error_handler._should_retry(item)
    assert should_retry is True

    # Test no retry when at max retries
    item.retry_count = 3
    should_retry = error_handler._should_retry(item)
    assert should_retry is False

    # Test no retry when circuit is open
    item.retry_count = 1
    error_handler.circuit_breakers["test-cluster"] = CircuitBreakerState(state="OPEN", failure_count=5)
    should_retry = error_handler._should_retry(item)
    assert should_retry is False


def test_calculate_backoff_delay(error_handler_setup):
    """Test backoff delay calculation."""
    queue, error_handler = error_handler_setup

    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster", cluster_type="test", service_name="test-service", service_config=service_config
    )

    # Test exponential backoff with default backoff_delay
    item.retry_count = 0
    delay = error_handler._calculate_backoff_delay(item)
    assert delay >= 0.9  # Base delay (default) with jitter tolerance

    item.retry_count = 1
    delay = error_handler._calculate_backoff_delay(item)
    assert delay >= 1.8  # 2^1 * 1.0 with jitter tolerance

    item.retry_count = 2
    delay = error_handler._calculate_backoff_delay(item)
    assert delay >= 3.6  # 2^2 * 1.0 with jitter tolerance


def test_is_circuit_open(error_handler_setup):
    """Test circuit breaker state checking."""
    queue, error_handler = error_handler_setup

    # Test closed circuit
    error_handler.circuit_breakers["test-cluster"] = CircuitBreakerState(state="CLOSED")
    is_open = error_handler._is_circuit_open("test-cluster")
    assert is_open is False

    # Test open circuit
    error_handler.circuit_breakers["test-cluster"] = CircuitBreakerState(state="OPEN")
    is_open = error_handler._is_circuit_open("test-cluster")
    assert is_open is True

    # Test half-open circuit
    error_handler.circuit_breakers["test-cluster"] = CircuitBreakerState(state="HALF_OPEN")
    is_open = error_handler._is_circuit_open("test-cluster")
    assert is_open is False


def test_update_circuit_breaker(error_handler_setup):
    """Test circuit breaker state updates."""
    queue, error_handler = error_handler_setup

    # Test successful operation
    error_handler._update_circuit_breaker("test-cluster", success=True)
    state = error_handler.circuit_breakers["test-cluster"]
    assert state.failure_count == 0
    assert state.state == "CLOSED"

    # Test failed operation
    error_handler._update_circuit_breaker("test-cluster", success=False)
    state = error_handler.circuit_breakers["test-cluster"]
    assert state.failure_count == 1
    assert state.last_failure_time is not None

    # Test circuit opening
    for _ in range(5):
        error_handler._update_circuit_breaker("test-cluster", success=False)
    state = error_handler.circuit_breakers["test-cluster"]
    assert state.state == "OPEN"


def test_handle_service_error(error_handler_setup):
    """Test handling service errors."""
    queue, error_handler = error_handler_setup

    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster", cluster_type="test", service_name="test-service", service_config=service_config
    )

    error = ConnectionError("Network unreachable")

    # Mock the retry method
    with patch.object(error_handler, "retry_failed_service") as mock_retry:
        mock_retry.return_value = True
        error_handler.handle_service_error(item, error)

        # Check that error was recorded
        assert len(error_handler.error_history) == 1
        error_context = error_handler.error_history[0]
        assert error_context.service_name == "test-service"
        assert error_context.cluster_name == "test-cluster"
        assert error_context.error_type == ErrorType.NETWORK

        # Check that retry was attempted
        mock_retry.assert_called_once_with(item)


def test_retry_failed_service(error_handler_setup):
    """Test retrying failed services."""
    queue, error_handler = error_handler_setup

    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster",
        cluster_type="test",
        service_name="test-service",
        service_config=service_config,
        max_retries=3,
    )

    # Test successful retry
    with patch.object(queue, "add_service_item") as mock_add:
        result = error_handler.retry_failed_service(item)

        assert result is True
        assert item.retry_count == 1
        assert item.status == ServiceStatus.PENDING
        assert item.started_at is None
        assert item.completed_at is None
        assert item.error_message is None
        mock_add.assert_called_once_with(item)

        # Test retry when at max retries
        item.retry_count = 3
        result = error_handler.retry_failed_service(item)
        assert result is False


def test_escalate_error(error_handler_setup):
    """Test error escalation."""
    queue, error_handler = error_handler_setup

    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster", cluster_type="test", service_name="test-service", service_config=service_config
    )

    error = ValueError("Critical configuration error")

    # Add recovery callback
    callback_called = []

    def recovery_callback(item, error_context):
        callback_called.append((item, error_context))

    error_handler.add_recovery_callback(recovery_callback)

    # Escalate error
    error_handler.escalate_error(item, error)

    # Check that item was marked as failed
    assert item.status == ServiceStatus.FAILED
    assert "CRITICAL:" in item.error_message
    assert item.completed_at is not None

    # Check that callback was called
    assert len(callback_called) == 1
    assert callback_called[0][0] == item
    assert callback_called[0][1].severity == ErrorSeverity.CRITICAL


def test_get_error_statistics(error_handler_setup):
    """Test getting error statistics."""
    queue, error_handler = error_handler_setup

    # Add some test errors
    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item1 = ServiceItem(
        cluster_name="cluster1", cluster_type="test", service_name="service1", service_config=service_config
    )
    item2 = ServiceItem(
        cluster_name="cluster2", cluster_type="test", service_name="service2", service_config=service_config
    )

    error_handler.handle_service_error(item1, ConnectionError("Network error"))
    error_handler.handle_service_error(item2, ValueError("Config error"))

    stats = error_handler.get_error_statistics()

    assert stats["total_errors"] == 2
    assert "error_by_type" in stats
    assert "error_rates" in stats
    assert "recent_errors" in stats
    assert "circuit_breakers" in stats


def test_reset_circuit_breaker(error_handler_setup):
    """Test resetting circuit breaker."""
    queue, error_handler = error_handler_setup

    # Set up circuit breaker in OPEN state
    error_handler.circuit_breakers["test-cluster"] = CircuitBreakerState(state="OPEN", failure_count=5)

    # Reset circuit breaker
    error_handler.reset_circuit_breaker("test-cluster")

    state = error_handler.circuit_breakers["test-cluster"]
    assert state.state == "CLOSED"
    assert state.failure_count == 0
    assert state.last_failure_time is None


@pytest.fixture
def recovery_manager_setup():
    """Create test setup with error handler and recovery manager."""
    queue = ServiceQueue(max_workers=2)
    error_handler = ErrorHandler(queue)
    recovery_manager = RecoveryManager(error_handler)
    return queue, error_handler, recovery_manager


def test_recovery_manager_creation(recovery_manager_setup):
    """Test creating recovery manager."""
    queue, error_handler, recovery_manager = recovery_manager_setup

    assert recovery_manager.error_handler == error_handler
    assert recovery_manager.health_checks == {}
    assert recovery_manager.recovery_operations == {}
    assert recovery_manager._recovery_thread is None
    assert recovery_manager._stop_event.is_set() is False


def test_add_health_check(recovery_manager_setup):
    """Test adding health check."""
    queue, error_handler, recovery_manager = recovery_manager_setup

    def health_check():
        return True

    recovery_manager.add_health_check("test_check", health_check)

    assert "test_check" in recovery_manager.health_checks
    assert recovery_manager.health_checks["test_check"] == health_check


def test_add_recovery_operation(recovery_manager_setup):
    """Test adding recovery operation."""
    queue, error_handler, recovery_manager = recovery_manager_setup

    def recovery_op():
        return True

    recovery_manager.add_recovery_operation("test_recovery", recovery_op)

    assert "test_recovery" in recovery_manager.recovery_operations
    assert recovery_manager.recovery_operations["test_recovery"] == recovery_op


def test_start_stop_recovery_monitoring(recovery_manager_setup):
    """Test starting and stopping recovery monitoring."""
    queue, error_handler, recovery_manager = recovery_manager_setup

    # Start monitoring
    recovery_manager.start_recovery_monitoring()
    assert recovery_manager._recovery_thread is not None
    assert recovery_manager._recovery_thread.is_alive()

    # Stop monitoring
    recovery_manager.stop_recovery_monitoring()
    assert recovery_manager._stop_event.is_set()


def test_run_health_checks(recovery_manager_setup):
    """Test running health checks."""
    queue, error_handler, recovery_manager = recovery_manager_setup

    # Add health checks
    check_results = []

    def healthy_check():
        check_results.append("healthy")
        return True

    def unhealthy_check():
        check_results.append("unhealthy")
        return False

    recovery_manager.add_health_check("healthy", healthy_check)
    recovery_manager.add_health_check("unhealthy", unhealthy_check)

    # Run health checks
    recovery_manager._run_health_checks()

    assert "healthy" in check_results
    assert "unhealthy" in check_results


def test_attempt_recoveries(recovery_manager_setup):
    """Test attempting recovery operations."""
    queue, error_handler, recovery_manager = recovery_manager_setup

    # Add recovery operations
    recovery_results = []

    def successful_recovery():
        recovery_results.append("success")
        return True

    def failed_recovery():
        recovery_results.append("failure")
        return False

    recovery_manager.add_recovery_operation("success", successful_recovery)
    recovery_manager.add_recovery_operation("failure", failed_recovery)

    # Attempt recoveries
    recovery_manager._attempt_recoveries()

    assert "success" in recovery_results
    assert "failure" in recovery_results


def test_get_error_handler():
    """Test getting global error handler."""
    queue = ServiceQueue(max_workers=2)
    error_handler = get_error_handler(queue)

    assert isinstance(error_handler, ErrorHandler)
    assert error_handler.queue == queue


def test_get_recovery_manager():
    """Test getting global recovery manager."""
    queue = ServiceQueue(max_workers=2)
    error_handler = ErrorHandler(queue)
    recovery_manager = get_recovery_manager(error_handler)

    assert isinstance(recovery_manager, RecoveryManager)
    assert recovery_manager.error_handler == error_handler


def test_cleanup_error_handling():
    """Test cleanup of error handling resources."""
    # This should not raise any exceptions
    cleanup_error_handling()


def test_full_error_handling_workflow():
    """Test full error handling workflow."""
    queue = ServiceQueue(max_workers=2)
    error_handler = ErrorHandler(queue)
    recovery_manager = RecoveryManager(error_handler)

    # Add health check and recovery operation
    health_check_called = []
    recovery_called = []

    def health_check():
        health_check_called.append(True)
        return True

    def recovery_op():
        recovery_called.append(True)
        return True

    recovery_manager.add_health_check("test_health", health_check)
    recovery_manager.add_recovery_operation("test_recovery", recovery_op)

    # Create service item
    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster", cluster_type="test", service_name="test-service", service_config=service_config
    )

    # Test error handling
    error = ConnectionError("Network error")

    with patch.object(error_handler, "retry_failed_service") as mock_retry:
        mock_retry.return_value = True
        error_handler.handle_service_error(item, error)

        # Verify error was handled
        assert len(error_handler.error_history) == 1
        mock_retry.assert_called_once()

    # Test recovery monitoring
    recovery_manager._run_health_checks()
    recovery_manager._attempt_recoveries()

    assert len(health_check_called) == 1
    assert len(recovery_called) == 1

    # Cleanup
    recovery_manager.stop_recovery_monitoring()


def test_circuit_breaker_integration():
    """Test circuit breaker integration with error handling."""
    queue = ServiceQueue(max_workers=2)
    error_handler = ErrorHandler(queue)

    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster", cluster_type="test", service_name="test-service", service_config=service_config
    )

    # Simulate multiple failures to open circuit
    for _ in range(6):
        error_handler.handle_service_error(item, ConnectionError("Network error"))

    # Check that circuit is open
    state = error_handler.circuit_breakers["test-cluster"]
    assert state.state == "OPEN"

    # Test that retry is blocked when circuit is open
    with patch.object(queue, "add_service_item") as mock_add:
        result = error_handler.retry_failed_service(item)
        assert result is False
        mock_add.assert_not_called()

    # Reset circuit breaker
    error_handler.reset_circuit_breaker("test-cluster")
    state = error_handler.circuit_breakers["test-cluster"]
    assert state.state == "CLOSED"


def test_error_escalation_with_callbacks():
    """Test error escalation with recovery callbacks."""
    queue = ServiceQueue(max_workers=2)
    error_handler = ErrorHandler(queue)

    # Add recovery callback
    escalation_events = []

    def escalation_callback(item, error_context):
        escalation_events.append((item.service_name, error_context.severity))

    error_handler.add_recovery_callback(escalation_callback)

    # Create service item
    service_config = ServiceConfig(cmd="echo test", kubeconfig_flag="--kubeconfig")
    item = ServiceItem(
        cluster_name="test-cluster", cluster_type="test", service_name="test-service", service_config=service_config
    )

    # Escalate error
    error = ValueError("Critical error")
    error_handler.escalate_error(item, error)

    # Verify escalation
    assert len(escalation_events) == 1
    assert escalation_events[0][0] == "test-service"
    assert escalation_events[0][1] == ErrorSeverity.CRITICAL
    assert item.status == ServiceStatus.FAILED
