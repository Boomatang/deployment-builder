# Deployment Builder

A command-line tool for managing kind Kubernetes clusters using configuration files. Built with Python and Click.

## Features

- **Create multiple kind clusters** from configuration files
- **Remove multiple kind clusters** based on configuration
- **Multiple config formats** - TOML (default), JSON and YAML support
- **Dry run mode** - Preview changes before execution
- **Flexible config discovery** - Automatic config file detection
- **Environment variable support** - Set config file via `DEPLOYMENT_CONFIG` envvar
- **Comprehensive logging** - Detailed logs written to `logs/deployment_builder.log`
- **Error handling** - Comprehensive error messages and validation

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

4. **Standard Clusters** (`standard: <number>`)
   - General purpose clusters
   - Names: `{prefix}-standard-1`, `{prefix}-standard-2`, etc.

#### Configuration Structure

```toml
prefix = "my-project"

[clusters]
metrics = true
primary = 2
secondary = 1
standard = 3
```

This creates 7 clusters:
- `my-project-metrics`
- `my-project-primary-1`, `my-project-primary-2`
- `my-project-secondary-1`
- `my-project-standard-1`, `my-project-standard-2`, `my-project-standard-3`

The prefix is automatically sanitized to be valid for kind (lowercase, alphanumeric, hyphens only).

## Usage

### Basic Commands

#### Using Poetry (Recommended)

```bash
# Show help
poetry run deploy --help

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

## Configuration Files

The tool supports TOML (default), JSON, and YAML configuration files with multi-cluster support. Configuration files are automatically discovered in the current directory, or you can specify a custom path using the `--config` flag or the `DEPLOYMENT_CONFIG` environment variable.

### Multi-Cluster Configuration Structure

```toml
# Basic project information
name = "my-deployment"
version = "1.0.0"
environment = "production"
prefix = "my-project"

# Multi-cluster configuration
[clusters]
metrics = true      # Create metrics cluster
primary = 2         # Create 2 primary clusters
secondary = 1       # Create 1 secondary cluster
standard = 3        # Create 3 standard clusters

# Resource configuration
[resources]
cpu = "2"
memory = "4Gi"
replicas = 3

# Service definitions
[[services]]
name = "web"
port = 8080
image = "nginx:latest"

[[services]]
name = "api"
port = 3000
image = "node:18-alpine"
```

This configuration creates 7 clusters:
- `my-project-metrics`
- `my-project-primary-1`, `my-project-primary-2`
- `my-project-secondary-1`
- `my-project-standard-1`, `my-project-standard-2`, `my-project-standard-3`

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

#### TOML Example (`config.toml`) - Default Format

```toml
# Basic deployment configuration
name = "my-deployment"
version = "1.0.0"
environment = "production"

[resources]
cpu = "2"
memory = "4Gi"
replicas = 3

[[services]]
name = "web"
port = 8080
image = "nginx:latest"

[[services]]
name = "api"
port = 3000
image = "node:18-alpine"
```

#### JSON Example (`config.json`)

```json
{
  "name": "my-deployment",
  "version": "1.0.0",
  "environment": "production",
  "resources": {
    "cpu": "2",
    "memory": "4Gi",
    "replicas": 3
  },
  "services": [
    {
      "name": "web",
      "port": 8080,
      "image": "nginx:latest"
    },
    {
      "name": "api",
      "port": 3000,
      "image": "node:18-alpine"
    }
  ]
}
```

#### YAML Example (`deployment.yaml`)

```yaml
name: my-deployment
version: 1.0.0
environment: production
resources:
  cpu: "2"
  memory: "4Gi"
  replicas: 3
services:
  - name: web
    port: 8080
    image: nginx:latest
  - name: api
    port: 3000
    image: node:18-alpine
```

## Example Configurations

The `examples/` directory contains sample configuration files in all supported formats:

- `examples/config.toml` - Basic TOML configuration
- `examples/deployment.toml` - Advanced TOML configuration with multiple services
- `examples/config.json` - Basic JSON configuration
- `examples/deployment.yaml` - Advanced YAML configuration

You can copy any of these files to your project directory and customize them for your needs.

## Examples

### Using Default Configuration

```bash
# Create a deployment using the default config file
poetry run deploy create

# Remove the deployment
poetry run deploy remove
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
│       └── cli.py
├── tests/
├── pyproject.toml
└── README.md
```

### Dependencies

- `click>=8.0.0` - Command-line interface framework
- `pyyaml>=6.0` - YAML configuration file support
- `tomli>=2.0.0` - TOML configuration file support

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
# Run tests (when implemented)
poetry run pytest
```

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
