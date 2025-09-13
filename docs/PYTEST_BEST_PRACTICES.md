# Pytest Best Practices for deployment-builder

This document outlines the best practices for writing and organizing pytest tests in the deployment-builder project, based on pytest's design philosophy and community standards.

## Table of Contents

1. [Test Structure Philosophy](#test-structure-philosophy)
2. [Function-Based Tests (Recommended)](#function-based-tests-recommended)
3. [Class-Based Tests (When Appropriate)](#class-based-tests-when-appropriate)
4. [Test Organization](#test-organization)
5. [Naming Conventions](#naming-conventions)
6. [Fixtures and Setup](#fixtures-and-setup)
7. [Assertions and Error Messages](#assertions-and-error-messages)
8. [Test Data Management](#test-data-management)
9. [Mocking and Patching](#mocking-and-patching)
10. [Performance and Parallel Testing](#performance-and-parallel-testing)
11. [Integration vs Unit Tests](#integration-vs-unit-tests)
12. [Code Coverage](#code-coverage)
13. [Common Anti-Patterns](#common-anti-patterns)
14. [Migration Guidelines](#migration-guidelines)

## Test Structure Philosophy

### Core Principle: Function-Based Tests First

**pytest is designed around function-based tests.** This is the recommended approach because:

- **Simplicity**: Functions are easier to read and understand
- **Isolation**: Each test function is independent
- **Debugging**: Easier to debug individual test failures
- **Performance**: Slightly better performance due to less overhead
- **Pytest Features**: Full access to pytest's features like fixtures, parametrization, and markers

### When to Use Class-Based Tests

Class-based tests should only be used when you have:

1. **Shared setup/teardown logic** that applies to multiple related tests
2. **Stateful testing** where tests build upon each other
3. **Complex test data** that needs to be shared across multiple test methods
4. **Integration with unittest** (legacy compatibility)

## Function-Based Tests (Recommended)

### Basic Structure

```python
def test_function_name():
    """Test description explaining what is being tested."""
    # Arrange
    input_data = "test_value"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

### With Fixtures

```python
def test_with_fixture(sample_config):
    """Test using a fixture for setup."""
    result = process_config(sample_config)
    assert result.is_valid
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_scenarios(input_value, expected):
    """Test multiple scenarios with parametrization."""
    result = function_under_test(input_value)
    assert result == expected
```

## Class-Based Tests (When Appropriate)

### Proper Class Structure

```python
class TestFeatureName:
    """Test class for FeatureName functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup that runs before each test method."""
        self.test_data = create_test_data()
        yield
        # Cleanup after each test
        cleanup_test_data()
    
    def test_specific_behavior(self):
        """Test specific behavior of the feature."""
        result = self.feature.process(self.test_data)
        assert result.is_success
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            self.feature.process(invalid_data)
```

### When NOT to Use Classes

❌ **Don't use classes for:**
- Simple tests that don't share setup
- Tests that can be written as functions
- Grouping related tests (use modules instead)
- Avoiding code duplication (use fixtures instead)

## Test Organization

### File Structure

The project now uses a well-organized test structure:

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_config.py            # Configuration tests
│   ├── test_queue.py             # Queue system tests
│   ├── test_optimization.py      # Optimization tests
│   ├── test_execution_planner.py # Execution planning tests
│   ├── test_load_balancer.py     # Load balancer tests
│   ├── test_monitor.py           # Monitoring tests
│   ├── test_error_handler.py     # Error handling tests
│   └── test_benchmark.py         # Benchmark tests
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_cli_integration.py   # CLI integration tests
│   ├── test_kind_config_integration.py # Kind config tests
│   └── test_kubeconfig_integration.py  # Kubeconfig tests
├── pytest.ini                    # Pytest configuration
├── run_tests.py                  # Performance test runner
└── Makefile                      # Convenient test targets
```

### Module Organization

- **One test file per source module** (e.g., `test_config.py` for `config.py`)
- **Group related tests** in the same file
- **Use descriptive test names** that explain the scenario
- **Keep test files focused** on a single module or feature
- **Separate unit and integration tests** for better organization

### Test Categories

```python
# Unit tests - test individual functions/methods
@pytest.mark.unit
def test_validate_cluster_name():
    """Test cluster name validation logic."""
    assert validate_cluster_name("valid-name") is True
    assert validate_cluster_name("invalid name") is False

# Integration tests - test component interactions
@pytest.mark.integration
@pytest.mark.cli
def test_cli_create_command_with_config_file():
    """Test CLI create command with real config file."""
    result = cli_runner.invoke(create_command, ["--config", "test.toml"])
    assert result.exit_code == 0

# Performance tests - test execution speed
@pytest.mark.slow
def test_full_deployment_workflow():
    """Test complete deployment workflow from config to running clusters."""
    # Test the entire flow
```

### Test Markers

The project uses comprehensive pytest markers for test categorization:

```python
@pytest.mark.unit              # Unit tests
@pytest.mark.integration       # Integration tests
@pytest.mark.cli               # CLI command tests
@pytest.mark.config            # Configuration tests
@pytest.mark.kind              # Kind integration tests
@pytest.mark.kubeconfig        # Kubeconfig tests
@pytest.mark.slow              # Slow-running tests
@pytest.mark.fast              # Fast-running tests
```

## Naming Conventions

### Test Files
- **Pattern**: `test_*.py` or `*_test.py`
- **Examples**: `test_config.py`, `test_cli_integration.py`

### Test Functions
- **Pattern**: `test_*`
- **Descriptive**: Explain what is being tested
- **Examples**: 
  - `test_validate_cluster_name_with_valid_input()`
  - `test_create_cluster_raises_error_on_invalid_config()`
  - `test_service_queue_processes_items_in_order()`

### Test Classes (when needed)
- **Pattern**: `Test*`
- **Examples**: `TestConnectionPool`, `TestExecutionPlanner`

### Fixtures
- **Pattern**: `*_fixture` or descriptive names
- **Examples**: `sample_config`, `mock_kind_client`, `temp_config_file`

## Fixtures and Setup

### Basic Fixtures

```python
@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return DeploymentConfig(
        general=GeneralConfig(name="test", prefix="test"),
        clusters={"worker": ClusterConfig(enable=True, count=2)}
    )
```

### Scope Management

```python
@pytest.fixture(scope="session")
def shared_resource():
    """Expensive resource shared across all tests."""
    return create_expensive_resource()

@pytest.fixture(scope="function")
def fresh_state():
    """Fresh state for each test."""
    return create_fresh_state()
```

### Autouse Fixtures

```python
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically setup test environment."""
    setup_environment()
    yield
    cleanup_environment()
```

### Parametrized Fixtures

```python
@pytest.fixture(params=["toml", "json", "yaml"])
def config_format(request):
    """Test with different config formats."""
    return request.param
```

## Assertions and Error Messages

### Use Plain Assertions

```python
# ✅ Good - pytest's assertion introspection
def test_calculation():
    result = calculate(2, 3)
    assert result == 5

# ❌ Avoid - unittest style
def test_calculation():
    result = calculate(2, 3)
    self.assertEqual(result, 5)
```

### Custom Assertion Messages

```python
def test_cluster_creation():
    cluster = create_cluster("test-cluster")
    assert cluster.is_ready, f"Cluster {cluster.name} is not ready: {cluster.status}"
```

### Exception Testing

```python
def test_invalid_input_raises_error():
    with pytest.raises(ValueError, match="Invalid cluster name"):
        validate_cluster_name("invalid name")
```

### Multiple Assertions

```python
def test_complete_validation():
    result = validate_config(config)
    
    assert result.is_valid
    assert len(result.errors) == 0
    assert result.warnings == []
    assert result.cluster_count == 3
```

## Test Data Management

### Test Data Files

```
tests/
├── data/
│   ├── valid_config.toml
│   ├── invalid_config.json
│   └── sample_deployment.yaml
└── conftest.py
```

### Inline Test Data

```python
def test_config_parsing():
    config_data = {
        "general": {"name": "test", "prefix": "test"},
        "clusters": {"worker": {"enable": True, "count": 2}}
    }
    config = parse_config(config_data)
    assert config.general.name == "test"
```

### Temporary Files

```python
def test_config_file_loading(tmp_path):
    config_file = tmp_path / "test.toml"
    config_file.write_text("[general]\nname = 'test'")
    
    config = load_config_file(config_file)
    assert config.general.name == "test"
```

## Mocking and Patching

### Basic Mocking

```python
@patch('deployment_builder.kind_integration.subprocess.run')
def test_kind_cluster_creation(mock_run):
    """Test kind cluster creation with mocked subprocess."""
    mock_run.return_value.returncode = 0
    
    result = create_kind_cluster("test-cluster")
    
    assert result is True
    mock_run.assert_called_once()
```

### Mock Objects

```python
def test_service_execution():
    """Test service execution with mock."""
    mock_service = MagicMock()
    mock_service.name = "test-service"
    mock_service.execute.return_value = True
    
    result = execute_service(mock_service)
    
    assert result is True
    mock_service.execute.assert_called_once()
```

### Context Managers

```python
def test_with_context_manager():
    """Test using context manager for patching."""
    with patch('deployment_builder.config.os.path.exists') as mock_exists:
        mock_exists.return_value = True
        
        result = check_config_file("test.toml")
        assert result is True
```

## Performance and Parallel Testing

### Performance Optimization Features

The project now includes comprehensive performance optimizations:

1. **Parallel Execution**: Full support for pytest-xdist with automatic worker detection
2. **Fixture Optimization**: Session-scoped and lazy-loading fixtures
3. **Performance Monitoring**: Built-in performance metrics collection
4. **Test Categorization**: Fast/slow test markers for optimized execution

### Parallel Test Execution

The project supports multiple parallel execution strategies:

```bash
# Run all tests in parallel (auto-detect CPU cores)
poetry run pytest -n auto

# Run tests with specific number of workers
poetry run pytest -n 4

# Run only unit tests in parallel (recommended)
poetry run pytest -m unit -n auto

# Run only integration tests in parallel
poetry run pytest -m integration -n auto

# Run only fast tests in parallel
poetry run pytest -m fast -n auto

# Run slow tests sequentially (recommended)
poetry run pytest -m slow
```

### Performance Monitoring

The test suite includes built-in performance monitoring:

```bash
# Run performance comparison
poetry run python run_tests.py

# Run with performance metrics
poetry run pytest --durations=10

# Run with profiling
poetry run pytest --profile
```

### Makefile Targets

Convenient make targets for different performance scenarios:

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
```

### Performance Testing Examples

```python
def test_performance_requirement():
    """Test that operation completes within time limit."""
    start_time = time.time()
    
    result = expensive_operation()
    
    execution_time = time.time() - start_time
    assert execution_time < 1.0  # Must complete within 1 second
    assert result is not None

def test_memory_usage():
    """Test memory usage doesn't exceed limits."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Perform memory-intensive operation
    result = memory_intensive_operation()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    assert memory_increase < 100 * 1024 * 1024  # Less than 100MB
```

### Performance Best Practices

1. **Fixture Scope**: Use session-scoped fixtures for expensive resources
2. **Lazy Loading**: Load resources only when needed using lazy fixtures
3. **Resource Pooling**: Reuse expensive resources across tests
4. **Parallel Execution**: Use pytest-xdist for CPU-intensive tests
5. **Test Categorization**: Mark tests as fast/slow for optimal execution
6. **Performance Monitoring**: Use built-in metrics to identify bottlenecks

## Integration vs Unit Tests

### Unit Tests

- **Purpose**: Test individual functions/methods in isolation
- **Scope**: Single module or class
- **Dependencies**: Mocked or stubbed
- **Speed**: Fast execution
- **Location**: `test_*.py` files

```python
def test_validate_cluster_name():
    """Unit test for cluster name validation."""
    assert validate_cluster_name("valid-name") is True
    assert validate_cluster_name("invalid name") is False
```

### Integration Tests

- **Purpose**: Test component interactions
- **Scope**: Multiple modules working together
- **Dependencies**: Real or partially mocked
- **Speed**: Slower execution
- **Location**: `test_*_integration.py` files

```python
def test_cli_with_real_config_file():
    """Integration test for CLI with real config file."""
    result = cli_runner.invoke(create_command, ["--config", "examples/config.toml"])
    assert result.exit_code == 0
```

## Code Coverage

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src/deployment_builder"]
omit = ["*/tests/*", "*/conftest.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

### Running Coverage

```bash
# Run tests with coverage
poetry run pytest --cov=src/deployment_builder --cov-report=html

# Coverage report
poetry run coverage report
poetry run coverage html
```

## Common Anti-Patterns

### ❌ Don't Do This

```python
# Don't use classes for simple tests
class TestSimpleFunction:
    def test_simple_calculation(self):
        assert add(2, 3) == 5

# Don't use unittest style assertions
def test_with_unittest_style():
    self.assertEqual(result, expected)

# Don't create complex inheritance hierarchies
class BaseTestClass:
    def setup_method(self):
        # Complex setup
        pass

class TestFeatureA(BaseTestClass):
    def test_feature_a(self):
        pass

# Don't use __init__ in test classes
class TestFeature:
    def __init__(self):
        self.data = "test"  # This breaks pytest discovery
```

### ✅ Do This Instead

```python
# Use functions for simple tests
def test_simple_calculation():
    assert add(2, 3) == 5

# Use pytest assertions
def test_with_pytest_style():
    assert result == expected

# Use fixtures for shared setup
@pytest.fixture
def test_data():
    return "test"

def test_feature_a(test_data):
    assert test_data == "test"

# Use fixtures instead of __init__
@pytest.fixture
def test_data():
    return "test"
```

## Migration Guidelines

### From Class-Based to Function-Based

1. **Identify shared setup**: Move to fixtures
2. **Extract test methods**: Convert to functions
3. **Update naming**: Follow function naming conventions
4. **Test isolation**: Ensure each test is independent

### Example Migration

**Before (Class-based):**
```python
class TestConnectionPool:
    def setup_method(self):
        self.pool = ConnectionPool()
    
    def test_add_connection(self):
        self.pool.add("test")
        assert "test" in self.pool.connections
    
    def test_remove_connection(self):
        self.pool.add("test")
        self.pool.remove("test")
        assert "test" not in self.pool.connections
```

**After (Function-based):**
```python
@pytest.fixture
def connection_pool():
    return ConnectionPool()

def test_add_connection(connection_pool):
    connection_pool.add("test")
    assert "test" in connection_pool.connections

def test_remove_connection(connection_pool):
    connection_pool.add("test")
    connection_pool.remove("test")
    assert "test" not in connection_pool.connections
```

## Project-Specific Guidelines

### Current Project Status

The deployment-builder project currently uses a **mixed approach** with both class-based and function-based tests. Based on the analysis:

- **25 class-based test classes** across 5 files
- **129 function-based tests** across 4 files
- **Mixed patterns** in the same files

### Recommended Migration Strategy

1. **Phase 1**: New tests should be function-based
2. **Phase 2**: Gradually migrate existing class-based tests to function-based
3. **Phase 3**: Keep class-based tests only where truly needed (shared setup)

### Files to Prioritize for Migration

1. `test_optimization.py` - 8 classes, complex setup
2. `test_monitor.py` - 5 classes, could be simplified
3. `test_execution_planner.py` - 2 classes, good candidates for migration
4. `test_queue.py` - 5 classes, some may need to stay class-based
5. `test_load_balancer.py` - 5 classes, likely can be migrated

## Conclusion

**Function-based tests are the pytest best practice** and should be the default approach. Class-based tests should only be used when there's a clear need for shared setup/teardown logic that can't be handled with fixtures.

The current project would benefit from migrating most class-based tests to function-based tests, using fixtures for shared setup, and keeping the codebase consistent with pytest's design philosophy.

## References

- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest Parametrization](https://docs.pytest.org/en/stable/parametrize.html)
