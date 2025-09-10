"""
Integration tests for CLI commands with example configuration files.

These tests verify that the CLI commands work correctly with real configuration files
from the examples directory, ensuring end-to-end functionality.
"""

import os
import tempfile
import subprocess
import pytest
from pathlib import Path


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.examples_dir = Path(__file__).parent.parent / "examples"
        self.example_files = ["config.toml", "deployment.toml", "config.json", "deployment.yaml"]

    def run_cli_command(self, command_args, expect_success=True):
        """Run a CLI command and return the result."""
        cmd = ["poetry", "run", "deploy"] + command_args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        if expect_success:
            assert result.returncode == 0, f"Command failed: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        else:
            assert result.returncode != 0, f"Command should have failed but succeeded: {cmd}\nSTDOUT: {result.stdout}"

        return result

    def test_defaults_command(self):
        """Test the defaults command."""
        result = self.run_cli_command(["defaults"])

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

    def test_create_command_dry_run_all_examples(self):
        """Test create command with --dry-run for all example files."""
        for example_file in self.example_files:
            file_path = self.examples_dir / example_file
            assert file_path.exists(), f"Example file {example_file} does not exist"

            result = self.run_cli_command(["create", "--config", str(file_path), "--dry-run"])

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

    def test_create_command_dry_run_with_short_options(self):
        """Test create command with --dry-run using short options."""
        config_file = self.examples_dir / "config.toml"

        result = self.run_cli_command(["create", "-c", str(config_file), "-n"])

        assert "DRY RUN:" in result.stdout
        assert "Would create kind clusters" in result.stdout
        assert "Total execution time:" in result.stdout

    def test_remove_command_dry_run_all_examples(self):
        """Test remove command with --dry-run for all example files."""
        for example_file in self.example_files:
            file_path = self.examples_dir / example_file
            assert file_path.exists(), f"Example file {example_file} does not exist"

            result = self.run_cli_command(["remove", "--config", str(file_path), "--dry-run"])

            # Check that dry run output contains expected elements
            assert "DRY RUN:" in result.stdout
            assert "Would remove kind clusters" in result.stdout
            assert "Total execution time:" in result.stdout

    def test_remove_command_dry_run_with_force(self):
        """Test remove command with --dry-run and --force."""
        config_file = self.examples_dir / "config.toml"

        result = self.run_cli_command(["remove", "--config", str(config_file), "--dry-run", "--force"])

        assert "DRY RUN:" in result.stdout
        assert "Would remove kind clusters" in result.stdout
        assert "Total execution time:" in result.stdout

    def test_create_command_with_nonexistent_config(self):
        """Test create command with non-existent config file."""
        result = self.run_cli_command(["create", "--config", "nonexistent.toml", "--dry-run"], expect_success=False)

        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()

    def test_create_command_with_invalid_config(self):
        """Test create command with invalid config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("invalid toml content [\n")
            temp_file = f.name

        try:
            result = self.run_cli_command(["create", "--config", temp_file, "--dry-run"], expect_success=False)

            assert result.returncode != 0
            assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()
        finally:
            os.unlink(temp_file)

    def test_help_commands(self):
        """Test that help commands work correctly."""
        # Test main help
        result = self.run_cli_command(["--help"])
        assert "Usage:" in result.stdout
        assert "Commands:" in result.stdout
        assert "create" in result.stdout
        assert "remove" in result.stdout
        assert "defaults" in result.stdout

        # Test create help
        result = self.run_cli_command(["create", "--help"])
        assert "Usage:" in result.stdout
        assert "create" in result.stdout
        assert "Options:" in result.stdout

        # Test remove help
        result = self.run_cli_command(["remove", "--help"])
        assert "Usage:" in result.stdout
        assert "remove" in result.stdout
        assert "Options:" in result.stdout

        # Test defaults help
        result = self.run_cli_command(["defaults", "--help"])
        assert "Usage:" in result.stdout
        assert "defaults" in result.stdout

    def test_config_discovery(self):
        """Test automatic config file discovery."""
        # Change to examples directory and test config discovery
        original_cwd = os.getcwd()
        try:
            os.chdir(self.examples_dir)

            # Test with config.toml (should be discovered automatically)
            cmd = ["poetry", "run", "deploy", "create", "--dry-run"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.examples_dir)

            assert result.returncode == 0, f"Command failed: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            assert "DRY RUN:" in result.stdout
            assert "my-deployment" in result.stdout

        finally:
            os.chdir(original_cwd)

    def test_environment_variable_config(self):
        """Test configuration via environment variable."""
        config_file = self.examples_dir / "config.toml"

        # Set environment variable
        env = os.environ.copy()
        env["DEPLOYMENT_CONFIG"] = str(config_file)

        cmd = ["poetry", "run", "deploy", "create", "--dry-run"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent, env=env)

        assert result.returncode == 0
        assert "DRY RUN:" in result.stdout
        assert "my-deployment" in result.stdout

    def test_services_configuration_parsing(self):
        """Test that services configuration is parsed correctly from example files."""
        for example_file in self.example_files:
            file_path = self.examples_dir / example_file
            result = self.run_cli_command(["create", "--config", str(file_path), "--dry-run"])

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

    def test_cluster_name_generation(self):
        """Test that cluster names are generated correctly from example files."""
        for example_file in self.example_files:
            file_path = self.examples_dir / example_file
            result = self.run_cli_command(["create", "--config", str(file_path), "--dry-run"])

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

    def test_max_workers_configuration(self):
        """Test that max_workers configuration is respected."""
        for example_file in self.example_files:
            file_path = self.examples_dir / example_file
            result = self.run_cli_command(["create", "--config", str(file_path), "--dry-run"])

            # Check that max_workers is included in the configuration output
            assert "max_workers" in result.stdout

            if "config" in example_file:
                assert '"max_workers": 4' in result.stdout
            elif "deployment" in example_file:
                assert '"max_workers": 6' in result.stdout
