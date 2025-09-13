"""Integration tests for kubeconfig management functionality."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from deployment_builder.kind_integration import (
    run_kind_command,
    extract_kubeconfig,
    remove_kubeconfig,
    get_kubeconfig_path_from_config,
    get_kind_config_path_from_config,
    generate_kind_config,
    save_kind_config,
    remove_kind_config,
    get_cluster_names_from_config,
)


@pytest.mark.integration
@pytest.mark.kubeconfig
@pytest.mark.config
def test_get_kubeconfig_path_from_config():
    """Test kubeconfig path extraction from configuration."""
    # Test with default path
    config = {"prefix": "test"}
    path = get_kubeconfig_path_from_config(config)
    assert path == Path("kubeconfigs").resolve()

    # Test with custom path
    config = {"prefix": "test", "kubeconfig_path": "custom/kubeconfigs"}
    path = get_kubeconfig_path_from_config(config)
    assert path == Path("custom/kubeconfigs").resolve()


@pytest.mark.integration
@pytest.mark.kubeconfig
@patch("subprocess.run")
@pytest.mark.config
def test_extract_kubeconfig_success(mock_run, tmp_path):
    """Test successful kubeconfig extraction."""
    kubeconfig_dir = tmp_path
    cluster_name = "test-cluster"

    # Mock the kind command to return a valid kubeconfig
    mock_kubeconfig_content = """apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://localhost:6443
  name: kind-test-cluster
contexts:
- context:
    cluster: kind-test-cluster
    user: kind-test-cluster
  name: kind-test-cluster
current-context: kind-test-cluster
users:
- name: kind-test-cluster
  user:
    client-certificate-data: fake-cert-data
    client-key-data: fake-key-data
"""

    mock_result = MagicMock()
    mock_result.stdout = mock_kubeconfig_content
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    success = extract_kubeconfig(cluster_name, kubeconfig_dir)

    assert success is True
    kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"
    assert kubeconfig_file.exists()
    assert kubeconfig_file.read_text() == mock_kubeconfig_content


@pytest.mark.integration
@pytest.mark.kubeconfig
@patch("subprocess.run")
@pytest.mark.config
def test_extract_kubeconfig_failure(mock_run, tmp_path):
    """Test kubeconfig extraction failure."""
    kubeconfig_dir = tmp_path
    cluster_name = "nonexistent-cluster"

    mock_run.side_effect = subprocess.CalledProcessError(1, "kind", "Cluster not found")

    success = extract_kubeconfig(cluster_name, kubeconfig_dir)

    assert success is False
    kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"
    assert not kubeconfig_file.exists()


@pytest.mark.integration
@pytest.mark.kubeconfig
@pytest.mark.config
def test_remove_kubeconfig_success(tmp_path):
    """Test successful kubeconfig removal."""
    kubeconfig_dir = tmp_path
    cluster_name = "test-cluster"
    kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"

    # Create a test kubeconfig file
    kubeconfig_file.write_text("test kubeconfig content")
    assert kubeconfig_file.exists()

    success = remove_kubeconfig(cluster_name, kubeconfig_dir)

    assert success is True
    assert not kubeconfig_file.exists()


@pytest.mark.integration
@pytest.mark.kubeconfig
@pytest.mark.config
def test_remove_kubeconfig_nonexistent(tmp_path):
    """Test kubeconfig removal when file doesn't exist."""
    kubeconfig_dir = tmp_path
    cluster_name = "nonexistent-cluster"

    success = remove_kubeconfig(cluster_name, kubeconfig_dir)

    # Should still return True (not an error if file doesn't exist)
    assert success is True


@pytest.mark.integration
@pytest.mark.kubeconfig
@patch("subprocess.run")
@pytest.mark.cli
def test_run_kind_command_with_kubeconfig(mock_run, tmp_path):
    """Test that run_kind_command adds --kubeconfig flag."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Cluster created successfully"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    # Create a test kubeconfig file
    kubeconfig_file = tmp_path / "test.kubeconfig"
    kubeconfig_file.write_text("test kubeconfig content")

    # Test the function
    success, stdout, stderr = run_kind_command(
        "create", "test-cluster", log_output=False, kubeconfig_file=kubeconfig_file
    )

    # Verify the command was called with the correct arguments
    mock_run.assert_called_once()
    call_args = mock_run.call_args

    # Verify the command structure includes --kubeconfig flag
    expected_cmd = ["kind", "create", "cluster", "--name", "test-cluster", "--kubeconfig", str(kubeconfig_file)]
    assert call_args.args[0] == expected_cmd

    assert success is True
    assert stdout == "Cluster created successfully"


@pytest.mark.integration
@pytest.mark.kubeconfig
@patch("subprocess.run")
@pytest.mark.cli
def test_run_kind_command_without_kubeconfig(mock_run):
    """Test that run_kind_command works without kubeconfig file."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Cluster created successfully"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    # Test the function without kubeconfig
    success, stdout, stderr = run_kind_command("create", "test-cluster", log_output=False, kubeconfig_file=None)

    # Verify the command was called without kubeconfig flag
    mock_run.assert_called_once()
    call_args = mock_run.call_args

    # Verify the command structure doesn't include --kubeconfig flag
    expected_cmd = ["kind", "create", "cluster", "--name", "test-cluster"]
    assert call_args.args[0] == expected_cmd

    assert success is True
    assert stdout == "Cluster created successfully"


