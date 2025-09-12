# Deployment Builder

A command-line tool for managing kind Kubernetes clusters using configuration files. Built with Python and Click.

## Features

- **Create multiple kind clusters** from configuration files (with parallel execution)
- **Remove multiple kind clusters** based on configuration (with parallel execution)
- **Show default configuration** - Display all default configuration values
- **Kubeconfig management** - Automatic kubeconfig file creation and cleanup for each cluster
- **Kind configuration management** - Automatic kind cluster configuration file generation and cleanup
- **Multiple config formats** - TOML (default), JSON and YAML support
- **Structured configuration** - New structured format with `[general]` and `[clusters.*]` sections
- **Legacy format support** - Backward compatibility with old configuration format
- **Dry run mode** - Preview changes before execution
- **Flexible config discovery** - Automatic config file detection
- **Environment variable support** - Set config file via `DEPLOYMENT_CONFIG` envvar
- **Comprehensive logging** - Detailed logs written to `logs/deployment_builder.log`
- **Execution timing** - Total execution time and per-cluster timing reports
- **Error handling** - Comprehensive error messages and validation
- **Configurable parallelism** - Control the number of parallel workers via `max_workers`
- **Service execution** - Run commands against clusters after creation
- **Global services** - Services that run on all clusters
- **Cluster-specific services** - Services that run only on specific cluster types
- **Dynamic cluster types** - Define any cluster types you need for your specific use case
- **Service Queue System** - Advanced queue-based service execution with parallel processing
- **Execution planning** - Preview service execution order and dependencies
- **Load balancing** - Multiple strategies for distributing service load across workers
- **Progress monitoring** - Real-time progress tracking and status updates
- **Error recovery** - Automatic retry mechanisms and circuit breaker patterns
- **Performance optimization** - Caching, batching, and resource optimization

## Installation

### Prerequisites

