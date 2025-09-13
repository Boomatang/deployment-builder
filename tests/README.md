# Test Suite Documentation

This directory contains the comprehensive test suite for the deployment-builder project, organized following pytest best practices.

## Overview

The test suite has been refactored to follow modern pytest patterns with:
- **Function-based tests** (preferred over class-based)
- **Comprehensive fixture system** with proper scoping
- **Parallel execution support** for improved performance
- **Well-organized structure** with unit and integration test separation
- **Performance monitoring** and optimization features

## Directory Structure

```
tests/
├── README.md                           # This file
├── conftest.py                         # Shared fixtures and configuration
├── pytest.ini                         # Pytest configuration
├── run_tests.py                        # Performance test runner
├── unit/                               # Unit tests
│   ├── __init__.py
│   ├── test_config.py                  # Configuration management tests
│   ├── test_queue.py                   # Service queue system tests
│   ├── test_optimization.py            # Performance optimization tests
│   ├── test_execution_planner.py       # Execution planning tests
│   ├── test_load_balancer.py           # Load balancing tests
│   ├── test_monitor.py                 # Progress monitoring tests
│   ├── test_error_handler.py           # Error handling tests
│   └── test_benchmark.py               # Performance benchmark tests
└── integration/                        # Integration tests
    ├── __init__.py
    ├── test_cli_integration.py         # CLI command integration tests
    ├── test_kind_config_integration.py # Kind configuration tests
    └── test_kubeconfig_integration.py  # Kubeconfig management tests
```

## Running Tests

### Basic Commands

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/unit/test_config.py

# Run specific test function
poetry run pytest tests/unit/test_config.py::test_validate_cluster_name
```

### Parallel Execution

```bash
# Run all tests in parallel (auto-detect CPU cores)
poetry run pytest -n auto

# Run with specific number of workers
poetry run pytest -n 4

# Run unit tests in parallel
poetry run pytest -m unit -n auto

# Run integration tests in parallel
poetry run pytest -m integration -n auto
```

### Test Categories

```bash
# Run only unit tests
poetry run pytest -m unit

# Run only integration tests
poetry run pytest -m integration

# Run only fast tests
poetry run pytest -m fast

# Run only slow tests
poetry run pytest -m slow

# Run CLI tests
poetry run pytest -m cli

# Run configuration tests
poetry run pytest -m config
```

### Performance Testing

```bash
# Run performance comparison
poetry run python run_tests.py

# Run with performance metrics
poetry run pytest --durations=10

# Run with profiling
poetry run pytest --profile
```

### Using Makefile

```bash
# All tests (sequential)
make test

# Unit tests (parallel)
make test-unit

# Integration tests (parallel)
make test-integration

# Fast tests (parallel)
make test-fast

# Slow tests (sequential)
make test-slow

# Performance comparison
make test-performance

# Coverage with performance
make test-coverage

# Clean up test artifacts
make clean
```

## Test Markers

The test suite uses comprehensive pytest markers for categorization:

| Marker | Description | Usage |
|--------|-------------|-------|
| `@pytest.mark.unit` | Unit tests | Individual function/method tests |
| `@pytest.mark.integration` | Integration tests | Component interaction tests |
| `@pytest.mark.cli` | CLI command tests | Command-line interface tests |
| `@pytest.mark.config` | Configuration tests | Configuration management tests |
| `@pytest.mark.kind` | Kind integration tests | Kind cluster management tests |
| `@pytest.mark.kubeconfig` | Kubeconfig tests | Kubeconfig management tests |
| `@pytest.mark.slow` | Slow-running tests | Performance and complex tests |
| `@pytest.mark.fast` | Fast-running tests | Quick unit tests |

## Fixtures

The test suite includes a comprehensive fixture system in `conftest.py`:

### Session-Scoped Fixtures
- `shared_config`: Shared configuration for all tests
- `shared_temp_dir`: Shared temporary directory
- `performance_metrics`: Performance metrics collection

### Function-Scoped Fixtures
- `fresh_queue`: Fresh service queue instance
- `mock_workers`: Mock worker instances
- `error_handler`: Error handler instance
- `recovery_manager`: Recovery manager instance
- `performance_benchmark`: Performance benchmark instance
- `temp_benchmark_dir`: Temporary directory for benchmarks

### Utility Fixtures
- `examples_dir`: Path to example configuration files
- `example_files`: List of example configuration files
- `cli_runner`: CLI command runner with error handling
- `lazy_expensive_resource`: Lazy-loaded expensive resources

## Performance Features

### Parallel Execution
- **pytest-xdist integration**: Automatic worker detection
- **Load balancing**: Efficient test distribution
- **Resource optimization**: Minimal setup/teardown overhead

### Performance Monitoring
- **Built-in metrics**: Execution time tracking
- **Slow test identification**: Automatic detection of bottlenecks
- **Performance comparison**: Side-by-side execution time analysis

### Optimization Strategies
- **Session-scoped fixtures**: Reuse expensive resources
- **Lazy loading**: Load resources only when needed
- **Test categorization**: Run fast tests in parallel, slow tests sequentially

## Best Practices

### Test Writing
1. **Use function-based tests** unless you need shared setup
2. **Write descriptive test names** that explain the scenario
3. **Use appropriate fixtures** for setup and teardown
4. **Mark tests appropriately** with performance and category markers
5. **Keep tests focused** on a single behavior or scenario

### Performance
1. **Use parallel execution** for unit tests and fast tests
2. **Run slow tests sequentially** to avoid resource conflicts
3. **Monitor performance** regularly to identify bottlenecks
4. **Optimize fixtures** for better resource utilization

### Maintenance
1. **Keep tests organized** by functionality and type
2. **Update documentation** when adding new test patterns
3. **Clean up test artifacts** regularly
4. **Monitor test execution time** and optimize as needed

## Troubleshooting

### Common Issues

1. **Collection errors**: Check for duplicate parametrization or decorators
2. **Fixture not found**: Ensure fixtures are properly defined in `conftest.py`
3. **Parallel execution issues**: Some tests may not be suitable for parallel execution
4. **Performance issues**: Use `--durations=10` to identify slow tests

### Debug Commands

```bash
# Run with maximum verbosity
poetry run pytest -vv --tb=long

# Run with debug output
poetry run pytest -s --tb=long

# Run specific test with debug
poetry run pytest tests/unit/test_config.py::test_validate_cluster_name -vv -s

# Check test collection
poetry run pytest --collect-only
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_<functionality>_<scenario>`
2. **Use appropriate markers**: Mark tests with relevant categories
3. **Write comprehensive docstrings**: Explain what each test does
4. **Use fixtures**: Leverage existing fixtures or create new ones as needed
5. **Consider performance**: Mark slow tests appropriately
6. **Update documentation**: Keep this README and other docs current

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [Project Best Practices](docs/PYTEST_BEST_PRACTICES.md)
- [Test Refactoring Plan](Plans/PLAN_TEST_REFACTORING.md)
