"""
Integration tests for CLI commands with example configuration files.

These tests verify that the CLI commands work correctly with real configuration files
from the examples directory, ensuring end-to-end functionality.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.cli
def test_defaults_command(cli_runner):
    """Test the defaults command."""
    result = cli_runner(["defaults"])

    # Check that output contains expected default values
    assert "general.name = default-deployment" in result.stdout
    assert "general.version = 1.0.0" in result.stdout
    assert "general.environment = development" in result.stdout
    assert "general.prefix = default" in result.stdout
    assert "general.max_workers = 4" in result.stdout
    assert "clusters.metrics.enable = False" in result.stdout
    assert "clusters.primary.enable = False" in result.stdout
    assert "clusters.secondary.enable = False" in result.stdout
    assert "clusters.standalone.enable = False" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
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
def test_remove_command_dry_run_with_force(examples_dir, cli_runner):
    """Test remove command with --dry-run and --force."""
    config_file = examples_dir / "config.toml"

    result = cli_runner(["remove", "--config", str(config_file), "--dry-run", "--force"])

    assert "DRY RUN:" in result.stdout
    assert "Would remove kind clusters" in result.stdout
    assert "Total execution time:" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
def test_create_command_with_nonexistent_config(cli_runner):
    """Test create command with non-existent config file."""
    result = cli_runner(["create", "--config", "nonexistent.toml", "--dry-run"], expect_success=False)

    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()


@pytest.mark.integration
@pytest.mark.cli
def test_create_command_with_invalid_config(tmp_path, cli_runner):
    """Test create command with invalid config file."""
    config_file = tmp_path / "invalid.toml"
    config_file.write_text("invalid toml content [\n")

    result = cli_runner(["create", "--config", str(config_file), "--dry-run"], expect_success=False)

    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()


@pytest.mark.integration
@pytest.mark.cli
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
def test_cluster_name_generation(example_file, examples_dir, cli_runner):
    """Test that cluster names are generated correctly from example files."""
    file_path = examples_dir / example_file
    result = cli_runner(["create", "--config", str(file_path), "--dry-run"])

    # Check that cluster names are generated
    assert "Clusters to create:" in result.stdout

    if "config" in example_file:
        assert "my-project-metrics" in result.stdout
        assert "my-project-primary" in result.stdout
        assert "my-project-secondary" in result.stdout
        assert "my-project-standalone" in result.stdout
    elif "deployment" in example_file:
        assert "advanced-project-metrics" in result.stdout
        assert "advanced-project-primary" in result.stdout
        assert "advanced-project-secondary" in result.stdout
        assert "advanced-project-standalone" in result.stdout


@pytest.mark.integration
@pytest.mark.cli
@pytest.mark.parametrize("example_file", ["config.toml", "deployment.toml", "config.json", "deployment.yaml"])
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