- Python 3.13+
- Poetry (for development)
- [kind](https://kind.sigs.k8s.io/) - Kubernetes in Docker

### Install from source

```bash
git clone <repository-url>
cd deployment-builder
pip install -e .
```

### Development setup

```bash
git clone <repository-url>
cd deployment-builder
poetry install
```

## Kind Integration

This tool integrates with [kind](https://kind.sigs.k8s.io/) to create and manage multiple local Kubernetes clusters. The tool wraps the `kind` CLI commands:

- `deploy create` → `kind create cluster --name <cluster_name>` (for each cluster)
- `deploy remove` → `kind delete cluster --name <cluster_name>` (for each cluster)

### Multi-Cluster Configuration

The tool supports creating multiple clusters based on configuration with **dynamic cluster types**. You can define any cluster types you need for your specific use case.

#### Dynamic Cluster Types

The tool supports two types of cluster configurations:

1. **Single Cluster Types** (`enable: true, count: 1`)
   - Single cluster instances
   - Name: `{prefix}-{cluster_type}`
   - Example: `my-project-gateway`, `my-project-metrics`

2. **Multiple Cluster Types** (`count: <number>`)
   - Multiple cluster instances
   - Names: `{prefix}-{cluster_type}-1`, `{prefix}-{cluster_type}-2`, etc.
   - Example: `my-project-worker-1`, `my-project-worker-2`, `my-project-worker-3`

#### Cluster Type Rules

- **Names**: Must be alphanumeric with hyphens and underscores only
- **Length**: 1-50 characters
- **Uniqueness**: Each cluster type name must be unique
- **Flexibility**: No limit on the number of cluster types you can define
- **Naming**: Use descriptive names that reflect your architecture (e.g., `gateway`, `worker`, `database`, `cache`)

#### Configuration Structure

```toml
[general]
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"
kubeconfig_path = "kubeconfigs"
kind_config_path = "kind-configs"
max_workers = 4

[clusters]
# Single cluster types (enable: true, count: 1)
[clusters.gateway]
enable = true
count = 1

[clusters.metrics]
enable = true
count = 1

# Multiple cluster types (count: number)
[clusters.worker]
count = 3

[clusters.database]
count = 2

[clusters.cache]
count = 1
```

This creates 7 clusters:
- `my-project-gateway` (single cluster)
- `my-project-metrics` (single cluster)
- `my-project-worker-1`, `my-project-worker-2`, `my-project-worker-3` (multiple clusters)
- `my-project-database-1`, `my-project-database-2` (multiple clusters)
- `my-project-cache` (single cluster)

The prefix is automatically sanitized to be valid for kind (lowercase, alphanumeric, hyphens only).

## Parallel Execution

The tool automatically uses parallel execution to speed up cluster operations:

### Performance Benefits

- **Faster Operations**: Multiple clusters are created/deleted simultaneously
- **Optimal Concurrency**: Automatically determines the best number of parallel workers
- **Progress Tracking**: Real-time progress updates in logs
- **Resource Efficient**: Uses ThreadPoolExecutor for optimal resource usage

### Concurrency Control

- **Small Clusters (≤2)**: Sequential execution for simplicity
- **Large Clusters (>2)**: Parallel execution with configurable workers (default: 4)
- **Configurable Workers**: Set `max_workers` in configuration to control parallelism
- **Progress Indicators**: Shows completion progress in logs
- **Error Handling**: Individual cluster failures don't stop other operations

### Example Performance

```bash
# 7 clusters created in parallel
Creating 7 kind clusters in parallel...
Starting parallel execution for clusters: my-project-metrics, my-project-primary-1, my-project-primary-2, my-project-secondary-1, my-project-standalone-1, my-project-standalone-2, my-project-standalone-3
🚀 Starting parallel creation of cluster: my-project-metrics
🚀 Starting parallel creation of cluster: my-project-primary-1
🚀 Starting parallel creation of cluster: my-project-primary-2
...
✓ Successfully created 7 clusters: my-project-metrics, my-project-primary-1, ...
⏱️  Total execution time: 2m 15.30s
```

**Log Evidence of Parallel Execution:**
```
2025-09-09 23:35:35 - INFO - Deleting 2 clusters in parallel (2 workers)
2025-09-09 23:35:35 - DEBUG - Starting parallel deletion of cluster: my-project-metrics
2025-09-09 23:35:35 - DEBUG - Starting parallel deletion of cluster: my-project-primary-1
```

Notice both clusters start at the exact same timestamp, proving true parallel execution.

## Kubeconfig Management

The tool automatically manages kubeconfig files for each cluster, making it easy to work with multiple clusters.

### Features

- **Automatic Creation**: Kubeconfig files are created for each cluster after successful creation
- **Individual Files**: Each cluster gets its own kubeconfig file named `{cluster_name}.kubeconfig`
- **Configurable Path**: Set the kubeconfig directory in your configuration file
- **Automatic Cleanup**: Kubeconfig files are removed when clusters are deleted
- **Directory Management**: Kubeconfig directory is created automatically if it doesn't exist
- **Command Integration**: `--kubeconfig` flag is used with kind commands to specify the correct kubeconfig file

### Configuration

Add the `kubeconfig_path` field to your configuration:

```toml
[general]
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"
kubeconfig_path = "kubeconfigs"  # Default: "kubeconfigs"

[clusters]
[clusters.metrics]
enable = true

[clusters.primary]
count = 2

[clusters.secondary]
count = 1

[clusters.standalone]
count = 3
```

### Kubeconfig Files

For the above configuration, the following kubeconfig files will be created:

```
kubeconfigs/
├── my-project-metrics.kubeconfig
├── my-project-primary-1.kubeconfig
├── my-project-primary-2.kubeconfig
├── my-project-secondary-1.kubeconfig
├── my-project-standalone-1.kubeconfig
├── my-project-standalone-2.kubeconfig
└── my-project-standalone-3.kubeconfig
```

### Using Kubeconfig Files

You can use these kubeconfig files with `kubectl`:

```bash
# Use a specific cluster's kubeconfig
kubectl --kubeconfig=kubeconfigs/my-project-metrics.kubeconfig get nodes

# Or set KUBECONFIG environment variable
export KUBECONFIG=kubeconfigs/my-project-metrics.kubeconfig
kubectl get nodes
```

### Kubeconfig Command Integration

The tool automatically uses the `--kubeconfig` flag when running kind commands, ensuring that each cluster operation uses the correct kubeconfig file:

- **During Cluster Creation**: The `--kubeconfig` flag is added to point to the cluster's kubeconfig file when running `kind create cluster`
- **During Cluster Deletion**: The `--kubeconfig` flag is added to point to the cluster's kubeconfig file when running `kind delete cluster`
- **Automatic Management**: This happens transparently - you don't need to manually specify kubeconfig files
- **Parallel Safety**: Each parallel operation uses its own kubeconfig file, preventing conflicts

This ensures that kind commands always operate on the correct cluster context, even when managing multiple clusters simultaneously, and prevents kubeconfig file lock conflicts during parallel operations.

## Service Queue System

The deployment-builder includes an advanced Service Queue System that provides efficient parallel execution of services across multiple clusters with comprehensive monitoring and error handling.

### Key Features

- **Parallel Service Execution**: Services are executed in parallel across multiple workers
- **Queue Management**: Centralized queue system for managing service execution order
- **Load Balancing**: Multiple strategies for distributing service load efficiently
- **Execution Planning**: Preview service execution order and dependencies
- **Progress Monitoring**: Real-time progress tracking and status updates
- **Error Recovery**: Automatic retry mechanisms and circuit breaker patterns
- **Performance Optimization**: Caching, batching, and resource optimization

### Queue System Components

#### Service Queue
- **Priority-based execution**: Services can be assigned priorities for execution order
- **Retry mechanism**: Automatic retry with configurable attempts and delays
- **Status tracking**: Real-time status updates (PENDING, RUNNING, COMPLETED, FAILED)
- **Thread-safe operations**: Safe for concurrent access from multiple workers

#### Worker Pool
- **Parallel workers**: Multiple workers process services simultaneously
- **Load balancing**: Services are distributed across available workers
- **Worker monitoring**: Real-time worker status and utilization tracking
- **Graceful shutdown**: Clean worker termination and resource cleanup

#### Load Balancing Strategies
- **Round Robin**: Even distribution across workers
- **Least Loaded**: Assign services to workers with the least load
- **Priority Based**: High-priority services get preference

#### Execution Planning
- **Dependency resolution**: Automatic resolution of service dependencies
- **Timeline generation**: Estimated execution timeline with start/end times
- **Parallel groups**: Services that can run in parallel are grouped together
- **Optimization**: Execution order is optimized for maximum efficiency

### Configuration

The Service Queue System can be configured in your configuration file:

```toml
[general]
name = "my-deployment"
max_workers = 8  # Number of parallel workers

[clusters]
[clusters.worker]
count = 3

[clusters.database]
count = 2

# Global services (run on all clusters)
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

### CLI Commands

#### Create Command with Queue Options
```bash
# Create clusters with custom worker count
poetry run deploy create --workers 8

# Create clusters with specific load balancer
poetry run deploy create --load-balancer least_loaded

# Preview execution plan in dry-run mode
poetry run deploy create --dry-run
```

#### Plan Command
```bash
# Show basic execution plan
poetry run deploy plan

# Show detailed timeline
poetry run deploy plan --timeline

# Show service dependencies
poetry run deploy plan --dependencies

# Filter by cluster types
poetry run deploy plan --cluster-types worker,database
```

### Performance Benefits

- **Faster Execution**: Parallel processing significantly reduces total execution time
- **Better Resource Utilization**: Workers are efficiently utilized across all clusters
- **Scalability**: System scales well with large numbers of clusters and services
- **Reliability**: Comprehensive error handling and recovery mechanisms
- **Visibility**: Clear execution planning and progress monitoring

### Error Handling and Recovery

- **Automatic Retry**: Failed services are automatically retried with exponential backoff
- **Circuit Breaker**: Prevents cascading failures by temporarily stopping execution on failing clusters
- **Error Classification**: Errors are classified by type and severity for appropriate handling
- **Recovery Operations**: Health checks and recovery operations for failed services
- **Error Statistics**: Comprehensive error tracking and reporting

### Monitoring and Progress Tracking

- **Real-time Progress**: Live progress updates during execution
- **Worker Utilization**: Monitor worker status and utilization
- **Queue Status**: Track queue size, completed, failed, and running services
- **Execution Timeline**: Estimated completion times and progress percentages
- **Performance Metrics**: Throughput, latency, and error rate monitoring

## Kind Configuration Management

The tool automatically generates and manages kind cluster configuration files, allowing you to customize cluster settings according to the [kind configuration documentation](https://kind.sigs.k8s.io/docs/user/configuration/).

### Features

- **Automatic Generation**: Kind configuration files are generated for each cluster based on your configuration
- **Individual Files**: Each cluster gets its own configuration file named `{cluster_name}-kind-config.yaml`
- **Configurable Path**: Set the kind config directory in your configuration file
- **Automatic Cleanup**: Kind config files are removed when clusters are deleted
- **Directory Management**: Kind config directory is created automatically if it doesn't exist
- **YAML Format**: Configuration files follow the official kind YAML format

### Configuration

Add the `kind_config_path` field to your configuration:

```toml
[general]
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"
kubeconfig_path = "kubeconfigs"
kind_config_path = "kind-configs"  # Default: "kind-configs"

[clusters]
[clusters.metrics]
enable = true

[clusters.primary]
count = 2

[clusters.secondary]
count = 1

[clusters.standalone]
count = 3
```

### Kind Configuration Files

For the above configuration, the following kind config files will be created:

```
kind-configs/
├── my-project-metrics-kind-config.yaml
├── my-project-primary-1-kind-config.yaml
├── my-project-primary-2-kind-config.yaml
├── my-project-secondary-1-kind-config.yaml
├── my-project-standalone-1-kind-config.yaml
├── my-project-standalone-2-kind-config.yaml
└── my-project-standalone-3-kind-config.yaml
```

### Supported Kind Configuration Options

The tool supports all standard kind configuration options:

- **Networking**: IP family, API server address/port, pod/service subnets
- **Feature Gates**: Kubernetes feature gates
- **Runtime Config**: API server runtime configuration
- **Nodes**: Custom node configurations, extra mounts, port mappings, labels
- **Kubeadm Patches**: Custom kubeadm configuration patches

### Example Kind Config File

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: my-project-metrics
networking:
  ipFamily: ipv4
  apiServerAddress: 127.0.0.1
featureGates:
  CSIMigration: true
```

### Automatic Cleanup

When you delete clusters, the corresponding kubeconfig and kind config files are automatically removed:

```bash
poetry run deploy remove --config examples/config.toml
# Removes clusters, kubeconfig files, and kind config files
```

## Usage

### Basic Commands

#### Using Poetry (Recommended)

```bash
# Show help
poetry run deploy --help

# Show default configuration values
poetry run deploy defaults

# Create multiple kind clusters
poetry run deploy create

# Remove multiple kind clusters
poetry run deploy remove

# Set log level
poetry run deploy --log-level=debug create --dry-run
```

#### Using Python Module

```bash
# Show help
python -m deployment_builder --help

# Show default configuration
python -m deployment_builder defaults

# Create deployment
python -m deployment_builder create

# Remove deployment
python -m deployment_builder remove
```

### Command Options

#### Global Options

```bash
poetry run deploy [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options:
  --log-level [debug|info|warning|error|critical]
                                  Set the logging level for the tool.
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

#### Create Command

```bash
poetry run deploy create [OPTIONS]

Options:
  -c, --config PATH  Path to configuration file. If not provided, looks for
                     config files in current directory. Can also be set via
                     DEPLOYMENT_CONFIG environment variable.
  -n, --dry-run      Show what would be created without actually creating it.
  -w, --workers INTEGER
                     Number of workers for parallel service execution.
                     Overrides config value.
  --load-balancer [round_robin|least_loaded|priority_based]
                     Load balancing strategy for service execution.
                     Overrides config value.
  --help             Show this message and exit.
```

#### Remove Command

```bash
poetry run deploy remove [OPTIONS]

Options:
  -c, --config PATH  Path to configuration file. If not provided, looks for
                     config files in current directory. Can also be set via
                     DEPLOYMENT_CONFIG environment variable.
  -n, --dry-run      Show what would be removed without actually removing it.
  -f, --force        Force removal without confirmation.
  --help             Show this message and exit.
```

#### Plan Command

```bash
poetry run deploy plan [OPTIONS]

Options:
  -c, --config PATH  Path to configuration file. If not provided, looks for
                     config files in current directory. Can also be set via
                     DEPLOYMENT_CONFIG environment variable.
  -t, --timeline     Show detailed execution timeline with start/end times.
  -d, --dependencies Show service dependencies and relationships.
  --cluster-types TEXT
                     Filter by specific cluster types (comma-separated).
  --help             Show this message and exit.
```

#### Defaults Command

```bash
poetry run deploy defaults

Description:
  Show the default configuration values used by the tool.
  
  This command displays all default configuration values in a dot-separated
  format, making it easy to understand what values will be used when no
  configuration file is provided or when configuration values are not specified.
  
  Example output:
  general.name = default-deployment
  general.version = 1.0.0
  general.max_workers = 4
  clusters.metrics.enable = False
  clusters.standalone.count = 0
```

## Configuration Files

The tool supports TOML (default), JSON, and YAML configuration files with multi-cluster support. Configuration files are automatically discovered in the current directory, or you can specify a custom path using the `--config` flag or the `DEPLOYMENT_CONFIG` environment variable.

### New Structured Configuration Format (Recommended)

```toml
[general]
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"
kubeconfig_path = "kubeconfigs"
kind_config_path = "kind-configs"
max_workers = 4

[clusters]
# Single cluster types (enable: true, count: 1)
[clusters.gateway]
enable = true
count = 1

[clusters.metrics]
enable = true
count = 1

# Multiple cluster types (count: number)
[clusters.worker]
count = 3

[clusters.database]
count = 2

[clusters.cache]
count = 1

# Global services (run on all clusters)
[services]
[services.pods]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -n kube-system"

[services.nodes]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get nodes"

# Cluster-specific services (run only on primary clusters)
[clusters.primary.services]
[clusters.primary.services.namespaces]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get namespaces"
```

### Legacy Configuration Format (Still Supported)

```toml
# Basic project information
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"

# Kubeconfig configuration
kubeconfig_path = "kubeconfigs"  # Default: "kubeconfigs"

# Kind configuration
kind_config_path = "kind-configs"  # Default: "kind-configs"

# Multi-cluster configuration
[clusters]
metrics = true      # Create metrics cluster
primary = 2         # Create 2 primary clusters
secondary = 1       # Create 1 secondary cluster
standalone = 3      # Create 3 standalone clusters
```

Both formats create 7 clusters:
- `my-project-metrics`
- `my-project-primary-1`, `my-project-primary-2`
- `my-project-secondary-1`
- `my-project-standalone-1`, `my-project-standalone-2`, `my-project-standalone-3`

### Configuration Features

#### General Section (`[general]`)
- **`name`**: Deployment name (default: "default-deployment")
- **`version`**: Deployment version (default: "1.0.0")
- **`environment`**: Environment type (default: "development")
- **`prefix`**: Cluster name prefix (default: "default")
- **`kubeconfig_path`**: Directory for kubeconfig files (default: "kubeconfigs")
- **`kind_config_path`**: Directory for kind config files (default: "kind-configs")
- **`max_workers`**: Number of parallel workers (default: 4)

#### Clusters Section (`[clusters]`)
The clusters section supports **dynamic cluster types**. You can define any cluster types you need:

- **`[clusters.{cluster_type}]`**: Cluster type configuration
  - `enable`: Enable the cluster type (boolean) - for single clusters
  - `count`: Number of clusters to create (integer) - for multiple clusters
  - **Cluster Type Rules**:
    - Names must be alphanumeric with hyphens and underscores only
    - Length: 1-50 characters
    - Each cluster type name must be unique
    - No limit on the number of cluster types

**Examples:**
- `[clusters.gateway]` with `enable = true` → creates `{prefix}-gateway`
- `[clusters.worker]` with `count = 3` → creates `{prefix}-worker-1`, `{prefix}-worker-2`, `{prefix}-worker-3`
- `[clusters.database]` with `count = 1` → creates `{prefix}-database`

#### Services Section (`[services]`)
- **Global Services**: Services that run on all clusters
  - `[services.service_name]`: Service configuration
    - `kubeconfig.flag`: Kubeconfig flag for the command (default: "--kubeconfig")
    - `cmd`: Command to execute against the cluster

#### Cluster-Specific Services
- **Per-Cluster Services**: Services that run only on specific cluster types
  - `[clusters.cluster_type.services.service_name]`: Cluster-specific service configuration
    - `kubeconfig.flag`: Kubeconfig flag for the command (default: "--kubeconfig")
    - `cmd`: Command to execute against the cluster

#### Backward Compatibility
The tool maintains full backward compatibility with the legacy configuration format. You can mix and match formats, and the tool will automatically detect and handle both formats correctly.

### Supported File Names

The tool looks for these files in order (TOML files are prioritized):
- `config.toml`
- `deployment.toml`
- `config.json`
- `config.yaml`
- `config.yml`
- `deployment.json`
- `deployment.yaml`
- `deployment.yml`

### Configuration Format

#### TOML Example (`config.toml`) - New Structured Format

```toml
[general]
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"
kubeconfig_path = "kubeconfigs"
kind_config_path = "kind-configs"
max_workers = 4

[clusters]
[clusters.metrics]
enable = true

[clusters.primary]
count = 2

[clusters.secondary]
count = 1

[clusters.standalone]
count = 3
```

#### JSON Example (`config.json`)

```json
{
  "general": {
    "name": "my-deployment",
    "version": "1.0.0",
    "environment": "production",
    "prefix": "my-project",
    "kubeconfig_path": "kubeconfigs",
    "kind_config_path": "kind-configs",
    "max_workers": 4
  },
  "clusters": {
    "gateway": {
      "enable": true
    },
    "metrics": {
      "enable": true
    },
    "worker": {
      "count": 3
    },
    "database": {
      "count": 2
    },
    "cache": {
      "count": 1
    }
  }
}
```

#### YAML Example (`deployment.yaml`)

```yaml
general:
  name: my-deployment
  version: 1.0.0
  environment: production
  prefix: my-project
  kubeconfig_path: kubeconfigs
  kind_config_path: kind-configs
  max_workers: 4

clusters:
  gateway:
    enable: true
  metrics:
    enable: true
  worker:
    count: 3
  database:
    count: 2
  cache:
    count: 1
```

## Example Configurations

The `examples/` directory contains sample configuration files in all supported formats and various use cases:

### Basic Examples
- `examples/config.toml` - Basic TOML configuration (new structured format)
- `examples/deployment.toml` - Advanced TOML configuration (new structured format)
- `examples/config.json` - Basic JSON configuration (new structured format)
- `examples/deployment.yaml` - Advanced YAML configuration (new structured format)

### Use Case Examples
- `examples/simple.toml` - Simple 3-cluster setup for beginners
- `examples/dynamic-clusters.toml` - Dynamic cluster types demonstration
- `examples/microservices.toml` - Microservices architecture with multiple services
- `examples/edge-computing.toml` - Edge computing platform with regional clusters
- `examples/development.toml` - Development environment with testing clusters
- `examples/high-availability.toml` - High-availability system with redundancy

All example files use the new structured configuration format with `[general]` and `[clusters.*]` sections. You can copy any of these files to your project directory and customize them for your needs.

## Documentation

Additional documentation is available in the `docs/` directory:

- **[Best Practices](docs/BEST_PRACTICES.md)** - Guidelines for using dynamic cluster types effectively
- **[Validation Rules](docs/VALIDATION_RULES.md)** - Complete validation rules and error messages

## Examples

### Using Default Configuration

```bash
# Show default configuration values
poetry run deploy defaults

# Create a deployment using the default config file
poetry run deploy create

# Remove the deployment
poetry run deploy remove
```

### Viewing Default Configuration

The `defaults` command shows all default configuration values in a dot-separated format:

```bash
$ poetry run deploy defaults
Default Configuration Values:
==================================================
general.environment = development
general.kind_config_path = kind-configs
general.kubeconfig_path = kubeconfigs
general.max_workers = 4
general.name = default-deployment
general.prefix = default
general.version = 1.0.0
```

**Note**: The `defaults` command shows only the general configuration values. Cluster types are defined dynamically in your configuration file - there are no default cluster types. You define exactly the cluster types you need for your specific use case.

### Using Custom Configuration

```bash
# Create with a specific config file
poetry run deploy create --config /path/to/my-config.yaml

# Remove with a specific config file
poetry run deploy remove --config /path/to/my-config.json
```

### Using Environment Variables

```bash
# Set config file via environment variable
export DEPLOYMENT_CONFIG=/path/to/my-config.toml
poetry run deploy create

# Or use inline environment variable
DEPLOYMENT_CONFIG=examples/deployment.toml poetry run deploy create --dry-run
```

**Note**: Command-line options take precedence over environment variables. If both are provided, the `--config` flag will be used.

### Dry Run Mode

```bash
# Preview what would be created
poetry run deploy create --dry-run

# Preview what would be removed
poetry run deploy remove --dry-run
```

### Force Removal

```bash
# Remove without confirmation prompt
poetry run deploy remove --force
```

## Execution Timing

The tool provides detailed timing reports for all operations to help you understand performance characteristics.

### Timing Features

- **Total Execution Time**: Shows the complete time for each command
- **Per-Cluster Timing**: When processing multiple clusters, shows average time per cluster
- **Human-Readable Format**: Times are displayed in seconds, minutes, or hours as appropriate
- **Log Integration**: Timing information is also logged to the log file

### Timing Report Examples

```bash
# Dry run with timing
$ poetry run deploy create --config examples/config.toml --dry-run
...
⏱️  Total execution time: 0.00 seconds

# Actual cluster creation with timing
$ poetry run deploy create --config examples/config.toml
Creating 7 kind clusters...
✓ Successfully created 7 clusters: my-project-metrics, my-project-primary-1, ...
⏱️  Total execution time: 2m 15.30s
```

### Log File Timing

Timing information is also logged to the log file with additional details:

```
2025-09-09 23:23:57 - INFO - Timing Report: create command completed successfully in 2m 15.30s (7 clusters)
2025-09-09 23:23:57 - INFO - Average time per cluster: 19.33 seconds
```

## Logging

The deployment-builder tool provides comprehensive logging for debugging and monitoring:

### Log File Location

- **Default location**: `logs/deployment_builder.log` in the current directory
- **Log rotation**: Files are rotated when they reach 10MB (5 backup files kept)
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Log Level Control

You can control the verbosity of logging using the `--log-level` global flag:

```bash
# Debug level - most verbose (shows all messages)
poetry run deploy --log-level=debug create --dry-run

# Info level - default (shows INFO, WARNING, ERROR, CRITICAL)
poetry run deploy --log-level=info create --dry-run

# Warning level - only warnings and errors
poetry run deploy --log-level=warning create --dry-run

# Error level - only errors and critical messages
poetry run deploy --log-level=error create --dry-run

# Critical level - only critical messages
poetry run deploy --log-level=critical create --dry-run
```

**Available log levels** (from most to least verbose):
- `DEBUG` - Detailed information for debugging
- `INFO` - General information about program execution
- `WARNING` - Warning messages (default)
- `ERROR` - Error messages
- `CRITICAL` - Critical error messages

### What Gets Logged

- Command execution start and end
- Configuration file discovery and loading
- Command parameters and options
- Success and error states
- Detailed error information with stack traces
- User interactions (confirmations, cancellations)

### Log Format

```
2025-09-09 22:32:58 - INFO - log_command_start:85 - Starting create command
2025-09-09 22:32:58 - INFO - load_config:58 - Loading configuration from: examples/config.toml
2025-09-09 22:32:58 - INFO - log_command_end:106 - create command completed successfully
```

### Viewing Logs

```bash
# View recent logs
tail -f logs/deployment_builder.log

# View all logs
cat logs/deployment_builder.log

# Search for errors
grep ERROR logs/deployment_builder.log
```

## Error Handling

The tool provides clear error messages for common issues:

- **File not found**: When the specified config file doesn't exist
- **Invalid format**: When the config file format is not supported
- **Missing config**: When no config file is found in the current directory

## Development

### Project Structure

```
deployment-builder/
├── src/
│   └── deployment_builder/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py                     # CLI interface with plan command
│       ├── config.py                  # Configuration management
│       ├── kind_integration.py        # Kind cluster integration
│       ├── logging_config.py          # Logging configuration
│       ├── queue.py                   # Service queue system
│       ├── load_balancer.py           # Load balancing strategies
│       ├── execution_planner.py       # Execution planning
│       ├── monitor.py                 # Progress monitoring
│       ├── optimization.py            # Performance optimization
│       ├── error_handler.py           # Error handling and recovery
│       └── benchmark.py               # Performance benchmarking
├── tests/
│   ├── conftest.py                    # Shared pytest fixtures
│   ├── test_config.py                 # Unit tests for configuration management
│   ├── test_cli_integration.py        # Integration tests for CLI commands
│   ├── test_kind_config_integration.py # Integration tests for kind cluster management
│   ├── test_kubeconfig_integration.py # Integration tests for kubeconfig management
│   ├── test_queue.py                  # Unit tests for queue system
│   ├── test_load_balancer.py          # Unit tests for load balancing
│   ├── test_execution_planner.py      # Unit tests for execution planning
│   ├── test_monitor.py                # Unit tests for monitoring
│   ├── test_optimization.py           # Unit tests for optimization
│   ├── test_error_handler.py          # Unit tests for error handling
│   └── test_benchmark.py              # Unit tests for benchmarking
├── examples/
│   ├── config.toml
│   ├── deployment.toml
│   ├── config.json
│   ├── deployment.yaml
│   ├── simple.toml
│   ├── dynamic-clusters.toml
│   ├── microservices.toml
│   ├── edge-computing.toml
│   ├── development.toml
│   └── high-availability.toml
├── docs/
│   ├── BEST_PRACTICES.md              # Best practices for dynamic cluster types
│   ├── PYTEST_BEST_PRACTICES.md       # Testing best practices
│   └── VALIDATION_RULES.md            # Configuration validation rules
├── Plans/
│   ├── PLAN_SERVICE_QUEUE_SYSTEM.md   # Service queue system implementation plan
│   ├── PLAN_DYNAMIC_CLUSTER_TYPES.md  # Dynamic cluster types plan
│   └── PLAN_GAPS_ANALYSIS.md          # Gaps analysis plan
├── hack/
│   └── test_examples.fish
├── pyproject.toml
└── README.md
```

### Dependencies

**Production Dependencies:**
- `click>=8.0.0` - Command-line interface framework
- `pyyaml>=6.0` - YAML configuration file support
- `tomli>=2.0.0` - TOML configuration file support

**Development Dependencies:**
- `black>=23.0.0` - Code formatting
- `pytest>=7.0.0` - Testing framework

### Code Formatting

This project uses Black for code formatting:

```bash
# Format all Python files
poetry run black src/ tests/

# Check formatting without making changes
poetry run black --check src/ tests/
```

### Running Tests

The test suite has been refactored to follow pytest best practices with fixtures, parametrization, and proper test organization.

#### Test Structure

The tests are organized into the following categories:

- **Unit Tests** (`@pytest.mark.unit`): Test individual components and functions
- **Integration Tests** (`@pytest.mark.integration`): Test CLI commands and component interactions
- **CLI Tests** (`@pytest.mark.cli`): Test command-line interface functionality
- **Config Tests** (`@pytest.mark.config`): Test configuration management
- **Kind Tests** (`@pytest.mark.kind`): Test kind cluster integration
- **Kubeconfig Tests** (`@pytest.mark.kubeconfig`): Test kubeconfig management

#### Running All Tests

```bash
# Run all tests
poetry run pytest tests/ -v

# Run tests with coverage
poetry run pytest tests/ --cov=src/deployment_builder
```

#### Running Tests by Category

```bash
# Run only unit tests (configuration tests)
poetry run pytest tests/ -m "unit" -v

# Run only integration tests (CLI, kind, kubeconfig)
poetry run pytest tests/ -m "integration" -v

# Run only CLI tests
poetry run pytest tests/ -m "cli" -v

# Run only configuration tests
poetry run pytest tests/ -m "config" -v

# Run only kind integration tests
poetry run pytest tests/ -m "kind" -v

# Run only kubeconfig tests
poetry run pytest tests/ -m "kubeconfig" -v
```

#### Running Specific Test Files

```bash
# Run configuration tests
poetry run pytest tests/test_config.py -v

# Run CLI integration tests
poetry run pytest tests/test_cli_integration.py -v

# Run kind integration tests
poetry run pytest tests/test_kind_config_integration.py -v

# Run kubeconfig integration tests
poetry run pytest tests/test_kubeconfig_integration.py -v
```

#### Test Features

The refactored test suite includes:

- **91 total tests** (increased from 76 due to parametrization)
- **36 unit tests** for configuration management
- **55 integration tests** for CLI commands and component interactions
- **Parametrized tests** using `@pytest.mark.parametrize` for testing multiple scenarios
- **Shared fixtures** in `conftest.py` for common test setup
- **Test markers** for easy categorization and selective running
- **Enhanced assertions** with descriptive error messages
- **Temporary file handling** using pytest's `tmp_path` fixture

#### Test Fixtures

The test suite includes several shared fixtures in `conftest.py`:

- `examples_dir`: Path to the examples directory containing test configuration files
- `example_files`: List of example configuration files for testing
- `cli_runner`: Fixture for running CLI commands with proper error handling
- `sample_config_data`: Sample configuration data for testing

#### Example Test Usage

```python
# Using fixtures in tests
def test_create_command_dry_run(example_file, examples_dir, cli_runner):
    """Test create command with --dry-run for all example files."""
    file_path = examples_dir / example_file
    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])
    assert "DRY RUN:" in result.stdout

