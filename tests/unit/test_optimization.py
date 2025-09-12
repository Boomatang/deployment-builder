"""
Tests for the optimization module.

This module tests the performance optimization features including
connection pooling, caching, batch processing, and resource optimization.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, call
from collections import defaultdict

from deployment_builder.optimization import (
    ConnectionPool,
    CacheEntry,
    ServiceCache,
    BatchProcessor,
    ResourceOptimizer,
    PerformanceProfiler,
    get_connection_pool,
    get_service_cache,
    get_batch_processor,
    get_resource_optimizer,
    get_performance_profiler,
    cleanup_optimization_resources,
)


def test_connection_pool_creation():
    """Test creating connection pool."""
    pool = ConnectionPool()
    assert pool.contexts == {}
    assert isinstance(pool._lock, threading.Lock)


def test_set_and_get_context():
    """Test setting and getting contexts."""
    pool = ConnectionPool()

    pool.set_context("cluster1", "context1")
    assert pool.get_context("cluster1") == "context1"
    assert pool.get_context("nonexistent") is None


def test_clear_context():
    """Test clearing contexts."""
    pool = ConnectionPool()

    pool.set_context("cluster1", "context1")
    pool.set_context("cluster2", "context2")

    pool.clear_context("cluster1")
    assert pool.get_context("cluster1") is None
    assert pool.get_context("cluster2") == "context2"


def test_clear_all():
    """Test clearing all contexts."""
    pool = ConnectionPool()

    pool.set_context("cluster1", "context1")
    pool.set_context("cluster2", "context2")

    pool.clear_all()
    assert pool.contexts == {}


def test_thread_safety():
    """Test thread safety of connection pool."""
    pool = ConnectionPool()
    results = []

    def worker(worker_id):
        for i in range(10):
            cluster_name = f"cluster_{worker_id}_{i}"
            context_name = f"context_{worker_id}_{i}"
            pool.set_context(cluster_name, context_name)
            result = pool.get_context(cluster_name)
            results.append((cluster_name, result))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All results should be correct
    for cluster_name, result in results:
        expected_context = cluster_name.replace("cluster_", "context_")
        assert result == expected_context


def test_cache_entry_creation():
    """Test creating cache entry."""
    entry = CacheEntry("value", 1234567890.0, 300.0)
    assert entry.value == "value"
    assert entry.timestamp == 1234567890.0
    assert entry.ttl == 300.0


def test_cache_entry_default_ttl():
    """Test cache entry with default TTL."""
    entry = CacheEntry("value", 1234567890.0)
    assert entry.ttl == 300.0


def test_is_expired():
    """Test cache entry expiration."""
    current_time = time.time()

    # Not expired
    entry = CacheEntry("value", current_time - 100.0, 300.0)
    assert not entry.is_expired()

    # Expired
    entry = CacheEntry("value", current_time - 400.0, 300.0)
    assert entry.is_expired()


def test_service_cache_creation():
    """Test creating service cache."""
    cache = ServiceCache()
    assert cache.cache == {}
    assert cache.default_ttl == 300.0
    assert isinstance(cache._lock, threading.Lock)


def test_service_cache_custom_ttl():
    """Test service cache with custom TTL."""
    cache = ServiceCache(600.0)
    assert cache.default_ttl == 600.0


def test_set_and_get():
    """Test setting and getting cache values."""
    cache = ServiceCache()

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("nonexistent") is None


def test_set_with_custom_ttl():
    """Test setting cache value with custom TTL."""
    cache = ServiceCache()

    cache.set("key1", "value1", 600.0)
    entry = cache.cache["key1"]
    assert entry.ttl == 600.0


def test_expired_entry_removal():
    """Test removal of expired entries."""
    cache = ServiceCache(0.1)  # Very short TTL

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Wait for expiration
    time.sleep(0.2)
    assert cache.get("key1") is None


def test_clear():
    """Test clearing cache."""
    cache = ServiceCache()

    cache.set("key1", "value1")
    cache.set("key2", "value2")

    cache.clear()
    assert cache.cache == {}


def test_cleanup_expired():
    """Test cleanup of expired entries."""
    cache = ServiceCache(0.1)  # Very short TTL

    cache.set("key1", "value1")
    cache.set("key2", "value2")

    # Wait for expiration
    time.sleep(0.2)

    removed_count = cache.cleanup_expired()
    assert removed_count == 2
    assert cache.cache == {}


def test_thread_safety():
    """Test thread safety of service cache."""
    cache = ServiceCache()
    results = []

    def worker(worker_id):
        for i in range(10):
            key = f"key_{worker_id}_{i}"
            value = f"value_{worker_id}_{i}"
            cache.set(key, value)
            result = cache.get(key)
            results.append((key, result))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All results should be correct
    for key, result in results:
        expected_value = key.replace("key_", "value_")
        assert result == expected_value


def test_batch_processor_creation():
    """Test creating batch processor."""
    processor = BatchProcessor()
    assert processor.batch_size == 5
    assert processor.batch_timeout == 2.0
    assert processor.pending_batches == {}
    assert processor.batch_timers == {}
    assert isinstance(processor._lock, threading.Lock)


def test_batch_processor_custom_params():
    """Test batch processor with custom parameters."""
    processor = BatchProcessor(batch_size=10, batch_timeout=5.0)
    assert processor.batch_size == 10
    assert processor.batch_timeout == 5.0


def test_add_to_batch_immediate_processing():
    """Test adding items to batch that triggers immediate processing."""
    processor = BatchProcessor(batch_size=2)
    processed_items = []
    processing_complete = threading.Event()

    def processor_func(item):
        processed_items.append(item)
        # Signal completion when we have both items
        if len(processed_items) == 2:
            processing_complete.set()

    # Add items to trigger immediate processing
    processor.add_to_batch("batch1", "item1", processor_func)
    processor.add_to_batch("batch1", "item2", processor_func)

    # Wait for processing to complete with timeout
    assert processing_complete.wait(timeout=2.0), "Batch processing did not complete within timeout"

    assert len(processed_items) == 2
    assert "item1" in processed_items
    assert "item2" in processed_items


def test_add_to_batch_timeout_processing():
    """Test adding items to batch that triggers timeout processing."""
    processor = BatchProcessor(batch_size=5, batch_timeout=0.1)
    processed_items = []
    processing_complete = threading.Event()

    def processor_func(item):
        processed_items.append(item)
        processing_complete.set()

    # Add one item (not enough for immediate processing)
    processor.add_to_batch("batch1", "item1", processor_func)

    # Wait for timeout processing to complete
    assert processing_complete.wait(timeout=1.0), "Timeout processing did not complete within timeout"

    assert len(processed_items) == 1
    assert "item1" in processed_items


def test_multiple_batches():
    """Test processing multiple batches."""
    processor = BatchProcessor(batch_size=2)
    processed_items = defaultdict(list)
    processing_complete = threading.Event()
    expected_items = 4

    def processor_func(item):
        batch_key, item_value = item
        processed_items[batch_key].append(item_value)
        # Signal completion when we have all expected items
        total_processed = sum(len(items) for items in processed_items.values())
        if total_processed == expected_items:
            processing_complete.set()

    # Add items to different batches
    processor.add_to_batch("batch1", ("batch1", "item1"), processor_func)
    processor.add_to_batch("batch1", ("batch1", "item2"), processor_func)
    processor.add_to_batch("batch2", ("batch2", "item3"), processor_func)
    processor.add_to_batch("batch2", ("batch2", "item4"), processor_func)

    # Wait for processing to complete
    assert processing_complete.wait(timeout=2.0), "Multiple batch processing did not complete within timeout"

    assert len(processed_items["batch1"]) == 2
    assert len(processed_items["batch2"]) == 2
    assert "item1" in processed_items["batch1"]
    assert "item2" in processed_items["batch1"]
    assert "item3" in processed_items["batch2"]
    assert "item4" in processed_items["batch2"]


def test_resource_optimizer_creation():
    """Test creating resource optimizer."""
    optimizer = ResourceOptimizer()
    assert optimizer.max_workers == 4
    assert isinstance(optimizer.connection_pool, ConnectionPool)
    assert isinstance(optimizer.service_cache, ServiceCache)
    assert isinstance(optimizer.batch_processor, BatchProcessor)
    assert optimizer.worker_stats == {}
    assert isinstance(optimizer._lock, threading.Lock)


def test_resource_optimizer_custom_workers():
    """Test resource optimizer with custom worker count."""
    optimizer = ResourceOptimizer(max_workers=8)
    assert optimizer.max_workers == 8


def test_optimize_worker_allocation():
    """Test worker allocation optimization."""
    optimizer = ResourceOptimizer()

    # Mock workers
    workers = [MagicMock() for _ in range(4)]

    # Mock services with different cluster types
    services = []
    for i in range(6):
        service = MagicMock()
        service.cluster_type = f"type{i % 2}"  # Alternate between type0 and type1
        services.append(service)

    optimized_workers = optimizer.optimize_worker_allocation(workers, services)

    # Should return optimized workers
    assert len(optimized_workers) <= len(workers)
    assert all(hasattr(worker, "cluster_type") for worker in optimized_workers)


@patch("subprocess.run")
def test_pre_warm_connections(mock_run):
    """Test pre-warming connections."""
    optimizer = ResourceOptimizer()

    # Mock successful kubectl command
    mock_run.return_value.returncode = 0

    cluster_names = ["cluster1", "cluster2"]
    optimizer.pre_warm_connections(cluster_names)

    # Should have called kubectl for each cluster
    assert mock_run.call_count == 2

    # Check that contexts were set
    assert optimizer.connection_pool.get_context("cluster1") == "cluster1"
    assert optimizer.connection_pool.get_context("cluster2") == "cluster2"


@patch("subprocess.run")
def test_pre_warm_connections_failure(mock_run):
    """Test pre-warming connections with failures."""
    optimizer = ResourceOptimizer()

    # Mock failed kubectl command
    mock_run.return_value.returncode = 1

    cluster_names = ["cluster1", "cluster2"]
    optimizer.pre_warm_connections(cluster_names)

    # Should have called kubectl for each cluster
    assert mock_run.call_count == 2

    # Check that contexts were not set due to failure
    assert optimizer.connection_pool.get_context("cluster1") is None
    assert optimizer.connection_pool.get_context("cluster2") is None


def test_optimize_service_execution():
    """Test service execution optimization."""
    optimizer = ResourceOptimizer()

    # Mock service item
    service_item = MagicMock()
    service_item.service_name = "test-service"
    service_item.cluster_name = "test-cluster"

    # Set context in pool
    optimizer.connection_pool.set_context("test-cluster", "test-context")

    result = optimizer.optimize_service_execution(service_item)

    # Should return the service item with context
    assert result == service_item
    assert hasattr(service_item, "kubectl_context")
    assert service_item.kubectl_context == "test-context"


def test_batch_similar_services():
    """Test batching similar services."""
    optimizer = ResourceOptimizer()

    # Create services with different cluster types and service types
    services = []
    for i in range(6):
        service = MagicMock()
        service.cluster_type = f"cluster{i % 2}"
        service.service_type = f"service{i % 3}"
        services.append(service)

    batches = optimizer.batch_similar_services(services)

    # Should have grouped services by cluster_type and service_type
    assert len(batches) > 0
    assert all(isinstance(batch, list) for batch in batches)
    assert sum(len(batch) for batch in batches) == len(services)


def test_get_performance_metrics():
    """Test getting performance metrics."""
    optimizer = ResourceOptimizer()

    # Add some test data
    optimizer.connection_pool.set_context("cluster1", "context1")
    optimizer.service_cache.set("key1", "value1")

    metrics = optimizer.get_performance_metrics()

    assert "connection_pool_size" in metrics
    assert "cache_size" in metrics
    assert "cache_hit_rate" in metrics
    assert "worker_utilization" in metrics
    assert "batch_efficiency" in metrics

    assert metrics["connection_pool_size"] == 1
    assert metrics["cache_size"] == 1


def test_cleanup():
    """Test cleanup of resources."""
    optimizer = ResourceOptimizer()

    # Add some test data
    optimizer.connection_pool.set_context("cluster1", "context1")
    optimizer.service_cache.set("key1", "value1")

    optimizer.cleanup()

    # Should clear all resources
    assert optimizer.connection_pool.contexts == {}
    assert optimizer.service_cache.cache == {}


def test_performance_profiler_creation():
    """Test creating performance profiler."""
    profiler = PerformanceProfiler()
    assert profiler.metrics == {}
    assert profiler.start_times == {}
    assert isinstance(profiler._lock, threading.Lock)


def test_start_and_end_timer():
    """Test starting and ending timers."""
    profiler = PerformanceProfiler()

    profiler.start_timer("operation1")
    time.sleep(0.01)  # Small delay
    duration = profiler.end_timer("operation1")

    assert duration > 0
    assert "operation1" in profiler.metrics
    assert len(profiler.metrics["operation1"]) == 1
    assert profiler.metrics["operation1"][0] == duration


def test_end_timer_without_start():
    """Test ending timer without starting it."""
    profiler = PerformanceProfiler()

    duration = profiler.end_timer("nonexistent")
    assert duration == 0.0


def test_get_average_time():
    """Test getting average time for an operation."""
    profiler = PerformanceProfiler()

    # Add some timing data
    profiler.metrics["operation1"] = [0.1, 0.2, 0.3]

    average = profiler.get_average_time("operation1")
    assert abs(average - 0.2) < 0.001  # Use approximate equality for floating point

    # Test with no data
    average = profiler.get_average_time("nonexistent")
    assert average == 0.0


def test_get_performance_summary():
    """Test getting performance summary."""
    profiler = PerformanceProfiler()

    # Add some timing data
    profiler.metrics["operation1"] = [0.1, 0.2, 0.3]
    profiler.metrics["operation2"] = [0.5, 0.6]

    summary = profiler.get_performance_summary()

    assert "operation1" in summary
    assert "operation2" in summary

    op1_summary = summary["operation1"]
    assert op1_summary["count"] == 3
    assert op1_summary["total_time"] == 0.6
    assert abs(op1_summary["average_time"] - 0.2) < 0.001  # Use approximate equality
    assert op1_summary["min_time"] == 0.1
    assert op1_summary["max_time"] == 0.3


def test_reset():
    """Test resetting profiler."""
    profiler = PerformanceProfiler()

    # Add some data
    profiler.start_timer("operation1")
    profiler.end_timer("operation1")
    profiler.metrics["operation2"] = [0.1, 0.2]

    profiler.reset()

    assert profiler.metrics == {}
    assert profiler.start_times == {}


def test_thread_safety():
    """Test thread safety of performance profiler."""
    profiler = PerformanceProfiler()
    results = []

    def worker(worker_id):
        for i in range(10):
            operation = f"op_{worker_id}_{i}"
            profiler.start_timer(operation)
            time.sleep(0.001)  # Small delay
            duration = profiler.end_timer(operation)
            results.append((operation, duration))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All results should have positive durations
    for operation, duration in results:
        assert duration > 0


def test_get_connection_pool():
    """Test getting global connection pool."""
    pool = get_connection_pool()
    assert isinstance(pool, ConnectionPool)


def test_get_service_cache():
    """Test getting global service cache."""
    cache = get_service_cache()
    assert isinstance(cache, ServiceCache)


def test_get_batch_processor():
    """Test getting global batch processor."""
    processor = get_batch_processor()
    assert isinstance(processor, BatchProcessor)


def test_get_resource_optimizer():
    """Test getting global resource optimizer."""
    optimizer = get_resource_optimizer()
    assert isinstance(optimizer, ResourceOptimizer)


def test_get_performance_profiler():
    """Test getting global performance profiler."""
    profiler = get_performance_profiler()
    assert isinstance(profiler, PerformanceProfiler)


def test_cleanup_optimization_resources():
    """Test cleanup of all optimization resources."""
    # This should not raise any exceptions
    cleanup_optimization_resources()


def test_full_optimization_workflow():
    """Test full optimization workflow."""
    optimizer = ResourceOptimizer()
    profiler = PerformanceProfiler()

    # Start profiling
    profiler.start_timer("total_optimization")

    # Pre-warm connections
    cluster_names = ["cluster1", "cluster2"]
    optimizer.pre_warm_connections(cluster_names)

    # Optimize worker allocation
    workers = [MagicMock() for _ in range(4)]
    services = []
    for i in range(6):
        service = MagicMock()
        service.cluster_type = f"type{i % 2}"
        services.append(service)

    optimized_workers = optimizer.optimize_worker_allocation(workers, services)

    # Batch similar services
    batches = optimizer.batch_similar_services(services)

    # Get performance metrics
    metrics = optimizer.get_performance_metrics()

    # End profiling
    total_time = profiler.end_timer("total_optimization")

    # Verify results
    assert len(optimized_workers) <= len(workers)
    assert len(batches) > 0
    assert total_time > 0
    assert "connection_pool_size" in metrics

    # Cleanup
    optimizer.cleanup()
    profiler.reset()


def test_optimization_with_caching():
    """Test optimization with caching enabled."""
    optimizer = ResourceOptimizer()

    # Mock service item
    service_item = MagicMock()
    service_item.service_name = "test-service"
    service_item.cluster_name = "test-cluster"

    # First execution (not cached)
    result1 = optimizer.optimize_service_execution(service_item)

    # Second execution (should use cache)
    result2 = optimizer.optimize_service_execution(service_item)

    # Both should return the same service item
    assert result1 == result2

    # Cleanup
    optimizer.cleanup()
