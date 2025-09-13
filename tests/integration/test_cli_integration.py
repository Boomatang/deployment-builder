"""
Integration tests for CLI commands with example configuration files.

These tests verify that the CLI commands work correctly with real configuration files
from the examples directory, ensuring end-to-end functionality.
"""

import os
import subprocess
from pathlib import Path

import pytest


def write_toml_config(config_data, file_path):
    """Write configuration data to a TOML file."""
    with open(file_path, "w") as f:
        f.write("[general]\n")
        if "general" in config_data:
            general = config_data["general"]
            for key, value in general.items():
                if isinstance(value, str):
                    f.write(f'{key} = "{value}"\n')
                else:
                    f.write(f"{key} = {value}\n")

        if "clusters" in config_data:
            f.write("\n[clusters]\n")
            for cluster_name, cluster_config in config_data["clusters"].items():
                if isinstance(cluster_config, dict):
                    f.write(f"[{cluster_name}]\n")
                    for key, value in cluster_config.items():
                        if isinstance(value, str):
                            f.write(f'{key} = "{value}"\n')
                        else:
                            f.write(f"{key} = {value}\n")
                else:
                    f.write(f"{cluster_name} = {cluster_config}\n")

        if "services" in config_data:
            f.write("\n[services]\n")
            for service_name, service_config in config_data["services"].items():
                f.write(f"[{service_name}]\n")
                for key, value in service_config.items():
                    if isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    else:
                        f.write(f"{key} = {value}\n")


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_defaults_command(cli_runner):
    """Test the defaults command."""
    result = cli_runner(["defaults"])

    # Check that output contains expected default values
    assert "general.name = default-deployment" in result.stdout
    assert "general.version = 1.0.0" in result.stdout
    assert "general.environment = development" in result.stdout
    assert "general.prefix = default" in result.stdout
    assert "general.max_workers = 4" in result.stdout
    # Clusters are now dynamic, so no hardcoded cluster types by default


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
def test_create_command_dry_run(example_file, examples_dir, cli_runner):
    """Test create command with --dry-run for all example files."""
    file_path = examples_dir / example_file
    assert file_path.exists(), f"Example file {example_file} does not exist"

    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])

    # Check that dry run output contains expected elements
    assert "DRY RUN:" in result.stdout
    assert "Would create kind clusters" in result.stdout
    assert "Total execution time:" in result.stdout

    # Check that configuration is loaded correctly
    if "config" in example_file:
        assert "my-deployment" in result.stdout
        assert "my-project" in result.stdout
    elif "deployment" in example_file:
        assert "advanced-deployment" in result.stdout
        assert "advanced-project" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_create_command_dry_run_with_short_options(examples_dir, cli_runner):
    """Test create command with --dry-run using short options."""
    config_file = examples_dir / "config.toml"

    result = cli_runner(["create", "-c", str(config_file), "-n"])

    assert "DRY RUN:" in result.stdout
    assert "Would create kind clusters" in result.stdout
    assert "Total execution time:" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
