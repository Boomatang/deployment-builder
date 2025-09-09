# Deployment Builder

A command-line tool for managing deployments using configuration files. Built with Python and Click.

## Features

- **Create deployments** from configuration files
- **Remove deployments** based on configuration
- **Multiple config formats** - JSON and YAML support
- **Dry run mode** - Preview changes before execution
- **Flexible config discovery** - Automatic config file detection
- **Error handling** - Comprehensive error messages and validation

## Installation

### Prerequisites

- Python 3.13+
- Poetry (for development)

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

## Usage

### Basic Commands

#### Using Poetry (Recommended)

```bash
# Show help
poetry run deploy --help

# Create deployment
poetry run deploy create

# Remove deployment
poetry run deploy remove
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

#### Create Command

```bash
python -m deployment_builder create [OPTIONS]

Options:
  -c, --config PATH  Path to configuration file. If not provided, looks for
                     config files in current directory.
  -n, --dry-run      Show what would be created without actually creating it.
  --help             Show this message and exit.
```

#### Remove Command

```bash
python -m deployment_builder remove [OPTIONS]

Options:
  -c, --config PATH  Path to configuration file. If not provided, looks for
                     config files in current directory.
  -n, --dry-run      Show what would be removed without actually removing it.
  -f, --force        Force removal without confirmation.
  --help             Show this message and exit.
```

## Configuration Files

The tool supports both JSON and YAML configuration files. Configuration files are automatically discovered in the current directory, or you can specify a custom path using the `--config` flag.

### Supported File Names

The tool looks for these files in order:
- `config.json`
- `config.yaml`
- `config.yml`
- `deployment.json`
- `deployment.yaml`
- `deployment.yml`

### Configuration Format

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