@pytest.mark.integration
@pytest.mark.kubeconfig
@patch("subprocess.run")
@pytest.mark.cli
def test_run_kind_command_with_nonexistent_kubeconfig(mock_run):
    """Test that run_kind_command adds --kubeconfig flag even for nonexistent files."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Cluster created successfully"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    # Create a path to a nonexistent file
    nonexistent_kubeconfig = Path("/nonexistent/path/kubeconfig")

    # Test the function with nonexistent kubeconfig
    success, stdout, stderr = run_kind_command(
        "create", "test-cluster", log_output=False, kubeconfig_file=nonexistent_kubeconfig
    )

    # Verify the command was called with kubeconfig flag
    # (even though file doesn't exist)
    mock_run.assert_called_once()
    call_args = mock_run.call_args

    # Verify the command structure includes --kubeconfig flag
    expected_cmd = [
        "kind",
        "create",
        "cluster",
        "--name",
        "test-cluster",
        "--kubeconfig",
        str(nonexistent_kubeconfig),
    ]
    assert call_args.args[0] == expected_cmd

    assert success is True
    assert stdout == "Cluster created successfully"


@pytest.mark.integration
@pytest.mark.kubeconfig
@patch("subprocess.run")
@pytest.mark.cli
def test_run_kind_command_kubeconfig_flag_integration(mock_run):
    """Test that --kubeconfig flag is properly added to both create and delete commands."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Command completed successfully"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    kubeconfig_file = Path("test-kubeconfig.kubeconfig")

    # Test create command with kubeconfig
    success, stdout, stderr = run_kind_command(
        "create", "test-cluster", log_output=False, kubeconfig_file=kubeconfig_file
    )

    # Verify create command includes --kubeconfig flag
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    actual_cmd = call_args.args[0]

    expected_cmd = ["kind", "create", "cluster", "--name", "test-cluster", "--kubeconfig", str(kubeconfig_file)]
    assert actual_cmd == expected_cmd
    assert success is True

    # Reset mock for delete test
    mock_run.reset_mock()

    # Test delete command with kubeconfig
    success, stdout, stderr = run_kind_command(
        "delete", "test-cluster", log_output=False, kubeconfig_file=kubeconfig_file
    )

    # Verify delete command includes --kubeconfig flag
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    actual_cmd = call_args.args[0]

    expected_cmd = ["kind", "delete", "cluster", "--name", "test-cluster", "--kubeconfig", str(kubeconfig_file)]
    assert actual_cmd == expected_cmd
    assert success is True

    # Reset mock for nonexistent file test
    mock_run.reset_mock()

    # Test with nonexistent kubeconfig file (should still add --kubeconfig flag)
    nonexistent_kubeconfig = Path("/nonexistent/path/kubeconfig")
    success, stdout, stderr = run_kind_command(
        "create", "test-cluster", log_output=False, kubeconfig_file=nonexistent_kubeconfig
    )

    # Verify command still includes --kubeconfig flag even for nonexistent file
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    actual_cmd = call_args.args[0]

    expected_cmd = [
        "kind",
        "create",
        "cluster",
        "--name",
        "test-cluster",
        "--kubeconfig",
        str(nonexistent_kubeconfig),
    ]
    assert actual_cmd == expected_cmd
    assert success is True


@pytest.mark.integration
@pytest.mark.kubeconfig
@pytest.mark.config
def test_get_cluster_names_from_config_new_format():
    """Test cluster name extraction with new structured format."""
    config_data = {
        "prefix": "test-project",
        "clusters": {
            "metrics": {"enable": True, "count": 0},  # count=0, so not created
            "primary": {"enable": True, "count": 2},
            "secondary": {"enable": True, "count": 3},
            "standalone": {"enable": True, "count": 1},
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = [
        # metrics has count=0, so not created
        "test-project-primary-1",
        "test-project-primary-2",
        "test-project-secondary-1",
        "test-project-secondary-2",
        "test-project-secondary-3",
        "test-project-standalone",  # count=1, so no suffix
    ]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kubeconfig
@pytest.mark.config
def test_get_cluster_names_from_config_legacy_format():
    """Test cluster name extraction with legacy format (backward compatibility)."""
    config_data = {
        "prefix": "test-project",
        "clusters": {
            "metrics": True,
            "primary": 2,
            "secondary": 1,
            "standalone": 3,
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = [
        "test-project-metrics",
        "test-project-primary-1",
        "test-project-primary-2",
        "test-project-secondary-1",
        "test-project-standalone-1",
        "test-project-standalone-2",
        "test-project-standalone-3",
    ]
    assert cluster_names == expected_names
