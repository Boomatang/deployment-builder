# Best Practices for Dynamic Cluster Types

This document provides best practices and guidelines for using dynamic cluster types in the deployment-builder tool.

## Table of Contents

- [Cluster Type Naming](#cluster-type-naming)
- [Configuration Organization](#configuration-organization)
- [Single vs Multiple Cluster Types](#single-vs-multiple-cluster-types)
- [Service Configuration](#service-configuration)
- [Performance Considerations](#performance-considerations)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Observability](#monitoring-and-observability)
- [Common Patterns](#common-patterns)

## Cluster Type Naming

### Naming Conventions

**Good Examples:**
```toml
[clusters.api-gateway]
[clusters.web-frontend]
[clusters.database-primary]
[clusters.redis-cache]
[clusters.ml-inference]
[clusters.edge-processor]
```

**Bad Examples:**
```toml
[clusters.API]           # Uppercase not recommended
[clusters.web frontend]  # Spaces not allowed
[clusters.web-frontend-1] # Don't include numbers in type names
[clusters.123]           # Don't start with numbers
```

### Naming Guidelines

1. **Use descriptive names** that reflect the cluster's purpose
2. **Use kebab-case** (lowercase with hyphens) for consistency
3. **Avoid numbers** in cluster type names (use `count` for multiple instances)
4. **Use consistent prefixes** for related cluster types (e.g., `database-primary`, `database-replica`)
5. **Keep names concise** but meaningful (1-3 words typically)

## Configuration Organization

### File Structure

Organize your configuration files logically:

```toml
[general]
name = "my-application"
version = "1.0.0"
environment = "production"
prefix = "my-app"

[clusters]
# Core application clusters
[clusters.api-gateway]
enable = true

[clusters.web-frontend]
count = 2

[clusters.api-backend]
count = 3

# Data layer clusters
[clusters.database-primary]
enable = true

[clusters.database-replica]
count = 2

[clusters.redis-cache]
count = 3

# Infrastructure clusters
[clusters.load-balancer]
count = 2

[clusters.monitoring]
enable = true

[clusters.logging]
enable = true
```

### Configuration Comments

Use comments to organize and document your configuration:

```toml
[clusters]
# === Core Application ===
[clusters.api-gateway]
enable = true

[clusters.web-frontend]
count = 2

# === Data Layer ===
[clusters.database-primary]
enable = true

[clusters.redis-cache]
count = 3

# === Infrastructure ===
[clusters.monitoring]
enable = true
```

## Single vs Multiple Cluster Types

### When to Use Single Clusters (`enable: true`)

Use single clusters for:
- **Unique services** that only need one instance
- **Centralized components** like monitoring, logging, or API gateways
- **Stateful services** that don't scale horizontally
- **Management services** like CI/CD or configuration management

**Examples:**
```toml
[clusters.api-gateway]
enable = true

[clusters.prometheus]
enable = true

[clusters.jenkins]
enable = true
```

### When to Use Multiple Clusters (`count: N`)

Use multiple clusters for:
- **Stateless services** that can scale horizontally
- **Load balancing** across multiple instances
- **High availability** requirements
- **Geographic distribution** (different regions)
- **Environment separation** (dev, staging, prod)

**Examples:**
```toml
[clusters.web-server]
count = 5

[clusters.api-server]
count = 3

[clusters.worker-node]
count = 10
```

### Mixed Configuration

You can mix single and multiple cluster types in the same configuration:

```toml
[clusters]
# Single instances
[clusters.api-gateway]
enable = true

[clusters.database-primary]
enable = true

# Multiple instances
[clusters.web-server]
count = 3

[clusters.api-server]
count = 2

[clusters.worker-node]
count = 5
```

## Service Configuration

### Global Services

Global services run on all clusters. Use them for:
- Health checks
- Security scanning
- Common monitoring
- Network connectivity tests

```toml
[services]
health-check = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get nodes" }
security-scan = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pods -n security" }
```

### Cluster-Specific Services

Cluster-specific services run only on specific cluster types. Use them for:
- Service-specific deployments
- Type-specific monitoring
- Custom configurations

```toml
[clusters.web-server.services]
nginx-reload = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl rollout restart deployment/nginx" }

[clusters.database-primary.services]
backup-schedule = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get cronjobs -n backup" }
```

### Service Organization

Organize services by cluster type and purpose:

```toml
# Global services
[services]
health-check = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get nodes" }
network-test = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get networkpolicies" }

# Web tier services
[clusters.web-server.services]
app-deploy = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get deployments -n web" }
nginx-config = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get configmaps -n nginx" }

# API tier services
[clusters.api-server.services]
api-deploy = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get deployments -n api" }
api-logs = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl logs -n api --tail=100" }

# Data tier services
[clusters.database-primary.services]
db-backup = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pv" }
db-metrics = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pods -n database" }
```

## Performance Considerations

### Cluster Count Limits

- **Small deployments** (1-5 clusters): Use sequential execution
- **Medium deployments** (6-20 clusters): Use parallel execution with 4-8 workers
- **Large deployments** (20+ clusters): Use parallel execution with 8+ workers

### Memory Usage

- Each cluster consumes memory for kind and Kubernetes components
- Monitor system resources when creating many clusters
- Consider using `--dry-run` to preview large deployments

### Parallel Execution

Configure `max_workers` based on your system:

```toml
[general]
max_workers = 4  # Adjust based on CPU cores and memory
```

**Guidelines:**
- **CPU-bound**: Set to number of CPU cores
- **Memory-bound**: Set to 2-4 workers
- **I/O-bound**: Set to 8-16 workers

## Security Best Practices

### Cluster Isolation

- Use different cluster types for different security zones
- Separate public-facing clusters from internal clusters
- Use network policies to control traffic between clusters

```toml
[clusters]
# Public-facing clusters
[clusters.load-balancer]
count = 2

[clusters.web-server]
count = 3

# Internal clusters
[clusters.api-server]
count = 2

[clusters.database-primary]
enable = true
```

### Service Security

- Use least-privilege principles for service commands
- Avoid running privileged operations in services
- Use specific namespaces for service operations

```toml
[clusters.database-primary.services]
# Good: Specific namespace and resource
db-backup = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pv -n database" }

# Bad: Too broad access
db-backup = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get all --all-namespaces" }
```

## Monitoring and Observability

### Cluster Monitoring

Create dedicated monitoring clusters:

```toml
[clusters]
[clusters.prometheus]
enable = true

[clusters.grafana]
enable = true

[clusters.alertmanager]
enable = true
```

### Service Monitoring

Use services to monitor cluster health:

```toml
[services]
# Global health monitoring
health-check = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get nodes" }
pod-status = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pods --all-namespaces" }

# Cluster-specific monitoring
[clusters.web-server.services]
nginx-status = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pods -n nginx" }

[clusters.database-primary.services]
db-status = { "kubeconfig.flag" = "--kubeconfig", cmd = "kubectl get pods -n database" }
```

## Common Patterns

### Microservices Architecture

```toml
[clusters]
# API Gateway
[clusters.api-gateway]
enable = true

# Frontend services
[clusters.web-frontend]
count = 2

# Backend services
[clusters.user-service]
count = 2

[clusters.order-service]
count = 2

[clusters.payment-service]
count = 2

# Data services
[clusters.database-primary]
enable = true

[clusters.database-replica]
count = 2

[clusters.redis-cache]
count = 3

# Infrastructure
[clusters.monitoring]
enable = true

[clusters.logging]
enable = true
```

### High Availability Setup

```toml
[clusters]
# Load balancers
[clusters.load-balancer]
count = 3

# Application servers
[clusters.app-server]
count = 5

# Database cluster
[clusters.database-primary]
enable = true

[clusters.database-replica]
count = 3

# Cache cluster
[clusters.redis-cluster]
count = 4

# Monitoring
[clusters.prometheus-cluster]
count = 2

[clusters.grafana-cluster]
count = 2
```

### Development Environment

```toml
[clusters]
# Development services
[clusters.web-app]
enable = true

[clusters.api-server]
enable = true

[clusters.database]
enable = true

# Testing clusters
[clusters.test-runner]
count = 3

# Development tools
[clusters.jenkins]
enable = true

[clusters.sonarqube]
enable = true
```

### Edge Computing

```toml
[clusters]
# Central control
[clusters.control-plane]
enable = true

# Edge locations
[clusters.edge-site-1]
enable = true

[clusters.edge-site-2]
enable = true

[clusters.edge-site-3]
enable = true

# Regional data centers
[clusters.region-us-east]
count = 2

[clusters.region-eu-central]
count = 2

# IoT processing
[clusters.iot-processor]
count = 4
```

## Troubleshooting

### Common Issues

1. **Cluster name conflicts**: Ensure cluster type names are unique
2. **Resource limits**: Monitor system resources for large deployments
3. **Service failures**: Check service commands and kubeconfig paths
4. **Configuration errors**: Validate configuration syntax and structure

### Debugging Tips

1. **Use dry-run mode**: Preview changes before applying
2. **Check logs**: Review deployment logs for errors
3. **Validate configuration**: Use `deploy defaults` to see current values
4. **Test incrementally**: Start with small configurations and scale up

### Performance Optimization

1. **Adjust max_workers**: Based on system resources
2. **Use appropriate cluster counts**: Don't over-provision
3. **Monitor resource usage**: Watch CPU and memory consumption
4. **Optimize service commands**: Use efficient kubectl commands

## Conclusion

Following these best practices will help you create maintainable, scalable, and efficient cluster configurations. Start with simple configurations and gradually add complexity as needed. Always test your configurations with `--dry-run` before applying them to production environments.
