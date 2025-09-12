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
    get_cluster_names_from_config,
)
from deployment_builder.cli import load_config


@pytest.mark.integration
@pytest.mark.kind
def test_get_kind_config_path_from_config():
    """Test kind config path extraction from configuration."""
    # Test with default path
    config = {"prefix": "test"}
    path = get_kind_config_path_from_config(config)
    assert path == Path("kind-configs").resolve()

    # Test with custom path
    config = {"prefix": "test", "kind_config_path": "custom/kind-configs"}
    path = get_kind_config_path_from_config(config)
    assert path == Path("custom/kind-configs").resolve()


@pytest.mark.integration
@pytest.mark.kind
def test_generate_kind_config():
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


@pytest.mark.integration
@pytest.mark.kind
def test_generate_kind_config_minimal():
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


@pytest.mark.integration
@pytest.mark.kind
def test_save_kind_config_success(tmp_path):
    """Test successful kind config file saving."""
    config_dir = tmp_path
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


@pytest.mark.integration
@pytest.mark.kind
def test_save_kind_config_failure():
    """Test kind config saving failure."""
    cluster_name = "test-cluster"
    kind_config = {"kind": "Cluster"}

    # Try to save to a read-only directory (should fail)
    read_only_dir = Path("/read-only-directory")
    success = save_kind_config(cluster_name, kind_config, read_only_dir)

    assert success is False


@pytest.mark.integration
@pytest.mark.kind
def test_remove_kind_config_success(tmp_path):
    """Test successful kind config removal."""
    config_dir = tmp_path
    cluster_name = "test-cluster"
    config_file = config_dir / f"{cluster_name}-kind-config.yaml"

    # Create a test config file
    config_file.write_text("test config content")
    assert config_file.exists()

    success = remove_kind_config(cluster_name, config_dir)

    assert success is True
    assert not config_file.exists()


@pytest.mark.integration
@pytest.mark.kind
def test_remove_kind_config_nonexistent(tmp_path):
    """Test kind config removal when file doesn't exist."""
    config_dir = tmp_path
    cluster_name = "nonexistent-cluster"

    success = remove_kind_config(cluster_name, config_dir)

    # Should still return True (not an error if file doesn't exist)
    assert success is True


@pytest.mark.integration
@pytest.mark.kind
@patch("subprocess.run")
def test_run_kind_command_with_kind_config(mock_run, tmp_path):
    """Test that run_kind_command adds --config flag for kind config."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Cluster created successfully"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    # Create test files
    kubeconfig_file = tmp_path / "test.kubeconfig"
    kubeconfig_file.write_text("test kubeconfig content")

    kind_config_file = tmp_path / "test-kind-config.yaml"
    kind_config_file.write_text("test kind config content")

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


@pytest.mark.integration
@pytest.mark.kind
@patch("subprocess.run")
def test_run_kind_command_kind_config_create_only(mock_run, tmp_path):
    """Test that --config flag is only added for create command."""
    # Setup mock
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Cluster deleted successfully"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    kind_config_file = tmp_path / "test-kind-config.yaml"
    kind_config_file.write_text("test kind config content")

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


@pytest.mark.integration
@pytest.mark.kind
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
@pytest.mark.kind
def test_get_cluster_names_from_config_new_format_partial():
    """Test cluster name extraction with new format but only some clusters enabled."""
    config_data = {
        "prefix": "test-project",
        "clusters": {
            "metrics": {"enable": False, "count": 0},  # enable=False, so not created
            "primary": {"enable": True, "count": 1},
            "secondary": {"enable": True, "count": 0},  # count=0, so not created
            "standalone": {"enable": True, "count": 2},
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = [
        "test-project-primary",  # count=1, so no suffix
        "test-project-standalone-1",
        "test-project-standalone-2",
    ]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
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


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_mixed_format():
    """Test cluster name extraction with mixed format (some structured, some legacy)."""
    config_data = {
        "prefix": "test-project",
        "clusters": {
            "metrics": {"enable": True, "count": 0},  # New format, count=0 so not created
            "primary": 2,  # Legacy format
            "secondary": {"enable": True, "count": 1},  # New format
            "standalone": 0,  # Legacy format, count=0 so not created
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    # Should use new format since some values are dicts
    # standalone: 0 means no standalone clusters should be created
    expected_names = [
        # metrics has count=0, so not created
        "test-project-secondary",  # count=1, so no suffix
    ]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_no_clusters():
    """Test cluster name extraction when no clusters are defined."""
    config_data = {"prefix": "test-project", "clusters": {}}

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = ["test-project-default"]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_no_clusters_section():
    """Test cluster name extraction when clusters section is missing."""
    config_data = {"prefix": "test-project"}

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = ["test-project-default"]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_load_config_with_general_section(tmp_path):
    """Test configuration loading with [general] section."""
    import tomli

    # Create a temporary TOML file with [general] section
    config_content = """[general]
