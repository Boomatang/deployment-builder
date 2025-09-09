"""Integration tests for kind configuration management functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from deployment_builder.kind_integration import (
    run_kind_command,
    get_kind_config_path_from_config,
    generate_kind_config,
    save_kind_config,
    remove_kind_config,
)


class TestKindConfigIntegration:
    """Test kind configuration management integration."""

    def test_get_kind_config_path_from_config(self):
        """Test kind config path extraction from configuration."""
        # Test with default path
        config = {"prefix": "test"}
        path = get_kind_config_path_from_config(config)
        assert path == Path("kind-configs").resolve()

        # Test with custom path
        config = {"prefix": "test", "kind_config_path": "custom/kind-configs"}
        path = get_kind_config_path_from_config(config)
        assert path == Path("custom/kind-configs").resolve()

    def test_generate_kind_config(self):
        """Test kind configuration generation."""
        cluster_name = "test-cluster"
        config_data = {
            "networking": {"ipFamily": "ipv4", "apiServerAddress": "127.0.0.1"},
            "feature_gates": {"CSIMigration": True},
            "runtime_config": {"api/alpha": "false"},
        }

        kind_config = generate_kind_config(cluster_name, config_data)

        # Check base configuration
        assert kind_config["kind"] == "Cluster"
        assert kind_config["apiVersion"] == "kind.x-k8s.io/v1alpha4"
        assert kind_config["name"] == cluster_name

        # Check networking configuration
        assert kind_config["networking"]["ipFamily"] == "ipv4"
        assert kind_config["networking"]["apiServerAddress"] == "127.0.0.1"

        # Check feature gates
        assert kind_config["featureGates"]["CSIMigration"] is True

        # Check runtime config
        assert kind_config["runtimeConfig"]["api/alpha"] == "false"

    def test_generate_kind_config_minimal(self):
        """Test kind configuration generation with minimal config."""
        cluster_name = "test-cluster"
        config_data = {}

        kind_config = generate_kind_config(cluster_name, config_data)

        # Check base configuration only
        assert kind_config["kind"] == "Cluster"
        assert kind_config["apiVersion"] == "kind.x-k8s.io/v1alpha4"
        assert kind_config["name"] == cluster_name

        # Should not have optional fields
        assert "networking" not in kind_config
        assert "featureGates" not in kind_config
        assert "runtimeConfig" not in kind_config

    def test_save_kind_config_success(self):
        """Test successful kind config file saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            cluster_name = "test-cluster"
            kind_config = {
                "kind": "Cluster",
                "apiVersion": "kind.x-k8s.io/v1alpha4",
                "name": cluster_name,
                "networking": {"ipFamily": "ipv4"},
            }

            success = save_kind_config(cluster_name, kind_config, config_dir)

            assert success is True
            config_file = config_dir / f"{cluster_name}-kind-config.yaml"
            assert config_file.exists()

            # Verify file contents
            with open(config_file, "r") as f:
                loaded_config = yaml.safe_load(f)
            assert loaded_config == kind_config

    def test_save_kind_config_failure(self):
        """Test kind config saving failure."""
        cluster_name = "test-cluster"
        kind_config = {"kind": "Cluster"}

        # Try to save to a read-only directory (should fail)
        read_only_dir = Path("/read-only-directory")
        success = save_kind_config(cluster_name, kind_config, read_only_dir)

        assert success is False

    def test_remove_kind_config_success(self):
        """Test successful kind config removal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            cluster_name = "test-cluster"
            config_file = config_dir / f"{cluster_name}-kind-config.yaml"

            # Create a test config file
            config_file.write_text("test config content")
            assert config_file.exists()

            success = remove_kind_config(cluster_name, config_dir)

            assert success is True
            assert not config_file.exists()

    def test_remove_kind_config_nonexistent(self):
        """Test kind config removal when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            cluster_name = "nonexistent-cluster"

            success = remove_kind_config(cluster_name, config_dir)

            # Should still return True (not an error if file doesn't exist)
            assert success is True

    @patch("subprocess.run")
    def test_run_kind_command_with_kind_config(self, mock_run):
        """Test that run_kind_command adds --config flag for kind config."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Cluster created successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create test files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".kubeconfig", delete=False) as f:
            f.write("test kubeconfig content")
            kubeconfig_file = Path(f.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix="-kind-config.yaml", delete=False) as f:
            f.write("test kind config content")
            kind_config_file = Path(f.name)

        try:
            # Test create command with both kubeconfig and kind config
            success, stdout, stderr = run_kind_command(
                "create",
                "test-cluster",
                log_output=False,
                kubeconfig_file=kubeconfig_file,
                kind_config_file=kind_config_file,
            )

            # Verify the command was called with the correct arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            actual_cmd = call_args.args[0]

            # Verify the command structure includes both flags
            expected_cmd = [
                "kind",
                "create",
                "cluster",
                "--name",
                "test-cluster",
                "--kubeconfig",
                str(kubeconfig_file),
                "--config",
                str(kind_config_file),
            ]
            assert actual_cmd == expected_cmd
            assert success is True

        finally:
            # Clean up
            if kubeconfig_file.exists():
                kubeconfig_file.unlink()
            if kind_config_file.exists():
                kind_config_file.unlink()

    @patch("subprocess.run")
    def test_run_kind_command_kind_config_create_only(self, mock_run):
        """Test that --config flag is only added for create command."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Cluster deleted successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with tempfile.NamedTemporaryFile(mode="w", suffix="-kind-config.yaml", delete=False) as f:
            f.write("test kind config content")
            kind_config_file = Path(f.name)

        try:
            # Test delete command with kind config (should not add --config flag)
            success, stdout, stderr = run_kind_command(
                "delete", "test-cluster", log_output=False, kind_config_file=kind_config_file
            )

            # Verify the command was called without --config flag
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            actual_cmd = call_args.args[0]

            # Verify the command structure doesn't include --config flag
            expected_cmd = ["kind", "delete", "cluster", "--name", "test-cluster"]
            assert actual_cmd == expected_cmd
            assert success is True

        finally:
            # Clean up
            if kind_config_file.exists():
                kind_config_file.unlink()
