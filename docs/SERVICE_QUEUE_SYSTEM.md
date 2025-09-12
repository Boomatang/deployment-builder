# Service Queue System Documentation

## Overview

The Service Queue System is an advanced parallel processing system that efficiently executes services across multiple Kubernetes clusters. It provides queue management, load balancing, execution planning, progress monitoring, error handling, and performance optimization.

## Table of Contents

- [Architecture](#architecture)
- [Core Components](#core-components)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Usage Examples](#usage-examples)
- [Performance Optimization](#performance-optimization)
- [Error Handling](#error-handling)
- [Monitoring and Progress Tracking](#monitoring-and-progress-tracking)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Architecture

### System Overview

The Service Queue System consists of several interconnected components that work together to provide efficient parallel service execution:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service Queue │    │   Worker Pool   │    │ Load Balancer   │
│                 │    │                 │    │                 │
│ - Priority Queue│    │ - Multiple      │    │ - Round Robin   │
│ - Retry Logic   │    │   Workers       │    │ - Least Loaded │
│ - Status Track  │    │ - Service Exec  │    │ - Priority      │
│ - Thread Safe   │    │ - Error Handle  │    │   Based         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
         │Execution Planner│    │Progress Monitor │    │ Error Handler   │
         │                 │    │                 │    │                 │
         │ - Dependencies  │    │ - Real-time     │    │ - Retry Logic   │
         │ - Timeline      │    │   Progress      │    │ - Circuit       │
         │ - Optimization  │    │ - Worker Stats  │    │   Breaker       │
         │ - Parallel      │    │ - Queue Status  │    │ - Recovery      │
         │   Groups        │    │ - ETA           │    │   Operations    │
         └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Configuration Loading**: Services are loaded from configuration files
2. **Execution Planning**: Dependencies are resolved and execution order is optimized
3. **Queue Population**: Service items are added to the priority queue
4. **Worker Assignment**: Load balancer assigns services to available workers
5. **Parallel Execution**: Workers execute services simultaneously
6. **Progress Monitoring**: Real-time progress updates and status tracking
7. **Error Handling**: Failed services are retried or escalated as needed
8. **Completion**: Final status reporting and cleanup

## Core Components

### Service Queue (`queue.py`)

The central queue system that manages service execution order and status.

#### ServiceItem
```python
@dataclass
class ServiceItem:
    cluster_name: str
    cluster_type: str
    service_name: str
    service_config: ServiceConfig
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    status: ServiceStatus = ServiceStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
```

#### ServiceStatus
```python
class ServiceStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
```

#### Key Features
- **Priority Queue**: Services are executed based on priority
- **Retry Mechanism**: Automatic retry with configurable attempts
- **Status Tracking**: Real-time status updates
- **Thread Safety**: Safe for concurrent access

### Worker Pool (`queue.py`)

Manages multiple workers that execute services in parallel.

#### ServiceWorker
- **Thread Management**: Each worker runs in its own thread
- **Service Execution**: Executes services via subprocess
- **Error Handling**: Captures and reports execution errors
- **Status Reporting**: Reports worker status and utilization

#### WorkerPool
- **Worker Management**: Creates, starts, and stops workers
- **Load Distribution**: Distributes services across workers
- **Monitoring**: Tracks worker status and performance

### Load Balancer (`load_balancer.py`)

Distributes service items across available workers efficiently.

#### Strategies

**Round Robin**
- Even distribution across workers
- Simple and predictable
- Good for uniform workloads

**Least Loaded**
- Assigns to worker with least load
- Optimal resource utilization
- Good for variable workloads

**Priority Based**
- High-priority services get preference
- Ensures critical services run first
- Good for mixed priority workloads

### Execution Planner (`execution_planner.py`)

Creates optimized execution plans and resolves dependencies.

#### Features
- **Dependency Resolution**: Automatically resolves service dependencies
- **Timeline Generation**: Creates execution timeline with start/end times
- **Parallel Groups**: Groups services that can run in parallel
- **Optimization**: Optimizes execution order for maximum efficiency

#### DependencyGraph
- **Cycle Detection**: Prevents circular dependencies
- **Topological Sort**: Orders services based on dependencies
- **Ready Services**: Identifies services ready for execution

### Progress Monitor (`monitor.py`)

Provides real-time progress tracking and status updates.

#### ProgressStats
- **Completion Percentage**: Progress percentage
- **Elapsed Time**: Time since start
- **Estimated Remaining**: Estimated time to completion
- **Throughput**: Services completed per minute

#### StatusDisplay
- **Real-time Updates**: Live progress display
- **Worker Status**: Individual worker status
- **Queue Status**: Queue size and status
- **Final Summary**: Completion summary

### Error Handler (`error_handler.py`)

Comprehensive error handling and recovery mechanisms.

#### Error Classification
- **Network Errors**: Connection and timeout issues
- **Authentication Errors**: Permission and credential issues
- **Configuration Errors**: Invalid configuration
- **Resource Errors**: Memory and resource issues
- **Timeout Errors**: Service execution timeouts

#### Recovery Mechanisms
- **Automatic Retry**: Exponential backoff retry
- **Circuit Breaker**: Prevents cascading failures
- **Health Checks**: Service health monitoring
- **Recovery Operations**: Manual recovery procedures

### Performance Optimization (`optimization.py`)

Various optimization strategies for improved performance.

#### ConnectionPool
- **Resource Management**: Efficient connection reuse
- **Context Management**: Thread-safe context handling
- **Cleanup**: Automatic resource cleanup

#### ServiceCache
- **TTL-based Caching**: Time-to-live based caching
- **Memory Management**: Efficient memory usage
- **Cache Invalidation**: Automatic cache cleanup

#### BatchProcessor
- **Batch Processing**: Groups similar operations
- **Timeout Handling**: Batch timeout management
- **Thread Safety**: Safe concurrent batch processing

#### ResourceOptimizer
- **Worker Allocation**: Optimizes worker distribution
- **Pre-warming**: Pre-warms connections
- **Performance Metrics**: Tracks optimization metrics

### Performance Benchmarking (`benchmark.py`)

Comprehensive performance testing and validation.

#### PerformanceBenchmark
- **Load Testing**: Tests with various load levels
- **Throughput Testing**: Measures operations per second
- **Latency Testing**: Measures response times
- **Memory Testing**: Monitors memory usage
- **Scalability Testing**: Tests with different worker counts

#### SystemValidator
- **End-to-end Testing**: Full system validation
- **Integration Testing**: Component integration tests
- **Performance Validation**: Performance requirement validation
- **Error Handling Validation**: Error handling tests

## Configuration

### Basic Configuration

```toml
[general]
name = "my-deployment"
max_workers = 8  # Number of parallel workers

[clusters]
[clusters.worker]
count = 3

[clusters.database]
count = 2

# Global services
[services]
[services.health-check]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get nodes"
priority = 1
estimated_duration = 30.0

# Cluster-specific services
[clusters.worker.services]
[clusters.worker.services.monitoring]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -n monitoring"
priority = 2
estimated_duration = 60.0
dependencies = ["health-check"]
```

### Advanced Configuration

```toml
[general]
name = "advanced-deployment"
max_workers = 16
load_balancing_strategy = "least_loaded"

[clusters]
[clusters.api-gateway]
enable = true

[clusters.worker]
count = 5

[clusters.database]
count = 3

# High-priority services
[services]
[services.critical-health-check]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get nodes"
priority = 1
estimated_duration = 15.0

[services.security-scan]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -n security"
priority = 2
estimated_duration = 120.0
dependencies = ["critical-health-check"]

# Cluster-specific services with dependencies
[clusters.worker.services]
[clusters.worker.services.app-deploy]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl apply -f app.yaml"
priority = 3
estimated_duration = 45.0
dependencies = ["security-scan"]

[clusters.worker.services.app-verify]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -l app=myapp"
priority = 4
estimated_duration = 30.0
dependencies = ["app-deploy"]
```

## CLI Commands

### Create Command

```bash
# Basic cluster creation
poetry run deploy create

# With custom worker count
poetry run deploy create --workers 16

# With specific load balancer
poetry run deploy create --load-balancer least_loaded

# Preview execution plan
poetry run deploy create --dry-run

# With custom config
poetry run deploy create --config my-config.toml
```

### Plan Command

```bash
# Basic execution plan
poetry run deploy plan

# Detailed timeline
poetry run deploy plan --timeline

# Show dependencies
poetry run deploy plan --dependencies

# Filter by cluster types
poetry run deploy plan --cluster-types worker,database

# All options combined
poetry run deploy plan --config my-config.toml --timeline --dependencies --cluster-types worker
```

### Remove Command

```bash
# Remove clusters
poetry run deploy remove

# Force removal without confirmation
poetry run deploy remove --force

# Preview removal
poetry run deploy remove --dry-run
```

### Defaults Command

```bash
# Show default configuration values
poetry run deploy defaults
```

## Usage Examples

### Basic Usage

```bash
# 1. Create a configuration file
cat > my-config.toml << EOF
[general]
name = "my-app"
max_workers = 4

[clusters]
[clusters.web]
count = 2

[clusters.api]
count = 3

[services]
[services.health-check]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get nodes"
priority = 1
EOF

# 2. Preview the execution plan
poetry run deploy plan --config my-config.toml --timeline

# 3. Create clusters with services
poetry run deploy create --config my-config.toml
```

### Advanced Usage

```bash
# 1. Create a complex configuration
cat > complex-config.toml << EOF
[general]
name = "microservices"
max_workers = 8
load_balancing_strategy = "least_loaded"

[clusters]
[clusters.gateway]
enable = true

[clusters.user-service]
count = 2

[clusters.order-service]
count = 2

[clusters.database]
count = 1

[services]
[services.gateway-health]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -n gateway"
priority = 1
estimated_duration = 30.0

[clusters.user-service.services]
[clusters.user-service.services.deploy]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl apply -f user-service.yaml"
priority = 2
estimated_duration = 60.0
dependencies = ["gateway-health"]
EOF

# 2. Show detailed execution plan
poetry run deploy plan --config complex-config.toml --timeline --dependencies

# 3. Create with custom settings
poetry run deploy create --config complex-config.toml --workers 12 --load-balancer priority_based
```

### Monitoring and Debugging

```bash
# 1. Create with verbose logging
poetry run deploy --log-level=debug create --config my-config.toml

# 2. Monitor progress in real-time
tail -f logs/deployment_builder.log

# 3. Check specific cluster status
kubectl --kubeconfig=kubeconfigs/my-app-web-1.kubeconfig get pods
```

## Performance Optimization

### Worker Configuration

```toml
[general]
# Adjust based on your system
max_workers = 8  # CPU cores * 2 for I/O bound workloads
```

**Guidelines:**
- **CPU-bound**: Set to number of CPU cores
- **Memory-bound**: Set to 2-4 workers
- **I/O-bound**: Set to 8-16 workers

### Load Balancing Strategy

```toml
[general]
load_balancing_strategy = "least_loaded"  # round_robin, least_loaded, priority_based
```

**Strategy Selection:**
- **Round Robin**: Uniform workloads, simple distribution
- **Least Loaded**: Variable workloads, optimal utilization
- **Priority Based**: Mixed priorities, critical services first

### Service Optimization

```toml
# Optimize service configuration
[services.optimized-service]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods --no-headers"  # Faster than with headers
priority = 1
estimated_duration = 10.0  # Accurate estimates help planning
```

### Caching and Batching

The system automatically optimizes:
- **Connection Pooling**: Reuses connections efficiently
- **Service Caching**: Caches service results with TTL
- **Batch Processing**: Groups similar operations
- **Resource Optimization**: Optimizes worker allocation

## Error Handling

### Automatic Retry

```toml
# Services are automatically retried on failure
[services.retry-service]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods"
# Will retry up to 3 times with exponential backoff
```

### Circuit Breaker

The system implements circuit breaker pattern:
- **CLOSED**: Normal operation
- **OPEN**: Circuit open, services fail fast
- **HALF_OPEN**: Testing if service is recovered

### Error Classification

Errors are automatically classified:
- **Network**: Connection issues, timeouts
- **Authentication**: Permission errors
- **Configuration**: Invalid configuration
- **Resource**: Memory, CPU issues
- **Timeout**: Service execution timeouts

### Recovery Operations

```bash
# Manual recovery if needed
poetry run deploy create --config my-config.toml --force
```

## Monitoring and Progress Tracking

### Real-time Progress

The system provides real-time progress updates:

```
Service Queue System Progress
============================
Total Services: 15
Completed: 8 (53%)
Running: 3 (20%)
Pending: 4 (27%)
Failed: 0 (0%)

Worker Status:
Worker 1: IDLE (0 services)
Worker 2: RUNNING (1 service)
Worker 3: RUNNING (1 service)
Worker 4: RUNNING (1 service)

Estimated Completion: 2m 30s
```

### Queue Status

```bash
# Monitor queue status
poetry run deploy plan --config my-config.toml
```

### Performance Metrics

The system tracks:
- **Throughput**: Services completed per minute
- **Latency**: Average service execution time
- **Error Rate**: Percentage of failed services
- **Worker Utilization**: Worker efficiency
- **Memory Usage**: System memory consumption

### Logging

```bash
# Enable debug logging
poetry run deploy --log-level=debug create --config my-config.toml

# View logs
tail -f logs/deployment_builder.log
```

## Best Practices

### Service Design

1. **Idempotent Commands**: Use commands that can be safely retried
2. **Fast Execution**: Keep service execution times reasonable
3. **Clear Dependencies**: Define clear service dependencies
4. **Accurate Estimates**: Provide accurate duration estimates

### Configuration

1. **Appropriate Workers**: Set worker count based on system resources
2. **Load Balancing**: Choose appropriate load balancing strategy
3. **Service Priorities**: Use priorities to control execution order
4. **Dependencies**: Minimize dependencies for better parallelism

### Error Handling

1. **Retry Logic**: Let the system handle retries automatically
2. **Error Monitoring**: Monitor error rates and patterns
3. **Circuit Breaker**: Allow circuit breaker to prevent cascading failures
4. **Recovery**: Use recovery operations when needed

### Performance

1. **Resource Monitoring**: Monitor system resources during execution
2. **Worker Tuning**: Adjust worker count based on performance
3. **Service Optimization**: Optimize service commands for speed
4. **Caching**: Leverage automatic caching and batching

## Troubleshooting

### Common Issues

#### High Error Rates
```bash
# Check service commands
poetry run deploy plan --config my-config.toml --dependencies

# Enable debug logging
poetry run deploy --log-level=debug create --config my-config.toml
```

#### Slow Performance
```bash
# Check worker utilization
poetry run deploy plan --config my-config.toml

# Adjust worker count
poetry run deploy create --config my-config.toml --workers 16
```

#### Memory Issues
```bash
# Monitor memory usage
poetry run deploy --log-level=debug create --config my-config.toml

# Reduce worker count
poetry run deploy create --config my-config.toml --workers 4
```

#### Service Dependencies
```bash
# Check dependency resolution
poetry run deploy plan --config my-config.toml --dependencies

# Verify service names in dependencies
```

### Debug Commands

```bash
# Show execution plan
poetry run deploy plan --config my-config.toml --timeline --dependencies

# Dry run with verbose logging
poetry run deploy --log-level=debug create --config my-config.toml --dry-run

# Check configuration
poetry run deploy defaults
```

### Performance Analysis

```bash
# Run performance benchmarks
poetry run python -c "
from deployment_builder.benchmark import run_full_validation
results = run_full_validation()
print('Validation completed')
"

# Check system validation
poetry run python -c "
from deployment_builder.benchmark import get_validator
validator = get_validator()
results = validator.run_validation_suite()
print(f'Validation results: {len(results)} tests')
"
```

## Conclusion

The Service Queue System provides a powerful and flexible way to execute services across multiple Kubernetes clusters with parallel processing, comprehensive monitoring, and robust error handling. By following the best practices and using the provided tools, you can achieve significant performance improvements and reliable service execution.

For more information, see:
- [README.md](../README.md) - Main project documentation
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Best practices for dynamic cluster types
- [VALIDATION_RULES.md](VALIDATION_RULES.md) - Configuration validation rules