def test_remove_command_dry_run(example_file, examples_dir, cli_runner):
    """Test remove command with --dry-run for all example files."""
    file_path = examples_dir / example_file
    assert file_path.exists(), f"Example file {example_file} does not exist"

    result = cli_runner(["remove", "--config", str(file_path), "--dry-run"])

    # Check that dry run output contains expected elements
    assert "DRY RUN:" in result.stdout
    assert "Would remove kind clusters" in result.stdout
    assert "Total execution time:" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_remove_command_dry_run_with_force(examples_dir, cli_runner):
    """Test remove command with --dry-run and --force."""
    config_file = examples_dir / "config.toml"

    result = cli_runner(["remove", "--config", str(config_file), "--dry-run", "--force"])

    assert "DRY RUN:" in result.stdout
    assert "Would remove kind clusters" in result.stdout
    assert "Total execution time:" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_create_command_with_nonexistent_config(cli_runner):
    """Test create command with non-existent config file."""
    result = cli_runner(["create", "--config", "nonexistent.toml", "--dry-run"], expect_success=False)

    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_create_command_with_invalid_config(tmp_path, cli_runner):
    """Test create command with invalid config file."""
    config_file = tmp_path / "invalid.toml"
    config_file.write_text("invalid toml content [\n")

    result = cli_runner(["create", "--config", str(config_file), "--dry-run"], expect_success=False)

    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_help_commands(cli_runner):
    """Test that help commands work correctly."""
    # Test main help
    result = cli_runner(["--help"])
    assert "Usage:" in result.stdout
    assert "Commands:" in result.stdout
    assert "create" in result.stdout
    assert "remove" in result.stdout
    assert "defaults" in result.stdout

    # Test create help
    result = cli_runner(["create", "--help"])
    assert "Usage:" in result.stdout
    assert "create" in result.stdout
    assert "Options:" in result.stdout

    # Test remove help
    result = cli_runner(["remove", "--help"])
    assert "Usage:" in result.stdout
    assert "remove" in result.stdout
    assert "Options:" in result.stdout

    # Test defaults help
    result = cli_runner(["defaults", "--help"])
    assert "Usage:" in result.stdout
    assert "defaults" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_config_discovery(examples_dir):
    """Test automatic config file discovery."""
    # Change to examples directory and test config discovery
    original_cwd = os.getcwd()
    try:
        os.chdir(examples_dir)

        # Test with config.toml (should be discovered automatically)
        cmd = ["poetry", "run", "deploy", "create", "--dry-run"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=examples_dir)

        assert result.returncode == 0, f"Command failed: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        assert "DRY RUN:" in result.stdout
        assert "my-deployment" in result.stdout

    finally:
        os.chdir(original_cwd)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_environment_variable_config(examples_dir):
    """Test configuration via environment variable."""
    config_file = examples_dir / "config.toml"

    # Set environment variable
    env = os.environ.copy()
    env["DEPLOYMENT_CONFIG"] = str(config_file)

    cmd = ["poetry", "run", "deploy", "create", "--dry-run"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent, env=env)

    assert result.returncode == 0
    assert "DRY RUN:" in result.stdout
    assert "my-deployment" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