name = "test-deployment"
version = "1.0.0"
prefix = "test-project"
kubeconfig_path = "test-kubeconfigs"
kind_config_path = "test-kind-configs"

[clusters]
[clusters.metrics]
enable = true

[clusters.primary]
count = 2
"""

    config_file = tmp_path / "test.toml"
    config_file.write_text(config_content)

    # Load the configuration using the new configuration object
    from deployment_builder.config import load_config_from_file

    config_obj = load_config_from_file(str(config_file))

    # Verify that [general] section values are in the general section
    assert config_obj.general.name == "test-deployment"
    assert config_obj.general.version == "1.0.0"
    assert config_obj.general.prefix == "test-project"
    assert config_obj.general.kubeconfig_path == "test-kubeconfigs"
    assert config_obj.general.kind_config_path == "test-kind-configs"

    # Verify that clusters section is preserved
    assert config_obj.clusters["metrics"].enable is True
    assert config_obj.clusters["primary"].count == 2

    # Verify that the general section is present in the dict representation
    config_dict = config_obj.to_dict()
    assert "general" in config_dict
    assert config_dict["general"]["name"] == "test-deployment"


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_dynamic_types():
    """Test cluster name extraction with dynamic cluster types."""
    config_data = {
        "prefix": "dynamic-test",
        "clusters": {
            "gateway": {"enable": True, "count": 0},
            "api-server": {"enable": True, "count": 2},
            "database-cluster": {"enable": False, "count": 3},
            "cache_node": {"enable": True, "count": 1},
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = [
        # gateway has count=0, so not created
        "dynamic-test-api-server-1",
        "dynamic-test-api-server-2",
        # database-cluster has enable=False, so not created
        "dynamic-test-cache_node",  # count=1, so no suffix
    ]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_dynamic_types_mixed():
    """Test cluster name extraction with mixed dynamic cluster types."""
    config_data = {
        "prefix": "mixed-dynamic",
        "clusters": {
            "frontend": {"enable": True, "count": 0},  # Single cluster
            "backend": {"enable": False, "count": 2},  # Multiple, disabled
            "worker": {"enable": True, "count": 3},  # Multiple, enabled
            "monitoring": {"enable": True, "count": 0},  # Single cluster
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = [
        # frontend has count=0, so not created
        # backend has enable=False, so not created
        "mixed-dynamic-worker-1",
        "mixed-dynamic-worker-2",
        "mixed-dynamic-worker-3",
        # monitoring has count=0, so not created
    ]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_dynamic_types_performance():
    """Test cluster name extraction with many dynamic cluster types."""
    config_data = {"prefix": "performance-test", "clusters": {}}

    # Create 20 different cluster types
    for i in range(20):
        cluster_type = f"worker-{i}"
        config_data["clusters"][cluster_type] = {"enable": True, "count": 1}

    cluster_names = get_cluster_names_from_config(config_data)

    # Should have 20 cluster names
    assert len(cluster_names) == 20
    assert all(name.startswith("performance-test-worker-") for name in cluster_names)

    # Check specific names
    expected_names = [f"performance-test-worker-{i}" for i in range(20)]  # count=1, so no suffix
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_dynamic_types_special_characters():
    """Test cluster name extraction with special characters in cluster types."""
    config_data = {
        "prefix": "special-chars",
        "clusters": {
            "api-server": {"enable": True, "count": 0},
            "database_node": {"enable": True, "count": 2},
            "cache-cluster": {"enable": True, "count": 1},
        },
    }

    cluster_names = get_cluster_names_from_config(config_data)

    expected_names = [
        # api-server has count=0, so not created
        "special-chars-database_node-1",
        "special-chars-database_node-2",
        "special-chars-cache-cluster",  # count=1, so no suffix
    ]
    assert cluster_names == expected_names


@pytest.mark.integration
@pytest.mark.kind
def test_get_cluster_names_from_config_dynamic_types_validation():
    """Test cluster name extraction with invalid cluster types (should fail)."""
    from deployment_builder.config import create_default_config

    config_data = {
        "general": {"name": "invalid-test"},
        "clusters": {
            "valid-cluster": {"enable": True, "count": 0},
            "invalid!cluster": {"enable": True, "count": 0},  # Invalid name
        },
    }

    # This should fail during validation when updating the config
    config = create_default_config()
    with pytest.raises(ValueError, match="Invalid cluster type name"):
        config.update_from_dict(config_data)
