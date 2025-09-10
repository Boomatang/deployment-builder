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

The tool supports creating multiple clusters based on configuration:

#### Cluster Types

1. **Metrics Cluster** (`metrics: true/false`)
   - Single centralized metrics cluster
   - Name: `{prefix}-metrics`

2. **Primary Clusters** (`primary: <number>`)
   - Main application clusters
   - Names: `{prefix}-primary-1`, `{prefix}-primary-2`, etc.

3. **Secondary Clusters** (`secondary: <number>`)
   - Backup or secondary clusters
   - Names: `{prefix}-secondary-1`, `{prefix}-secondary-2`, etc.

4. **Standalone Clusters** (`standalone: <number>`)
   - General purpose clusters
   - Names: `{prefix}-standalone-1`, `{prefix}-standalone-2`, etc.

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
[clusters.metrics]
enable = true

[clusters.primary]
count = 2

[clusters.secondary]
count = 1

[clusters.standalone]
count = 3
```

This creates 7 clusters:
- `my-project-metrics`
- `my-project-primary-1`, `my-project-primary-2`
- `my-project-secondary-1`
- `my-project-standalone-1`, `my-project-standalone-2`, `my-project-standalone-3`

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
[clusters.metrics]
enable = true

[clusters.primary]
count = 2

[clusters.secondary]
count = 1

[clusters.standalone]
count = 3
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
- **`[clusters.metrics]`**: Metrics cluster configuration
  - `enable`: Enable metrics cluster (boolean)
  - `count`: Number of metrics clusters (integer, usually 0 or 1)
- **`[clusters.primary]`**: Primary cluster configuration
  - `enable`: Enable primary clusters (boolean)
  - `count`: Number of primary clusters (integer)
- **`[clusters.secondary]`**: Secondary cluster configuration
  - `enable`: Enable secondary clusters (boolean)
  - `count`: Number of secondary clusters (integer)
- **`[clusters.standalone]`**: Standalone cluster configuration
  - `enable`: Enable standalone clusters (boolean)
  - `count`: Number of standalone clusters (integer)

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
    "metrics": {
      "enable": true
    },
    "primary": {
      "count": 2
    },
    "secondary": {
      "count": 1
    },
    "standalone": {
      "count": 3
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
  metrics:
    enable: true
  primary:
    count: 2
  secondary:
    count: 1
  standalone:
    count: 3
```

## Example Configurations

The `examples/` directory contains sample configuration files in all supported formats:

- `examples/config.toml` - Basic TOML configuration (new structured format)
- `examples/deployment.toml` - Advanced TOML configuration (new structured format)
- `examples/config.json` - Basic JSON configuration (new structured format)
- `examples/deployment.yaml` - Advanced YAML configuration (new structured format)

All example files use the new structured configuration format with `[general]` and `[clusters.*]` sections. You can copy any of these files to your project directory and customize them for your needs.

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
clusters.metrics.count = 0
clusters.metrics.enable = False
clusters.primary.count = 0
clusters.primary.enable = False
clusters.secondary.count = 0
clusters.secondary.enable = False
clusters.standalone.count = 0
clusters.standalone.enable = False
general.environment = development
general.kind_config_path = kind-configs
general.kubeconfig_path = kubeconfigs
general.max_workers = 4
general.name = default-deployment
general.prefix = default
general.version = 1.0.0
```

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
│       ├── cli.py
│       ├── config.py
│       ├── kind_integration.py
│       └── logging_config.py
├── tests/
│   ├── test_config.py
│   ├── test_kind_config_integration.py
│   └── test_kubeconfig_integration.py
├── examples/
│   ├── config.toml
│   ├── deployment.toml
│   ├── config.json
│   └── deployment.yaml
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

```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_config.py -v

# Run tests with coverage
poetry run pytest tests/ --cov=src/deployment_builder
```

### Test Coverage

The project includes comprehensive test coverage:

- **Configuration Tests** (`test_config.py`): 29 tests covering configuration object behavior, file loading, and edge cases
- **Kind Integration Tests** (`test_kind_config_integration.py`): Tests for kind cluster creation and configuration
- **Kubeconfig Integration Tests** (`test_kubeconfig_integration.py`): Tests for kubeconfig file management

All tests use real objects without mocks, ensuring robust testing of the actual functionality.

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