def test_services_configuration_parsing(example_file, examples_dir, cli_runner):
    """Test that services configuration is parsed correctly from example files."""
    file_path = examples_dir / example_file
    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])

    # Check that services are included in the output
    assert "services" in result.stdout

    # Check for specific service commands
    if "config" in example_file:
        assert "kubectl get pods" in result.stdout
        assert "kubectl get nodes" in result.stdout
        assert "kubectl get namespaces" in result.stdout  # cluster-specific
    elif "deployment" in example_file:
        assert "kubectl get pods" in result.stdout
        assert "kubectl get services" in result.stdout
        assert "kubectl get ingress" in result.stdout
        assert "kubectl get namespaces" in result.stdout  # cluster-specific
        assert "kubectl get deployments" in result.stdout  # cluster-specific


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
def test_cluster_name_generation(example_file, examples_dir, cli_runner):
    """Test that cluster names are generated correctly from example files."""
    file_path = examples_dir / example_file
    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])

    # Check that cluster names are generated
    assert "Clusters to create:" in result.stdout

    if "config" in example_file:
        # metrics cluster has count=0, so it should not be created
        assert "my-project-primary" in result.stdout
        assert "my-project-secondary" in result.stdout
        assert "my-project-standalone" in result.stdout
    elif "deployment" in example_file:
        # metrics cluster has count=0, so it should not be created
        assert "advanced-project-primary" in result.stdout
        assert "advanced-project-secondary" in result.stdout
        assert "advanced-project-standalone" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types(examples_dir, cli_runner):
    """Test CLI commands with dynamic cluster types."""
    # Test with the dynamic-clusters.toml example
    result = cli_runner(["create", "--config", "examples/dynamic-clusters.toml", "--dry-run"])
    assert result.returncode == 0
    # gateway and metrics clusters have count=0, so they should not be created
    assert "demo-worker-1" in result.stdout
    assert "demo-worker-2" in result.stdout
    assert "demo-worker-3" in result.stdout
    assert "demo-database-1" in result.stdout
    assert "demo-database-2" in result.stdout
    assert "demo-cache" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_services(examples_dir, cli_runner):
    """Test CLI commands with dynamic cluster types and services."""
    # Test with the dynamic-clusters.toml example
    result = cli_runner(["create", "--config", "examples/dynamic-clusters.toml", "--dry-run"])
    assert result.returncode == 0

    # Check that services are included in the output
    assert "nginx" in result.stdout  # Gateway service
    assert "monitoring" in result.stdout  # Worker service
    assert "backup" in result.stdout  # Database service
    assert "health-check" in result.stdout  # Global service


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_validation(examples_dir, cli_runner):
    """Test CLI validation with invalid dynamic cluster types."""
    # Create a temporary config file with invalid cluster types
    import tempfile
    import json

    invalid_config = {
        "general": {"name": "invalid-test"},
        "clusters": {
            "valid-cluster": {"enable": True, "count": 0},
            "invalid!cluster": {"enable": True, "count": 0},  # Invalid name
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "Invalid cluster type name" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_performance(examples_dir, cli_runner):
    """Test CLI performance with many dynamic cluster types."""
    import tempfile
    import json

    # Create a config with many cluster types
    config = {"general": {"name": "performance-test", "prefix": "perf"}, "clusters": {}}

    # Create 20 different cluster types
    for i in range(20):
        cluster_type = f"worker-{i}"
        config["clusters"][cluster_type] = {"count": 1}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that all cluster names are generated
        for i in range(20):
            assert f"perf-worker-{i}" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_mixed_format(examples_dir, cli_runner):
    """Test CLI with mixed dynamic cluster types (single and multiple)."""
    import tempfile
    import json

    config = {
        "general": {"name": "mixed-test", "prefix": "mixed"},
        "clusters": {
            "gateway": {"enable": True, "count": 0},  # Single cluster
            "worker": {"enable": False, "count": 3},  # Multiple, disabled
            "database": {"enable": True, "count": 2},  # Multiple, enabled
            "monitoring": {"enable": True, "count": 0},  # Single cluster
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check expected cluster names
        # gateway and monitoring have count=0, so they should not be created
        # worker is disabled (enable: false), so not included
        assert "mixed-database-1" in result.stdout
        assert "mixed-database-2" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_service_execution(examples_dir, cli_runner):
    """Test CLI service execution with dynamic cluster types."""
    # Test with the dynamic-clusters.toml example
    result = cli_runner(["create", "--config", "examples/dynamic-clusters.toml", "--dry-run"])
    assert result.returncode == 0

    # Check that service configuration is included in dry-run output
    assert "nginx" in result.stdout  # Gateway service
    assert "monitoring" in result.stdout  # Worker service
    assert "backup" in result.stdout  # Database service
    assert "health-check" in result.stdout  # Global service


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_global_services(examples_dir, cli_runner):
    """Test CLI with global services and dynamic cluster types."""
    import tempfile
    import json

    config = {
        "general": {"name": "global-test", "prefix": "global"},
        "clusters": {
            "worker": {"count": 2},
            "database": {"count": 1},
        },
        "services": {"global": {"cmd": "kubectl apply -f global-service.yaml", "kubeconfig.flag": "--kubeconfig"}},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that global service is executed for all clusters
        assert "global-worker-1" in result.stdout
        assert "global-worker-2" in result.stdout
        assert "global-database" in result.stdout

        # Check that global service command is included
        assert "kubectl apply -f global-service.yaml" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_cluster_specific_services(examples_dir, cli_runner):
    """Test CLI with cluster-specific services and dynamic cluster types."""
    import tempfile
    import json

    config = {
        "general": {"name": "specific-test", "prefix": "specific"},
        "clusters": {
            "worker": {"count": 2},
            "database": {"count": 1},
        },
        "services": {
            "worker": {"cmd": "kubectl apply -f worker-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "database": {"cmd": "kubectl apply -f database-service.yaml", "kubeconfig.flag": "--kubeconfig"},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that cluster-specific services are executed
        assert "kubectl apply -f worker-service.yaml" in result.stdout
        assert "kubectl apply -f database-service.yaml" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_validation_errors(examples_dir, cli_runner):
    """Test CLI validation error handling with dynamic cluster types."""
    import tempfile
    import json

    # Test invalid cluster type name
    invalid_config = {
        "general": {"name": "invalid-test"},
        "clusters": {
            "valid-cluster": {"enable": True, "count": 0},
            "invalid!cluster": {"enable": True, "count": 0},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "Invalid cluster type name" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_count_validation(examples_dir, cli_runner):
    """Test CLI count validation with dynamic cluster types."""
    import tempfile
    import json

    # Test count exceeding limit
    invalid_config = {
        "general": {"name": "count-test"},
        "clusters": {
            "worker": {"count": 150},  # Exceeds 100 limit
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "exceeds maximum allowed" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_service_validation(examples_dir, cli_runner):
    """Test CLI service validation with dynamic cluster types."""
    import tempfile
    import json

    # Test invalid service configuration
    invalid_config = {
        "general": {"name": "service-test"},
        "clusters": {
            "worker": {"count": 1},
        },
        "services": {
            "worker": {
                "cmd": "kubectl apply -f worker-service.yaml"
                # Missing kubeconfig.flag
            }
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "must have kubeconfig.flag" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_missing_required_fields(examples_dir, cli_runner):
    """Test CLI with missing required fields in dynamic cluster types."""
    import tempfile
    import json

    # Test missing enable and count
    invalid_config = {
        "general": {"name": "missing-test"},
        "clusters": {
            "worker": {},  # Missing both enable and count
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "must have either 'enable' or 'count'" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_invalid_types(examples_dir, cli_runner):
    """Test CLI with invalid types in dynamic cluster types."""
    import tempfile
    import json

    # Test invalid types
    invalid_config = {
        "general": {"name": "type-test", "max_workers": "invalid"},
        "clusters": {
            "worker": {"enable": "invalid", "count": "invalid"},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "must be an integer" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_backward_compatibility(examples_dir, cli_runner):
    """Test CLI backward compatibility with legacy cluster formats."""
    import tempfile
    import json

    # Test legacy boolean format
    legacy_config = {
        "general": {"name": "legacy-test", "prefix": "legacy"},
        "clusters": {
            "worker": True,  # Legacy boolean format
            "database": False,  # Legacy boolean format
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(legacy_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that legacy format is handled correctly
        assert "legacy-worker" in result.stdout
        # database should not be included (False)
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_mixed_legacy_new(examples_dir, cli_runner):
    """Test CLI with mixed legacy and new cluster formats."""
    import tempfile
    import json

    # Test mixed format
    mixed_config = {
        "general": {"name": "mixed-test", "prefix": "mixed"},
        "clusters": {
            "worker": True,  # Legacy boolean
            "database": {"count": 2},  # New format
            "monitoring": {"enable": True, "count": 0},  # New format
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(mixed_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that both formats work
        assert "mixed-worker" in result.stdout
        assert "mixed-database-1" in result.stdout
        assert "mixed-database-2" in result.stdout
        # monitoring has count=0, so it should not be created
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_no_general_section(examples_dir, cli_runner):
    """Test CLI with dynamic cluster types and no general section (legacy)."""
    import tempfile
    import json

    # Test without general section
    no_general_config = {
        "clusters": {
            "worker": {"count": 1},
            "database": {"enable": True, "count": 0},
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(no_general_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that clusters are created with default names
        assert "default-worker" in result.stdout
        # database has count=0, so it should not be created
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_edge_cases(examples_dir, cli_runner):
    """Test CLI edge cases with dynamic cluster types."""
    import tempfile
    import json

    # Test edge cases
    edge_config = {
        "general": {"name": "edge-test", "prefix": "edge"},
        "clusters": {
            "a": {"count": 1},  # Single character
            "very-long-cluster-type-name": {"count": 1},  # Long name
            "cluster-with-dashes": {"count": 1},  # Dashes
            "cluster_with_underscores": {"count": 1},  # Underscores
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(edge_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that edge cases work
        assert "edge-a" in result.stdout
        assert "edge-very-long-cluster-type-name" in result.stdout
        assert "edge-cluster-with-dashes" in result.stdout
        assert "edge-cluster_with_underscores" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_zero_count(examples_dir, cli_runner):
    """Test CLI with zero count clusters."""
    import tempfile
    import json

    # Test zero count
    zero_config = {
        "general": {"name": "zero-test", "prefix": "zero"},
        "clusters": {
            "worker": {"count": 0},  # Zero count
            "database": {"enable": True, "count": 0},  # Zero count with enable
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(zero_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that zero count clusters are not created
        assert "zero-worker" not in result.stdout
        assert "zero-database" not in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_disabled_clusters(examples_dir, cli_runner):
    """Test CLI with disabled clusters."""
    import tempfile
    import json

    # Test disabled clusters
    disabled_config = {
        "general": {"name": "disabled-test", "prefix": "disabled"},
        "clusters": {
            "worker": {"enable": False, "count": 2},  # Disabled
            "database": {"enable": False, "count": 0},  # Disabled with zero count
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(disabled_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that disabled clusters are not created
        assert "disabled-worker" not in result.stdout
        assert "disabled-database" not in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_negative_count(examples_dir, cli_runner):
    """Test CLI with negative count clusters."""
    import tempfile
    import json

    # Test negative count
    negative_config = {
        "general": {"name": "negative-test"},
        "clusters": {
            "worker": {"count": -1},  # Negative count
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(negative_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "must be non-negative" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_performance_many_types(examples_dir, cli_runner):
    """Test CLI performance with many different cluster types."""
    import tempfile
    import json

    # Test with many cluster types
    many_types_config = {"general": {"name": "many-types-test", "prefix": "many"}, "clusters": {}}

    # Create 50 different cluster types
    for i in range(50):
        cluster_type = f"type-{i:02d}"
        many_types_config["clusters"][cluster_type] = {"count": 1}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(many_types_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that all cluster types are created
        for i in range(50):
            assert f"many-type-{i:02d}" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_performance_many_clusters(examples_dir, cli_runner):
    """Test CLI performance with many clusters of same type."""
    import tempfile
    import json

    # Test with many clusters of same type
    many_clusters_config = {
        "general": {"name": "many-clusters-test", "prefix": "many"},
        "clusters": {
            "worker": {"count": 50},  # 50 clusters of same type
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(many_clusters_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that all clusters are created
        for i in range(1, 51):
            assert f"many-worker-{i}" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_performance_mixed(examples_dir, cli_runner):
    """Test CLI performance with mixed cluster types and counts."""
    import tempfile
    import json

    # Test with mixed configuration
    mixed_config = {"general": {"name": "mixed-performance-test", "prefix": "mixed"}, "clusters": {}}

    # Create mixed configuration
    for i in range(10):
        cluster_type = f"type-{i}"
        if i % 2 == 0:
            mixed_config["clusters"][cluster_type] = {"count": 5}
        else:
            mixed_config["clusters"][cluster_type] = {"enable": True, "count": 0}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(mixed_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that enabled clusters are created
        for i in range(10):
            if i % 2 == 0:
                for j in range(1, 6):
                    assert f"mixed-type-{i}-{j}" in result.stdout
            # Odd-numbered clusters have count=0, so they should not be created
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_service_execution_complex(examples_dir, cli_runner):
    """Test CLI service execution with complex dynamic cluster types."""
    import tempfile
    import json

    # Test complex service execution
    complex_config = {
        "general": {"name": "complex-test", "prefix": "complex"},
        "clusters": {
            "gateway": {"count": 1},
            "worker": {"count": 3},
            "database": {"count": 2},
            "monitoring": {"count": 1},
        },
        "services": {
            "gateway": {"cmd": "kubectl apply -f gateway-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "worker": {"cmd": "kubectl apply -f worker-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "database": {"cmd": "kubectl apply -f database-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "monitoring": {"cmd": "kubectl apply -f monitoring-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "global": {"cmd": "kubectl apply -f global-service.yaml", "kubeconfig.flag": "--kubeconfig"},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(complex_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that all clusters are created
        assert "complex-gateway" in result.stdout
        assert "complex-worker-1" in result.stdout
        assert "complex-worker-2" in result.stdout
        assert "complex-worker-3" in result.stdout
        assert "complex-database-1" in result.stdout
        assert "complex-database-2" in result.stdout
        assert "complex-monitoring" in result.stdout

        # Check that services are executed
        assert "kubectl apply -f gateway-service.yaml" in result.stdout
        assert "kubectl apply -f worker-service.yaml" in result.stdout
        assert "kubectl apply -f database-service.yaml" in result.stdout
        assert "kubectl apply -f monitoring-service.yaml" in result.stdout
        assert "kubectl apply -f global-service.yaml" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_service_execution_mixed(examples_dir, cli_runner):
    """Test CLI service execution with mixed cluster types and services."""
    import tempfile
    import json

    # Test mixed service execution
    mixed_config = {
        "general": {"name": "mixed-service-test", "prefix": "mixed"},
        "clusters": {
            "worker": {"count": 2},
            "database": {"enable": True, "count": 0},
            "monitoring": {"count": 1},
        },
        "services": {
            "worker": {"cmd": "kubectl apply -f worker-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "monitoring": {"cmd": "kubectl apply -f monitoring-service.yaml", "kubeconfig.flag": "--kubeconfig"},
            "global": {"cmd": "kubectl apply -f global-service.yaml", "kubeconfig.flag": "--kubeconfig"},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(mixed_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"])
        assert result.returncode == 0

        # Check that clusters are created
        assert "mixed-worker-1" in result.stdout
        assert "mixed-worker-2" in result.stdout
        # database has count=0, so it should not be created
        assert "mixed-monitoring" in result.stdout

        # Check that services are executed
        assert "kubectl apply -f worker-service.yaml" in result.stdout
        assert "kubectl apply -f monitoring-service.yaml" in result.stdout
        assert "kubectl apply -f global-service.yaml" in result.stdout
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
@pytest.mark.cli
@pytest.mark.integration
def test_max_workers_configuration(example_file, examples_dir, cli_runner):
    """Test that max_workers configuration is respected."""
    file_path = examples_dir / example_file
    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])

    # Check that max_workers is included in the configuration output
    assert "max_workers" in result.stdout

    if "config" in example_file:
        assert '"max_workers": 4' in result.stdout
    elif "deployment" in example_file:
        assert '"max_workers": 6' in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_validation_comprehensive(examples_dir, cli_runner):
    """Test CLI comprehensive validation with dynamic cluster types."""
    import tempfile
    import json

    # Test comprehensive validation
    invalid_config = {
        "general": {"name": "validation-test", "max_workers": "invalid"},
        "clusters": {
            "worker": {"count": -1},  # Negative count
            "database": {"enable": "invalid"},  # Invalid enable type
            "monitoring": {},  # Missing required fields
        },
        "services": {
            "worker": {
                "kubeconfig.flag": "--kubeconfig",
                "cmd": "kubectl apply -f worker-service.yaml",
            }
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1

        # Check that validation errors are caught
        assert "must be an integer" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_validation_limits(examples_dir, cli_runner):
    """Test CLI validation limits with dynamic cluster types."""
    import tempfile
    import json

    # Test count limits
    limit_config = {
        "general": {"name": "limit-test"},
        "clusters": {
            "worker": {"count": 150},  # Exceeds 100 limit
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(limit_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "exceeds maximum allowed" in result.stderr
    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.integration
def test_cli_with_dynamic_cluster_types_validation_names(examples_dir, cli_runner):
    """Test CLI validation of cluster type names."""
    import tempfile
    import json

    # Test invalid names
    invalid_names_config = {
        "general": {"name": "names-test"},
        "clusters": {
            "valid-cluster": {"count": 1},
            "invalid!cluster": {"count": 1},  # Invalid character
            "": {"count": 1},  # Empty name
            "cluster with spaces": {"count": 1},  # Spaces
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(invalid_names_config))
        temp_file = f.name

    try:
        result = cli_runner(["create", "--config", temp_file, "--dry-run"], expect_success=False)
        assert result.returncode == 1
        assert "Invalid cluster type name" in result.stderr
    finally:
        import os

        os.unlink(temp_file)
