"""
Performance optimization module for the service queue system.

This module provides various optimization strategies to improve the performance
of the service queue system, including connection pooling, caching, and
batch processing.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor
import subprocess
import os

from .logging_config import get_logger

logger = get_logger()


@dataclass
class ConnectionPool:
    """Connection pool for kubectl contexts to avoid repeated authentication."""

    contexts: Dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_context(self, cluster_name: str) -> Optional[str]:
        """Get kubectl context for a cluster."""
        with self._lock:
            return self.contexts.get(cluster_name)

    def set_context(self, cluster_name: str, context: str) -> None:
        """Set kubectl context for a cluster."""
        with self._lock:
            self.contexts[cluster_name] = context

    def clear_context(self, cluster_name: str) -> None:
        """Clear kubectl context for a cluster."""
        with self._lock:
            self.contexts.pop(cluster_name, None)

    def clear_all(self) -> None:
        """Clear all contexts."""
        with self._lock:
            self.contexts.clear()


@dataclass
class CacheEntry:
    """Cache entry with timestamp and TTL."""

    value: Any
    timestamp: float
    ttl: float = 300.0  # 5 minutes default TTL

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl


class ServiceCache:
    """Cache for service execution results and metadata."""

    def __init__(self, default_ttl: float = 300.0):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self.cache.get(key)
            if entry and not entry.is_expired():
                return entry.value
            elif entry:
                # Remove expired entry
                del self.cache[key]
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        with self._lock:
            self.cache[key] = CacheEntry(value=value, timestamp=time.time(), ttl=ttl or self.default_ttl)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        with self._lock:
            expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)


class BatchProcessor:
    """Process similar services in batches for efficiency."""

    def __init__(self, batch_size: int = 5, batch_timeout: float = 2.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_batches: Dict[str, List[Any]] = defaultdict(list)
        self.batch_timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def add_to_batch(self, batch_key: str, item: Any, processor_func) -> None:
        """Add item to batch for processing."""
        should_process_immediately = False

        with self._lock:
            self.pending_batches[batch_key].append((item, processor_func))

            # If batch is full, process immediately
            if len(self.pending_batches[batch_key]) >= self.batch_size:
                should_process_immediately = True
            else:
                # Set timer for batch timeout
                if batch_key in self.batch_timers:
                    self.batch_timers[batch_key].cancel()

                self.batch_timers[batch_key] = threading.Timer(
                    self.batch_timeout, self._process_batch, args=[batch_key]
                )
                self.batch_timers[batch_key].start()

        # Process immediately if batch is full (outside the lock)
        if should_process_immediately:
            self._process_batch(batch_key)

    def _process_batch(self, batch_key: str) -> None:
        """Process a batch of items."""
        with self._lock:
            if batch_key not in self.pending_batches:
                return

            batch = self.pending_batches[batch_key]
            if not batch:
                return

            # Clear the batch
            del self.pending_batches[batch_key]
            if batch_key in self.batch_timers:
                self.batch_timers[batch_key].cancel()
                del self.batch_timers[batch_key]

        # Process items in parallel
        with ThreadPoolExecutor(max_workers=min(len(batch), 4)) as executor:
            futures = []
            for item, processor_func in batch:
                future = executor.submit(processor_func, item)
                futures.append(future)

            # Wait for all to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing batch item: {e}")


class ResourceOptimizer:
    """Optimize resource usage and performance."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.connection_pool = ConnectionPool()
        self.service_cache = ServiceCache()
        self.batch_processor = BatchProcessor()
        self.worker_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def optimize_worker_allocation(self, workers: List[Any], services: List[Any]) -> List[Any]:
        """Optimize worker allocation based on service characteristics."""
        # Group services by cluster type for better resource utilization
        cluster_groups = defaultdict(list)
        for service in services:
            cluster_type = getattr(service, "cluster_type", "default")
            cluster_groups[cluster_type].append(service)

        # Allocate workers to cluster groups
        optimized_workers = []
        worker_index = 0

        for cluster_type, cluster_services in cluster_groups.items():
            # Calculate optimal workers for this cluster type
            optimal_workers = min(len(cluster_services), max(1, len(workers) // len(cluster_groups)))

            for i in range(optimal_workers):
                if worker_index < len(workers):
                    worker = workers[worker_index]
                    worker.cluster_type = cluster_type
                    optimized_workers.append(worker)
                    worker_index += 1

        return optimized_workers

    def pre_warm_connections(self, cluster_names: List[str]) -> None:
        """Pre-warm connections to clusters."""
        logger.info(f"Pre-warming connections to {len(cluster_names)} clusters")

        def warm_connection(cluster_name: str):
            try:
                # Test kubectl connection
                result = subprocess.run(
                    ["kubectl", "cluster-info", "--context", cluster_name], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    self.connection_pool.set_context(cluster_name, cluster_name)
                    logger.debug(f"Pre-warmed connection to {cluster_name}")
                else:
                    logger.warning(f"Failed to pre-warm connection to {cluster_name}")
            except Exception as e:
                logger.warning(f"Error pre-warming connection to {cluster_name}: {e}")

        # Pre-warm connections in parallel
        with ThreadPoolExecutor(max_workers=min(len(cluster_names), 4)) as executor:
            futures = [executor.submit(warm_connection, name) for name in cluster_names]
            for future in futures:
                try:
                    future.result(timeout=15)
                except Exception as e:
                    logger.warning(f"Pre-warming failed: {e}")

    def optimize_service_execution(self, service_item: Any) -> Any:
        """Optimize individual service execution."""
        # Check cache first
        cache_key = f"{service_item.service_name}_{service_item.cluster_name}"
        cached_result = self.service_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Using cached result for {service_item.service_name}")
            return cached_result

        # Use connection pool for kubectl commands
        context = self.connection_pool.get_context(service_item.cluster_name)
        if context:
            # Add context to service item for execution
            service_item.kubectl_context = context

        return service_item

    def batch_similar_services(self, services: List[Any]) -> List[List[Any]]:
        """Group similar services for batch processing."""
        # Group by cluster type and service type
        groups = defaultdict(list)

        for service in services:
            cluster_type = getattr(service, "cluster_type", "default")
            service_type = getattr(service, "service_type", "default")
            key = f"{cluster_type}_{service_type}"
            groups[key].append(service)

        return list(groups.values())

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return {
                "connection_pool_size": len(self.connection_pool.contexts),
                "cache_size": len(self.service_cache.cache),
                "cache_hit_rate": self._calculate_cache_hit_rate(),
                "worker_utilization": self._calculate_worker_utilization(),
                "batch_efficiency": self._calculate_batch_efficiency(),
            }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (simplified)."""
        # This would need to be implemented with proper hit/miss tracking
        return 0.0

    def _calculate_worker_utilization(self) -> float:
        """Calculate worker utilization rate."""
        if not self.worker_stats:
            return 0.0

        total_workers = len(self.worker_stats)
        busy_workers = sum(1 for stats in self.worker_stats.values() if stats.get("is_busy", False))

        return busy_workers / total_workers if total_workers > 0 else 0.0

    def _calculate_batch_efficiency(self) -> float:
        """Calculate batch processing efficiency."""
        # This would need to be implemented with proper batch tracking
        return 0.0

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.connection_pool.clear_all()
        self.service_cache.clear()

        # Cancel any pending batch timers
        for timer in self.batch_processor.batch_timers.values():
            timer.cancel()
        self.batch_processor.batch_timers.clear()


class PerformanceProfiler:
    """Profile and analyze performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.start_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        with self._lock:
            self.start_times[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration."""
        with self._lock:
            if operation not in self.start_times:
                return 0.0

            duration = time.time() - self.start_times[operation]
            self.metrics[operation].append(duration)
            del self.start_times[operation]
            return duration

    def get_average_time(self, operation: str) -> float:
        """Get average time for an operation."""
        with self._lock:
            times = self.metrics.get(operation, [])
            return sum(times) / len(times) if times else 0.0

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        with self._lock:
            summary = {}
            for operation, times in self.metrics.items():
                if times:
                    summary[operation] = {
                        "count": len(times),
                        "total_time": sum(times),
                        "average_time": sum(times) / len(times),
                        "min_time": min(times),
                        "max_time": max(times),
                    }
            return summary

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.metrics.clear()
            self.start_times.clear()


# Global instances for optimization
_connection_pool = ConnectionPool()
_service_cache = ServiceCache()
_batch_processor = BatchProcessor()
_resource_optimizer = ResourceOptimizer()
_performance_profiler = PerformanceProfiler()


def get_connection_pool() -> ConnectionPool:
    """Get global connection pool instance."""
    return _connection_pool


def get_service_cache() -> ServiceCache:
    """Get global service cache instance."""
    return _service_cache


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor instance."""
    return _batch_processor


def get_resource_optimizer() -> ResourceOptimizer:
    """Get global resource optimizer instance."""
    return _resource_optimizer


def get_performance_profiler() -> PerformanceProfiler:
    """Get global performance profiler instance."""
    return _performance_profiler


def cleanup_optimization_resources() -> None:
    """Cleanup all optimization resources."""
    _resource_optimizer.cleanup()
    _performance_profiler.reset()
