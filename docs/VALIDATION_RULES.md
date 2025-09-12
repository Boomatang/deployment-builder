# Validation Rules and Error Messages

This document describes the validation rules and error messages for the deployment-builder tool's dynamic cluster types feature.

## Table of Contents

- [Cluster Type Validation](#cluster-type-validation)
- [Configuration Validation](#configuration-validation)
- [Service Validation](#service-validation)
- [Error Messages](#error-messages)
- [Troubleshooting](#troubleshooting)

## Cluster Type Validation

### Cluster Type Name Rules

**Valid Characters:**
- Alphanumeric characters (a-z, A-Z, 0-9)
- Hyphens (-)
- Underscores (_)

**Length Requirements:**
- Minimum: 1 character
- Maximum: 50 characters

**Uniqueness:**
- Each cluster type name must be unique within the configuration
- Case-sensitive (e.g., `worker` and `Worker` are different)

**Reserved Words:**
- Cannot use reserved configuration section names
- Cannot start with numbers
- Cannot contain spaces or special characters

### Valid Examples

```toml
[clusters]
[clusters.web-server]        # Valid
[clusters.api-gateway]       # Valid
[clusters.database-primary]  # Valid
[clusters.redis-cache]       # Valid
[clusters.ml-inference]      # Valid
[clusters.edge-processor]    # Valid
[clusters.worker-node]       # Valid
[clusters.monitoring]        # Valid
```

### Invalid Examples

```toml
[clusters]
[clusters.web server]        # Invalid: contains space
[clusters.web@server]        # Invalid: contains special character
[clusters.123worker]         # Invalid: starts with number
[clusters.web.server]        # Invalid: contains dot
[clusters.web/server]        # Invalid: contains slash
[clusters.web+server]        # Invalid: contains plus sign
[clusters.web*server]        # Invalid: contains asterisk
[clusters.web(server)]       # Invalid: contains parentheses
[clusters.web[server]]       # Invalid: contains brackets
[clusters.web{server}]       # Invalid: contains braces
[clusters.web|server]        # Invalid: contains pipe
[clusters.web&server]        # Invalid: contains ampersand
[clusters.web%server]        # Invalid: contains percent
[clusters.web#server]        # Invalid: contains hash
[clusters.web$server]        # Invalid: contains dollar sign
[clusters.web!server]        # Invalid: contains exclamation
[clusters.web?server]        # Invalid: contains question mark
[clusters.web=server]        # Invalid: contains equals
[clusters.web<server]        # Invalid: contains less than
[clusters.web>server]        # Invalid: contains greater than
[clusters.web,server]        # Invalid: contains comma
[clusters.web;server]        # Invalid: contains semicolon
[clusters.web:server]        # Invalid: contains colon
[clusters.web"server]        # Invalid: contains quote
[clusters.web'server]        # Invalid: contains apostrophe
[clusters.web`server]        # Invalid: contains backtick
[clusters.web~server]        # Invalid: contains tilde
[clusters.web^server]        # Invalid: contains caret
[clusters.web\server]        # Invalid: contains backslash
[clusters.web/server]        # Invalid: contains forward slash
```

## Configuration Validation

### Cluster Configuration Rules

**Required Fields:**
- Each cluster type must have either `enable` or `count` property
- Cannot have both `enable` and `count` properties

**Enable Property:**
- Must be boolean (true/false)
- Used for single cluster instances
- When `enable: true`, creates one cluster with name `{prefix}-{cluster_type}`
- When `enable: false`, no cluster is created

**Count Property:**
- Must be non-negative integer (0 or positive)
- Used for multiple cluster instances
- When `count > 0`, creates `count` clusters with names `{prefix}-{cluster_type}-1`, `{prefix}-{cluster_type}-2`, etc.
- When `count = 0`, no clusters are created

**Cluster Creation Rules:**
- Clusters are only created when both `enable: true` AND `count > 0` (for single clusters)
- Clusters are only created when `count > 0` (for multiple clusters)
- Clusters with `enable: false` are never created
- Clusters with `count: 0` are never created

### Valid Configuration Examples

```toml
[clusters]
# Single cluster (enable: true)
[clusters.gateway]
enable = true

# Single cluster (enable: false)
[clusters.monitoring]
enable = false

# Multiple clusters (count > 0)
[clusters.worker]
count = 3

# Multiple clusters (count = 0)
[clusters.database]
count = 0

# Mixed configuration
[clusters.api-gateway]
enable = true

[clusters.web-server]
count = 2

[clusters.database-primary]
enable = true

[clusters.database-replica]
count = 2
```

### Invalid Configuration Examples

```toml
[clusters]
# Invalid: both enable and count
[clusters.worker]
enable = true
count = 3

# Invalid: neither enable nor count
[clusters.worker]

# Invalid: enable is not boolean
[clusters.worker]
enable = "true"

# Invalid: count is not integer
[clusters.worker]
count = "3"

# Invalid: count is negative
[clusters.worker]
count = -1

# Invalid: count is float
[clusters.worker]
count = 3.5
```

## Service Validation

### Service Configuration Rules

**Required Fields:**
- `cmd`: Command to execute (string)
- `kubeconfig.flag`: Kubeconfig flag (string, default: "--kubeconfig")

**Optional Fields:**
- None

**Service Types:**
- **Global Services**: Defined in `[services]` section, run on all clusters
- **Cluster-Specific Services**: Defined in `[clusters.{cluster_type}.services]` section, run only on specific cluster types

### Valid Service Examples

```toml
# Global services
[services]
health-check = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get nodes" }
security-scan = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pods -n security" }

# Cluster-specific services
[clusters.web-server.services]
nginx-reload = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl rollout restart deployment/nginx" }

[clusters.database-primary.services]
backup-schedule = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get cronjobs -n backup" }
```

### Invalid Service Examples

```toml
# Invalid: missing cmd
[services]
health-check = { "kubeconfig.flag" = "--kubeconfig" }

# Invalid: missing kubeconfig.flag
[services]
health-check = { cmd = "kubectl get nodes" }

# Invalid: cmd is not string
[services]
health-check = { "kubeconfig.flag" = "--kubeconfig", cmd = 123 }

# Invalid: kubeconfig.flag is not string
[services]
health-check = { "kubeconfig.flag" = 123, cmd = "kubectl get nodes" }
```

## Error Messages

### Cluster Type Validation Errors

**Invalid cluster type name:**
```
ValueError: Invalid cluster type name 'web server': must contain only alphanumeric characters, hyphens, and underscores
```

**Cluster type name too long:**
```
ValueError: Cluster type name 'very-long-cluster-type-name-that-exceeds-fifty-characters' is too long: maximum 50 characters allowed
```

**Cluster type name too short:**
```
ValueError: Cluster type name '' is too short: minimum 1 character required
```

**Duplicate cluster type:**
```
ValueError: Duplicate cluster type 'worker' found in configuration
```

**Cluster type starts with number:**
```
ValueError: Invalid cluster type name '123worker': cannot start with a number
```

### Configuration Validation Errors

**Missing enable or count:**
```
ValueError: Cluster type 'worker' must have either 'enable' or 'count' property
```

**Both enable and count specified:**
```
ValueError: Cluster type 'worker' cannot have both 'enable' and 'count' properties
```

**Invalid enable value:**
```
ValueError: Invalid enable value for cluster type 'worker': must be boolean (true/false)
```

**Invalid count value:**
```
ValueError: Invalid count value for cluster type 'worker': must be non-negative integer
```

**Negative count value:**
```
ValueError: Invalid count value for cluster type 'worker': must be non-negative integer
```

**Float count value:**
```
ValueError: Invalid count value for cluster type 'worker': must be non-negative integer
```

### Service Validation Errors

**Missing cmd field:**
```
ValueError: Service 'health-check' is missing required field 'cmd'
```

**Missing kubeconfig.flag field:**
```
ValueError: Service 'health-check' is missing required field 'kubeconfig.flag'
```

**Invalid cmd type:**
```
ValueError: Service 'health-check' field 'cmd' must be string
```

**Invalid kubeconfig.flag type:**
```
ValueError: Service 'health-check' field 'kubeconfig.flag' must be string
```

### Configuration File Errors

**Invalid file format:**
```
ValueError: Unsupported configuration file format: .txt
```

**File not found:**
```
FileNotFoundError: Configuration file not found: /path/to/config.toml
```

**Invalid TOML syntax:**
```
tomli.TOMLDecodeError: Invalid TOML syntax at line 5, column 10
```

**Invalid JSON syntax:**
```
json.JSONDecodeError: Expecting ',' delimiter: line 5 column 10 (char 45)
```

**Invalid YAML syntax:**
```
yaml.YAMLError: while parsing a block mapping
  in "config.yaml", line 5, column 10
```

### General Configuration Errors

**Clusters configuration must be dictionary:**
```
ValueError: Clusters configuration must be a dictionary
```

**General configuration must be dictionary:**
```
ValueError: General configuration must be a dictionary
```

**Services configuration must be dictionary:**
```
ValueError: Services configuration must be a dictionary
```

## Troubleshooting

### Common Issues and Solutions

**Issue: Cluster type name validation fails**
- **Cause**: Cluster type name contains invalid characters
- **Solution**: Use only alphanumeric characters, hyphens, and underscores
- **Example**: Change `web server` to `web-server`

**Issue: Configuration validation fails**
- **Cause**: Missing required fields or invalid field types
- **Solution**: Ensure each cluster type has either `enable` or `count` property with correct types
- **Example**: Add `enable = true` or `count = 3` to cluster configuration

**Issue: Service validation fails**
- **Cause**: Missing required service fields
- **Solution**: Ensure each service has both `cmd` and `kubeconfig.flag` fields
- **Example**: Add `cmd = "kubectl get nodes"` to service configuration

**Issue: File format not supported**
- **Cause**: Using unsupported file format
- **Solution**: Use TOML, JSON, or YAML format
- **Example**: Rename `config.txt` to `config.toml`

**Issue: Configuration file not found**
- **Cause**: File path is incorrect or file doesn't exist
- **Solution**: Check file path and ensure file exists
- **Example**: Use absolute path or check current directory

### Debugging Tips

1. **Use dry-run mode**: Preview changes before applying
   ```bash
   deploy create --dry-run
   ```

2. **Check configuration syntax**: Validate file format
   ```bash
   # For TOML
   python -c "import tomli; tomli.load(open('config.toml'))"
   
   # For JSON
   python -c "import json; json.load(open('config.json'))"
   
   # For YAML
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

3. **Use debug logging**: Get detailed error information
   ```bash
   deploy --log-level=debug create --dry-run
   ```

4. **Check default values**: See current configuration
   ```bash
   deploy defaults
   ```

5. **Validate cluster names**: Check generated cluster names
   ```bash
   deploy create --dry-run | grep "Clusters to create"
   ```

### Getting Help

If you encounter validation errors:

1. **Check the error message** for specific details about what's wrong
2. **Review the validation rules** in this document
3. **Use dry-run mode** to test your configuration
4. **Check the examples** in the `examples/` directory
5. **Refer to the best practices** in `docs/BEST_PRACTICES.md`

### Reporting Issues

When reporting validation issues:

1. **Include the full error message**
2. **Provide your configuration file** (remove sensitive information)
3. **Specify the command** that caused the error
4. **Include the tool version** (`deploy --version`)
5. **Describe what you were trying to achieve**

This will help us provide better assistance and improve the tool's error messages.
