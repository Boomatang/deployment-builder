"""
Error handling and recovery module for the service queue system.

This module provides comprehensive error management, recovery mechanisms,
and circuit breaker patterns for robust service execution.
"""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
import logging
from collections import defaultdict, deque

from .queue import ServiceQueue, ServiceItem, ServiceStatus
from .logging_config import get_logger

logger = get_logger()


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(Enum):
    """Error types for categorization."""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""

    error_type: ErrorType
    severity: ErrorSeverity
    service_name: str
    cluster_name: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    backoff_delay: float = 1.0
    is_recoverable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """Circuit breaker state information."""

    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    success_threshold: int = 3
    consecutive_successes: int = 0


class ErrorHandler:
    """Comprehensive error handling and recovery system."""

    def __init__(self, queue: ServiceQueue):
        """Initialize error handler.

        Args:
            queue: Service queue to manage
        """
        self.queue = queue
        self.error_history: List[ErrorContext] = []
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.retry_strategies: Dict[ErrorType, Callable] = {
            ErrorType.NETWORK: self._exponential_backoff_retry,
            ErrorType.AUTHENTICATION: self._immediate_retry,
            ErrorType.TIMEOUT: self._linear_backoff_retry,
            ErrorType.CONFIGURATION: self._no_retry,
            ErrorType.RESOURCE: self._exponential_backoff_retry,
            ErrorType.UNKNOWN: self._exponential_backoff_retry,
        }
        self.error_handlers: Dict[ErrorType, Callable] = {
            ErrorType.NETWORK: self._handle_network_error,
            ErrorType.AUTHENTICATION: self._handle_auth_error,
            ErrorType.TIMEOUT: self._handle_timeout_error,
            ErrorType.CONFIGURATION: self._handle_config_error,
            ErrorType.RESOURCE: self._handle_resource_error,
            ErrorType.UNKNOWN: self._handle_unknown_error,
        }
        self._lock = threading.Lock()
        self._error_stats: Dict[str, int] = defaultdict(int)
        self._recovery_callbacks: List[Callable] = []

    def handle_service_error(self, item: ServiceItem, error: Exception) -> None:
        """Handle service execution error.

        Args:
            item: Service item that failed
            error: Exception that occurred
        """
        error_context = self._create_error_context(item, error)

        with self._lock:
            self.error_history.append(error_context)
            self._error_stats[error_context.error_type.value] += 1

        logger.error(
            f"Service error: {error_context.service_name} on {error_context.cluster_name}: {error_context.error_message}"
        )

        # Check circuit breaker
        if self._is_circuit_open(item.cluster_name):
            logger.warning(f"Circuit breaker is OPEN for {item.cluster_name}, skipping retry")
            self._escalate_error(item, error_context)
            return

        # Update circuit breaker on error
        self._update_circuit_breaker(item.cluster_name, success=False)

        # Handle error based on type
        handler = self.error_handlers.get(error_context.error_type, self._handle_unknown_error)
        handler(item, error_context)

    def retry_failed_service(self, item: ServiceItem) -> bool:
        """Retry failed service item.

        Args:
            item: Service item to retry

        Returns:
            True if retry was successful, False otherwise
        """
        if not self._should_retry(item):
            return False

        # Update retry count
        item.retry_count += 1

        # Calculate backoff delay
        delay = self._calculate_backoff_delay(item)

        if delay > 0:
            logger.info(f"Retrying {item.service_name} in {delay:.1f} seconds (attempt {item.retry_count})")
            time.sleep(delay)

        # Reset status and add back to queue
        item.status = ServiceStatus.PENDING
        item.started_at = None
        item.completed_at = None
        item.error_message = None

        self.queue.add_service_item(item)

        return True

    def escalate_error(self, item: ServiceItem, error: Exception) -> None:
        """Escalate critical errors.

        Args:
            item: Service item that failed
            error: Exception that occurred
        """
        error_context = self._create_error_context(item, error)
        error_context.severity = ErrorSeverity.CRITICAL
        error_context.is_recoverable = False

        logger.critical(
            f"Escalating error: {error_context.service_name} on {error_context.cluster_name}: {error_context.error_message}"
        )

        # Mark as permanently failed
        item.status = ServiceStatus.FAILED
        item.error_message = f"CRITICAL: {error_context.error_message}"
        item.completed_at = datetime.now()

        # Notify recovery callbacks
        for callback in self._recovery_callbacks:
            try:
                callback(item, error_context)
            except Exception as e:
                logger.error(f"Error in recovery callback: {e}")

    def add_recovery_callback(self, callback: Callable[[ServiceItem, ErrorContext], None]) -> None:
        """Add recovery callback for error escalation.

        Args:
            callback: Function to call when errors are escalated
        """
        self._recovery_callbacks.append(callback)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics.

        Returns:
            Dictionary with error statistics
        """
        with self._lock:
            total_errors = len(self.error_history)
            error_by_type = dict(self._error_stats)

            # Calculate error rates
            error_rates = {}
            for error_type, count in error_by_type.items():
                error_rates[error_type] = count / total_errors if total_errors > 0 else 0

            # Get recent errors (last hour)
            recent_cutoff = datetime.now() - timedelta(hours=1)
            recent_errors = [e for e in self.error_history if e.timestamp > recent_cutoff]

            return {
                "total_errors": total_errors,
                "error_by_type": error_by_type,
                "error_rates": error_rates,
                "recent_errors": len(recent_errors),
                "circuit_breakers": {
                    name: {
                        "state": state.state,
                        "failure_count": state.failure_count,
                        "last_failure": state.last_failure_time.isoformat() if state.last_failure_time else None,
                    }
                    for name, state in self.circuit_breakers.items()
                },
            }

    def reset_circuit_breaker(self, cluster_name: str) -> None:
        """Reset circuit breaker for a cluster.

        Args:
            cluster_name: Name of the cluster
        """
        with self._lock:
            if cluster_name in self.circuit_breakers:
                self.circuit_breakers[cluster_name] = CircuitBreakerState()
                logger.info(f"Reset circuit breaker for {cluster_name}")

    def _create_error_context(self, item: ServiceItem, error: Exception) -> ErrorContext:
        """Create error context from service item and exception.

        Args:
            item: Service item that failed
            error: Exception that occurred

        Returns:
            Error context
        """
        error_type = self._classify_error(error)
        severity = self._determine_severity(error, error_type)

        return ErrorContext(
            error_type=error_type,
            severity=severity,
            service_name=item.service_name,
            cluster_name=item.cluster_name,
            error_message=str(error),
            retry_count=item.retry_count,
            max_retries=item.max_retries,
            backoff_delay=getattr(item, "backoff_delay", 1.0),  # Default to 1.0 if not present
            is_recoverable=self._is_recoverable(error, error_type),
            metadata={
                "service_config": item.service_config.__dict__ if hasattr(item.service_config, "__dict__") else {},
                "cluster_type": getattr(item, "cluster_type", "unknown"),
            },
        )

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type based on exception.

        Args:
            error: Exception to classify

        Returns:
            Error type
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check for timeout errors first
        if "timeout" in error_str or "TimeoutError" in error_type or error_type == "timeouterror":
            return ErrorType.TIMEOUT

        # Check for network errors
        if any(keyword in error_str for keyword in ["network", "connection", "unreachable", "refused", "reset"]):
            return ErrorType.NETWORK

        # Check for authentication errors
        if any(
            keyword in error_str
            for keyword in ["auth", "permission", "unauthorized", "forbidden", "access denied", "credential"]
        ):
            return ErrorType.AUTHENTICATION
        elif error_type in ["permissionerror", "oserror"] and "permission" in error_str:
            return ErrorType.AUTHENTICATION

        # Check for configuration errors
        if any(keyword in error_str for keyword in ["config", "configuration", "invalid", "missing", "value"]):
            return ErrorType.CONFIGURATION
        elif error_type in ["valueerror", "typeerror", "keyerror"]:
            return ErrorType.CONFIGURATION

        # Check for resource errors
        if any(keyword in error_str for keyword in ["resource", "memory", "disk", "cpu", "space"]):
            return ErrorType.RESOURCE
        elif error_type in ["memoryerror", "oserror"] and any(keyword in error_str for keyword in ["memory", "space"]):
            return ErrorType.RESOURCE

        # Default to unknown
        return ErrorType.UNKNOWN

    def _determine_severity(self, error: Exception, error_type: ErrorType) -> ErrorSeverity:
        """Determine error severity.

        Args:
            error: Exception that occurred
            error_type: Classified error type

        Returns:
            Error severity
        """
        if error_type == ErrorType.CONFIGURATION:
            return ErrorSeverity.HIGH
        elif error_type == ErrorType.AUTHENTICATION:
            return ErrorSeverity.HIGH
        elif error_type == ErrorType.RESOURCE:
            return ErrorSeverity.MEDIUM
        elif error_type == ErrorType.NETWORK:
            return ErrorSeverity.MEDIUM
        elif error_type == ErrorType.TIMEOUT:
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM

    def _is_recoverable(self, error: Exception, error_type: ErrorType) -> bool:
        """Determine if error is recoverable.

        Args:
            error: Exception that occurred
            error_type: Classified error type

        Returns:
            True if error is recoverable
        """
        if error_type == ErrorType.CONFIGURATION:
            return False
        elif error_type == ErrorType.AUTHENTICATION:
            return True  # May be temporary auth issues
        else:
            return True

    def _should_retry(self, item: ServiceItem) -> bool:
        """Determine if service should be retried.

        Args:
            item: Service item to check

        Returns:
            True if should retry
        """
        if item.retry_count >= item.max_retries:
            return False

        if self._is_circuit_open(item.cluster_name):
            return False

        return True

    def _calculate_backoff_delay(self, item: ServiceItem) -> float:
        """Calculate backoff delay for retry.

        Args:
            item: Service item to calculate delay for

        Returns:
            Delay in seconds
        """
        base_delay = getattr(item, "backoff_delay", 1.0)  # Default to 1.0 if not present
        retry_count = item.retry_count

        # Exponential backoff with jitter
        delay = base_delay * (2**retry_count)
        jitter = delay * 0.1 * (0.5 - time.time() % 1)  # ±10% jitter
        return max(0, delay + jitter)

    def _is_circuit_open(self, cluster_name: str) -> bool:
        """Check if circuit breaker is open for cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            True if circuit is open
        """
        with self._lock:
            if cluster_name not in self.circuit_breakers:
                return False

            state = self.circuit_breakers[cluster_name]

            if state.state == "OPEN":
                # Check if recovery timeout has passed
                if state.last_failure_time:
                    recovery_time = state.last_failure_time + timedelta(seconds=state.recovery_timeout)
                    if datetime.now() > recovery_time:
                        state.state = "HALF_OPEN"
                        state.consecutive_successes = 0
                        logger.info(f"Circuit breaker for {cluster_name} moved to HALF_OPEN")
                        return False
                return True

            return False

    def _update_circuit_breaker(self, cluster_name: str, success: bool) -> None:
        """Update circuit breaker state.

        Args:
            cluster_name: Name of the cluster
            success: Whether the operation was successful
        """
        with self._lock:
            if cluster_name not in self.circuit_breakers:
                self.circuit_breakers[cluster_name] = CircuitBreakerState()

            state = self.circuit_breakers[cluster_name]

            if success:
                if state.state == "HALF_OPEN":
                    state.consecutive_successes += 1
                    if state.consecutive_successes >= state.success_threshold:
                        state.state = "CLOSED"
                        state.failure_count = 0
                        logger.info(f"Circuit breaker for {cluster_name} moved to CLOSED")
                elif state.state == "CLOSED":
                    state.failure_count = max(0, state.failure_count - 1)
            else:
                state.failure_count += 1
                state.last_failure_time = datetime.now()

                if state.failure_count >= state.failure_threshold:
                    state.state = "OPEN"
                    logger.warning(f"Circuit breaker for {cluster_name} moved to OPEN")

    def _escalate_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Escalate error to recovery callbacks.

        Args:
            item: Service item that failed
            error_context: Error context
        """
        for callback in self._recovery_callbacks:
            try:
                callback(item, error_context)
            except Exception as e:
                logger.error(f"Error in recovery callback: {e}")

    # Retry strategies
    def _exponential_backoff_retry(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Exponential backoff retry strategy."""
        if self.retry_failed_service(item):
            logger.info(f"Scheduled retry for {item.service_name} with exponential backoff")

    def _immediate_retry(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Immediate retry strategy."""
        if self.retry_failed_service(item):
            logger.info(f"Scheduled immediate retry for {item.service_name}")

    def _linear_backoff_retry(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Linear backoff retry strategy."""
        if self.retry_failed_service(item):
            logger.info(f"Scheduled retry for {item.service_name} with linear backoff")

    def _no_retry(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """No retry strategy - escalate immediately."""
        self._escalate_error(item, error_context)

    # Error type handlers
    def _handle_network_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Handle network errors."""
        logger.warning(f"Network error for {item.service_name}: {error_context.error_message}")
        self._exponential_backoff_retry(item, error_context)

    def _handle_auth_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Handle authentication errors."""
        logger.warning(f"Authentication error for {item.service_name}: {error_context.error_message}")
        self._immediate_retry(item, error_context)

    def _handle_timeout_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Handle timeout errors."""
        logger.warning(f"Timeout error for {item.service_name}: {error_context.error_message}")
        self._linear_backoff_retry(item, error_context)

    def _handle_config_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Handle configuration errors."""
        logger.error(f"Configuration error for {item.service_name}: {error_context.error_message}")
        self._no_retry(item, error_context)

    def _handle_resource_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Handle resource errors."""
        logger.warning(f"Resource error for {item.service_name}: {error_context.error_message}")
        self._exponential_backoff_retry(item, error_context)

    def _handle_unknown_error(self, item: ServiceItem, error_context: ErrorContext) -> None:
        """Handle unknown errors."""
        logger.warning(f"Unknown error for {item.service_name}: {error_context.error_message}")
        self._exponential_backoff_retry(item, error_context)


class RecoveryManager:
    """Manages recovery operations and health checks."""

    def __init__(self, error_handler: ErrorHandler):
        """Initialize recovery manager.

        Args:
            error_handler: Error handler instance
        """
        self.error_handler = error_handler
        self.health_checks: Dict[str, Callable] = {}
        self.recovery_operations: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._recovery_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def add_health_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Add health check function.

        Args:
            name: Name of the health check
            check_func: Function that returns True if healthy
        """
        with self._lock:
            self.health_checks[name] = check_func

    def add_recovery_operation(self, name: str, recovery_func: Callable[[], bool]) -> None:
        """Add recovery operation.

        Args:
            name: Name of the recovery operation
            recovery_func: Function that returns True if recovery successful
        """
        with self._lock:
            self.recovery_operations[name] = recovery_func

    def start_recovery_monitoring(self) -> None:
        """Start recovery monitoring thread."""
        if self._recovery_thread and self._recovery_thread.is_alive():
            return

        self._stop_event.clear()
        self._recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self._recovery_thread.start()
        logger.info("Started recovery monitoring")

    def stop_recovery_monitoring(self) -> None:
        """Stop recovery monitoring thread."""
        self._stop_event.set()
        if self._recovery_thread and self._recovery_thread.is_alive():
            self._recovery_thread.join(timeout=2.0)
        logger.info("Stopped recovery monitoring")

    def _recovery_loop(self) -> None:
        """Main recovery monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._run_health_checks()
                self._attempt_recoveries()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
                time.sleep(60)  # Wait longer on error

    def _run_health_checks(self) -> None:
        """Run all health checks."""
        with self._lock:
            for name, check_func in self.health_checks.items():
                try:
                    is_healthy = check_func()
                    if not is_healthy:
                        logger.warning(f"Health check failed: {name}")
                except Exception as e:
                    logger.error(f"Health check error for {name}: {e}")

    def _attempt_recoveries(self) -> None:
        """Attempt recovery operations."""
        with self._lock:
            for name, recovery_func in self.recovery_operations.items():
                try:
                    success = recovery_func()
                    if success:
                        logger.info(f"Recovery operation successful: {name}")
                    else:
                        logger.warning(f"Recovery operation failed: {name}")
                except Exception as e:
                    logger.error(f"Recovery operation error for {name}: {e}")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None
_recovery_manager: Optional[RecoveryManager] = None


def get_error_handler(queue: ServiceQueue) -> ErrorHandler:
    """Get global error handler instance.

    Args:
        queue: Service queue to manage

    Returns:
        Error handler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(queue)
    return _error_handler


def get_recovery_manager(error_handler: ErrorHandler) -> RecoveryManager:
    """Get global recovery manager instance.

    Args:
        error_handler: Error handler instance

    Returns:
        Recovery manager instance
    """
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager(error_handler)
    return _recovery_manager


def cleanup_error_handling() -> None:
    """Cleanup error handling resources."""
    global _error_handler, _recovery_manager

    if _recovery_manager:
        _recovery_manager.stop_recovery_monitoring()

    _error_handler = None
    _recovery_manager = None