# Using parametrization
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
def test_services_configuration_parsing(example_file, examples_dir, cli_runner):
    """Test that services configuration is parsed correctly."""
    file_path = examples_dir / example_file
    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])
    assert "services" in result.stdout
```

### Manual Testing

For manual testing with real cluster creation, use the hack script:

```bash
./hack/test_examples.fish
```

**Note**: The integration tests (`test_cli_integration.py`) provide comprehensive automated testing of CLI commands with all example configuration files using dry-run mode, which is much faster and safer than manual testing.

### Test Coverage

The project includes comprehensive test coverage with 334 total tests:

- **Configuration Tests** (`test_config.py`): 67 unit tests covering configuration object behavior, file loading, and edge cases
- **CLI Integration Tests** (`test_cli_integration.py`): 88 integration tests covering CLI commands with all example configuration files
- **Kind Integration Tests** (`test_kind_config_integration.py`): 12 integration tests for kind cluster creation and configuration
- **Kubeconfig Integration Tests** (`test_kubeconfig_integration.py`): 8 integration tests for kubeconfig file management
- **Service Queue Tests** (`test_queue.py`): 12 unit tests for queue system functionality
- **Load Balancer Tests** (`test_load_balancer.py`): 12 unit tests for load balancing strategies
- **Execution Planner Tests** (`test_execution_planner.py`): 15 unit tests for execution planning
- **Monitor Tests** (`test_monitor.py`): 6 unit tests for progress monitoring
- **Optimization Tests** (`test_optimization.py`): 25 unit tests for performance optimization
- **Error Handler Tests** (`test_error_handler.py`): 31 unit tests for error handling and recovery
- **Benchmark Tests** (`test_benchmark.py`): 36 unit tests for performance benchmarking

#### Test Organization

- **Unit Tests**: 208 tests focused on individual component testing
- **Integration Tests**: 126 tests covering end-to-end functionality and component interactions
- **Parametrized Tests**: Multiple test scenarios using `@pytest.mark.parametrize`
- **Fixture-Based**: Shared test setup using pytest fixtures in `conftest.py`
- **Marker-Based**: Tests categorized with markers for selective running

All tests use real objects without mocks, ensuring robust testing of the actual functionality. The test suite follows pytest best practices with proper fixture usage, parametrization, and descriptive assertions.

### Configuration Architecture

The tool uses a structured configuration object system:

- **`DeploymentConfig`**: Main configuration object containing all settings
- **`GeneralConfig`**: General deployment settings (name, version, environment, etc.)
- **`ClusterConfig`**: Individual cluster configuration (enable, count)
- **Configuration Loading**: Supports both new structured format and legacy format
- **Default Values**: Centralized default configuration with easy override
- **Type Safety**: Uses Python dataclasses for type-safe configuration

This architecture provides:
- **Centralized Defaults**: All default values in one place
- **Type Safety**: Compile-time type checking
- **Easy Override**: Simple configuration file override
- **Backward Compatibility**: Legacy format still supported
- **Validation**: Built-in validation and error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Author

Jim Fitzpatrick - jimfity@gmail.com
