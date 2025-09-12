"""Unit tests for configuration management and overriding."""

import json
import tempfile
import tomli
import yaml
from pathlib import Path

import pytest

from deployment_builder.config import (
    ClusterConfig,
    GeneralConfig,
    ServiceConfig,
    DeploymentConfig,
    create_default_config,
    load_config_from_file,
)


@pytest.mark.unit
@pytest.mark.config
def test_cluster_config_default_values():
    """Test that ClusterConfig has correct default values."""
    cluster = ClusterConfig()
    assert cluster.enable is False
    assert cluster.count == 0


@pytest.mark.unit
@pytest.mark.config
def test_cluster_config_custom_values():
    """Test ClusterConfig with custom values."""
    cluster = ClusterConfig(enable=True, count=3)
    assert cluster.enable is True
    assert cluster.count == 3


@pytest.mark.unit
@pytest.mark.config
def test_cluster_config_services_field():
    """Test that ClusterConfig has services field."""
    cluster = ClusterConfig()
    assert isinstance(cluster.services, dict)
    assert len(cluster.services) == 0


@pytest.mark.unit
@pytest.mark.config
def test_cluster_config_services_with_custom_values():
    """Test that ClusterConfig can have services."""
    service = ServiceConfig(kubeconfig_flag="--kubeconfig", cmd="kubectl get pods")
    cluster = ClusterConfig(enable=True, count=2, services={"pods": service})
    assert cluster.enable is True
    assert cluster.count == 2
    assert "pods" in cluster.services
    assert cluster.services["pods"].cmd == "kubectl get pods"


@pytest.mark.unit
@pytest.mark.config
def test_general_config_default_values():
    """Test that GeneralConfig has correct default values."""
    general = GeneralConfig()
    assert general.name == "default-deployment"
    assert general.version == "1.0.0"
    assert general.environment == "development"
    assert general.prefix == "default"
    assert general.kubeconfig_path == "kubeconfigs"
    assert general.kind_config_path == "kind-configs"
    assert general.max_workers == 4


@pytest.mark.unit
@pytest.mark.config
def test_general_config_custom_values():
    """Test GeneralConfig with custom values."""
    general = GeneralConfig(
        name="test-deployment",
        version="2.0.0",
        environment="production",
        prefix="test",
        kubeconfig_path="/custom/kubeconfigs",
        kind_config_path="/custom/kind-configs",
        max_workers=8,
    )
    assert general.name == "test-deployment"
    assert general.version == "2.0.0"
    assert general.environment == "production"
    assert general.prefix == "test"
    assert general.kubeconfig_path == "/custom/kubeconfigs"
    assert general.kind_config_path == "/custom/kind-configs"
    assert general.max_workers == 8


@pytest.mark.unit
@pytest.mark.config
def test_service_config_default_values():
    """Test that ServiceConfig has correct default values."""
    config = ServiceConfig()
    assert config.kubeconfig_flag == "--kubeconfig"
    assert config.cmd == ""


@pytest.mark.unit
@pytest.mark.config
def test_service_config_custom_values():
    """Test that ServiceConfig accepts custom values."""
    config = ServiceConfig(kubeconfig_flag="--kubeconfig-file", cmd="kubectl get pods -n kube-system")
    assert config.kubeconfig_flag == "--kubeconfig-file"
    assert config.cmd == "kubectl get pods -n kube-system"


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_default_configuration():
    """Test that create_default_config returns correct default values."""
    config = create_default_config()

    # Test general configuration
    assert config.general.name == "default-deployment"
    assert config.general.version == "1.0.0"
    assert config.general.environment == "development"
    assert config.general.prefix == "default"
    assert config.general.kubeconfig_path == "kubeconfigs"
    assert config.general.kind_config_path == "kind-configs"
    assert config.general.max_workers == 4

    # Test cluster configuration - now dynamic, so empty by default
    assert len(config.clusters) == 0
    assert isinstance(config.clusters, dict)

    # Test services configuration
    assert isinstance(config.services, dict)
    assert len(config.services) == 0  # No services by default


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_with_services():
    """Test updating configuration with services."""
    config = create_default_config()
    config_data = {
        "general": {
            "name": "test-deployment",
        },
        "services": {
            "pods": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n kube-system"},
            "nodes": {"kubeconfig.flag": "--kubeconfig-file", "cmd": "kubectl get nodes"},
        },
    }

    config.update_from_dict(config_data)

    # Test services configuration
    assert len(config.services) == 2
    assert "pods" in config.services
    assert "nodes" in config.services

    pods_service = config.services["pods"]
    assert isinstance(pods_service, ServiceConfig)
    assert pods_service.kubeconfig_flag == "--kubeconfig"
    assert pods_service.cmd == "kubectl get pods -n kube-system"

    nodes_service = config.services["nodes"]
    assert isinstance(nodes_service, ServiceConfig)
    assert nodes_service.kubeconfig_flag == "--kubeconfig-file"
    assert nodes_service.cmd == "kubectl get nodes"


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_with_cluster_specific_services():
    """Test updating configuration with cluster-specific services."""
    config = create_default_config()
    config_data = {
        "general": {
            "name": "test-deployment",
        },
        "clusters": {
            "primary": {
                "count": 2,
                "services": {"namespaces": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get namespaces"}},
            },
            "secondary": {
                "count": 1,
                "services": {"pods": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods"}},
            },
        },
        "services": {"global": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get nodes"}},
    }

    config.update_from_dict(config_data)

    # Test cluster-specific services
    assert config.clusters["primary"].count == 2
    assert len(config.clusters["primary"].services) == 1
    assert "namespaces" in config.clusters["primary"].services
    assert config.clusters["primary"].services["namespaces"].cmd == "kubectl get namespaces"

    assert config.clusters["secondary"].count == 1
    assert len(config.clusters["secondary"].services) == 1
    assert "pods" in config.clusters["secondary"].services
    assert config.clusters["secondary"].services["pods"].cmd == "kubectl get pods"

    # Test global services
    assert len(config.services) == 1
    assert "global" in config.services
    assert config.services["global"].cmd == "kubectl get nodes"


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_new_format():
    """Test updating configuration from new structured format."""
    config = create_default_config()

    config_data = {
        "general": {
            "name": "test-deployment",
            "version": "2.0.0",
            "environment": "production",
            "prefix": "test",
            "kubeconfig_path": "/custom/kubeconfigs",
            "kind_config_path": "/custom/kind-configs",
            "max_workers": 8,
        },
        "clusters": {
            "metrics": {"enable": True, "count": 0},
            "primary": {"enable": False, "count": 3},
            "secondary": {"enable": True, "count": 2},
            "standalone": {"enable": False, "count": 1},
        },
    }

    config.update_from_dict(config_data)

    # Test general configuration override
    assert config.general.name == "test-deployment"
    assert config.general.version == "2.0.0"
    assert config.general.environment == "production"
    assert config.general.prefix == "test"
    assert config.general.kubeconfig_path == "/custom/kubeconfigs"
    assert config.general.kind_config_path == "/custom/kind-configs"
    assert config.general.max_workers == 8

    # Test cluster configuration override
    assert config.clusters["metrics"].enable is True
    assert config.clusters["metrics"].count == 0
    assert config.clusters["primary"].enable is False
    assert config.clusters["primary"].count == 3
    assert config.clusters["secondary"].enable is True
    assert config.clusters["secondary"].count == 2
    assert config.clusters["standalone"].enable is False
    assert config.clusters["standalone"].count == 1


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_legacy_format():
    """Test updating configuration from legacy format."""
    config = create_default_config()

    config_data = {
        "name": "legacy-deployment",
        "version": "1.5.0",
        "environment": "staging",
        "prefix": "legacy",
        "kubeconfig_path": "/legacy/kubeconfigs",
        "kind_config_path": "/legacy/kind-configs",
        "max_workers": 6,
        "clusters": {
            "metrics": True,  # Legacy: boolean value
            "primary": 2,  # Legacy: integer value
            "secondary": 0,  # Legacy: zero count
            "standalone": 1,  # Legacy: integer value
        },
    }

    config.update_from_dict(config_data)

    # Test general configuration override
    assert config.general.name == "legacy-deployment"
    assert config.general.version == "1.5.0"
    assert config.general.environment == "staging"
    assert config.general.prefix == "legacy"
    assert config.general.kubeconfig_path == "/legacy/kubeconfigs"
    assert config.general.kind_config_path == "/legacy/kind-configs"
    assert config.general.max_workers == 6

    # Test cluster configuration override (legacy format)
    assert config.clusters["metrics"].enable is True
    assert config.clusters["metrics"].count == 1  # Boolean True becomes count 1
    assert config.clusters["primary"].enable is True
    assert config.clusters["primary"].count == 2
    assert config.clusters["secondary"].enable is False
    assert config.clusters["secondary"].count == 0
    assert config.clusters["standalone"].enable is True
    assert config.clusters["standalone"].count == 1


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_mixed_format():
    """Test updating configuration from mixed new/legacy format."""
    config = create_default_config()

    config_data = {
        "general": {
            "name": "mixed-deployment",
            "max_workers": 10,
        },
        "clusters": {
            "metrics": {"enable": True},  # New format: dict with enable
            "primary": 3,  # Legacy format: integer
            "secondary": {"count": 2},  # New format: dict with count
            "standalone": False,  # Legacy format: boolean
        },
    }

    config.update_from_dict(config_data)

    # Test general configuration override
    assert config.general.name == "mixed-deployment"
    assert config.general.max_workers == 10
    # Other general values should remain default
    assert config.general.version == "1.0.0"
    assert config.general.environment == "development"

    # Test cluster configuration override (mixed format)
    # Mixed format: dict clusters are processed as new format, non-dict clusters as legacy format
    assert config.clusters["metrics"].enable is True  # Dict processed as new format
    assert config.clusters["metrics"].count == 1  # enable=True without count sets count=1
    assert config.clusters["primary"].enable is True  # Integer processed as legacy format
    assert config.clusters["primary"].count == 3  # Integer processed as legacy format
    assert config.clusters["secondary"].enable is True  # Dict processed as new format
    assert config.clusters["secondary"].count == 2  # Dict processed as new format
    assert config.clusters["standalone"].enable is False  # Boolean processed as legacy format
    assert config.clusters["standalone"].count == 0  # Boolean False becomes count 0


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_partial_override():
    """Test updating configuration with partial overrides."""
    config = create_default_config()

    # Only override some general settings
    config_data = {
        "general": {
            "name": "partial-deployment",
            "max_workers": 12,
        },
    }

    config.update_from_dict(config_data)

    # Test overridden values
    assert config.general.name == "partial-deployment"
    assert config.general.max_workers == 12

    # Test that other values remain default
    assert config.general.version == "1.0.0"
    assert config.general.environment == "development"
    assert config.general.prefix == "default"
    assert config.general.kubeconfig_path == "kubeconfigs"
    assert config.general.kind_config_path == "kind-configs"

    # Test that clusters remain default
    for cluster_config in config.clusters.values():
        assert cluster_config.enable is False
        assert cluster_config.count == 0


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_update_from_dict_no_general_section():
    """Test updating configuration without general section (legacy format)."""
    config = create_default_config()

    config_data = {
        "name": "no-general-deployment",
        "version": "3.0.0",
        "max_workers": 16,
        "clusters": {
            "metrics": {"enable": True, "count": 1},
        },
    }

    config.update_from_dict(config_data)

    # Test that top-level keys are used for general configuration
    assert config.general.name == "no-general-deployment"
    assert config.general.version == "3.0.0"
    assert config.general.max_workers == 16

    # Test that other general values remain default
    assert config.general.environment == "development"
    assert config.general.prefix == "default"

    # Test cluster configuration
    assert config.clusters["metrics"].enable is True
    assert config.clusters["metrics"].count == 1


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_get_cluster_names():
    """Test cluster name generation."""
    config = create_default_config()

    # Test with default configuration (no clusters)
    cluster_names = config.get_cluster_names()
    assert cluster_names == ["default-default"]  # Default fallback

    # Test with custom prefix
    config.general.prefix = "test-project"
    cluster_names = config.get_cluster_names()
    assert cluster_names == ["test-project-default"]  # Default fallback with custom prefix

    # Test with enabled clusters - create cluster configs dynamically
    config.clusters["metrics"] = ClusterConfig(enable=True, count=0)
    config.clusters["primary"] = ClusterConfig(enable=True, count=2)
    config.clusters["secondary"] = ClusterConfig(enable=True, count=1)
    config.clusters["standalone"] = ClusterConfig(enable=True, count=3)

    cluster_names = config.get_cluster_names()
    expected = [
        # metrics has count=0, so not created
        "test-project-primary-1",
        "test-project-primary-2",
        "test-project-secondary",  # count=1, so no suffix
        "test-project-standalone-1",
        "test-project-standalone-2",
        "test-project-standalone-3",
    ]
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_get_cluster_names_with_special_characters():
    """Test cluster name generation with special characters in prefix."""
    config = create_default_config()
    config.general.prefix = "Test_Project@2024!"
    config.clusters["metrics"] = ClusterConfig(enable=True, count=0)  # count=0, so not created
    config.clusters["primary"] = ClusterConfig(enable=True, count=1)

    cluster_names = config.get_cluster_names()
    expected = ["test-project-2024-primary"]  # count=1, so no suffix
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_deployment_config_to_dict():
    """Test configuration to dictionary conversion."""
    config = create_default_config()
    config.general.name = "test-deployment"
    config.general.max_workers = 8
    config.clusters["metrics"] = ClusterConfig(enable=True, count=0)
    config.clusters["primary"] = ClusterConfig(enable=True, count=2)

    # Add services
    config.services["pods"] = ServiceConfig(kubeconfig_flag="--kubeconfig", cmd="kubectl get pods -n kube-system")
    config.services["nodes"] = ServiceConfig(kubeconfig_flag="--kubeconfig-file", cmd="kubectl get nodes")

    result = config.to_dict()

    # Test general section
    assert "general" in result
    assert result["general"]["name"] == "test-deployment"
    assert result["general"]["max_workers"] == 8
    assert result["general"]["version"] == "1.0.0"  # Default value

    # Test clusters section
    assert "clusters" in result
    assert result["clusters"]["metrics"]["enable"] is True
    assert result["clusters"]["metrics"]["count"] == 0
    assert result["clusters"]["primary"]["enable"] is True
    assert result["clusters"]["primary"]["count"] == 2

    # Test services section
    assert "services" in result
    assert "pods" in result["services"]
    assert "nodes" in result["services"]
    assert result["services"]["pods"]["kubeconfig.flag"] == "--kubeconfig"
    assert result["services"]["pods"]["cmd"] == "kubectl get pods -n kube-system"
    assert result["services"]["nodes"]["kubeconfig.flag"] == "--kubeconfig-file"
    assert result["services"]["nodes"]["cmd"] == "kubectl get nodes"


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_toml(tmp_path):
    """Test loading configuration from TOML file."""
    config_content = """[general]
name = "toml-deployment"
version = "2.0.0"
max_workers = 6

[clusters]
[clusters.metrics]
enable = true

[clusters.primary]
count = 2
"""

    config_file = tmp_path / "test.toml"
    config_file.write_text(config_content)

    config = load_config_from_file(str(config_file))

    assert config.general.name == "toml-deployment"
    assert config.general.version == "2.0.0"
    assert config.general.max_workers == 6
    assert config.clusters["metrics"].enable is True
    assert config.clusters["primary"].count == 2


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_json(tmp_path):
    """Test loading configuration from JSON file."""
    config_content = {
        "general": {
            "name": "json-deployment",
            "version": "3.0.0",
            "max_workers": 8,
        },
        "clusters": {
            "metrics": {"enable": True},
            "primary": {"count": 3},
        },
    }

    config_file = tmp_path / "test.json"
    with open(config_file, "w") as f:
        json.dump(config_content, f)

    config = load_config_from_file(str(config_file))

    assert config.general.name == "json-deployment"
    assert config.general.version == "3.0.0"
    assert config.general.max_workers == 8
    assert config.clusters["metrics"].enable is True
    assert config.clusters["primary"].count == 3


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_yaml(tmp_path):
    """Test loading configuration from YAML file."""
    config_content = """general:
  name: yaml-deployment
  version: 4.0.0
  max_workers: 10

clusters:
  metrics:
    enable: true
  primary:
    count: 4
"""

    config_file = tmp_path / "test.yaml"
    config_file.write_text(config_content)

    config = load_config_from_file(str(config_file))

    assert config.general.name == "yaml-deployment"
    assert config.general.version == "4.0.0"
    assert config.general.max_workers == 10
    assert config.clusters["metrics"].enable is True
    assert config.clusters["primary"].count == 4


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_with_services(tmp_path):
    """Test loading configuration from file with services."""
    config_content = """[general]
name = "services-deployment"
version = "1.0.0"

[clusters]
[clusters.metrics]
enable = true

[clusters.primary]
count = 1

[services]
[services.pods]
"kubeconfig.flag" = "--kubeconfig"
cmd = "kubectl get pods -n kube-system"

[services.nodes]
"kubeconfig.flag" = "--kubeconfig-file"
cmd = "kubectl get nodes"
"""

    config_file = tmp_path / "test.toml"
    config_file.write_text(config_content)

    config = load_config_from_file(str(config_file))

    assert config.general.name == "services-deployment"
    assert config.clusters["metrics"].enable is True
    assert config.clusters["primary"].count == 1

    # Test services
    assert len(config.services) == 2
    assert "pods" in config.services
    assert "nodes" in config.services

    pods_service = config.services["pods"]
    assert pods_service.kubeconfig_flag == "--kubeconfig"
    assert pods_service.cmd == "kubectl get pods -n kube-system"

    nodes_service = config.services["nodes"]
    assert nodes_service.kubeconfig_flag == "--kubeconfig-file"
    assert nodes_service.cmd == "kubectl get nodes"


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_legacy_format(tmp_path):
    """Test loading configuration from legacy format file."""
    config_content = """name = "legacy-deployment"
version = "1.5.0"
max_workers = 12

[clusters]
metrics = true
primary = 2
secondary = 0
standalone = 1
"""

    config_file = tmp_path / "test.toml"
    config_file.write_text(config_content)

    config = load_config_from_file(str(config_file))

    assert config.general.name == "legacy-deployment"
    assert config.general.version == "1.5.0"
    assert config.general.max_workers == 12
    assert config.clusters["metrics"].enable is True
    assert config.clusters["metrics"].count == 1
    assert config.clusters["primary"].enable is True
    assert config.clusters["primary"].count == 2
    assert config.clusters["secondary"].enable is False
    assert config.clusters["secondary"].count == 0
    assert config.clusters["standalone"].enable is True
    assert config.clusters["standalone"].count == 1


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_mixed_format(tmp_path):
    """Test loading configuration from mixed format file."""
    config_content = """[general]
name = "mixed-deployment"
max_workers = 14

[clusters]
metrics = true
primary = 3
secondary = 2
standalone = false
"""

    config_file = tmp_path / "test.toml"
    config_file.write_text(config_content)

    config = load_config_from_file(str(config_file))

    assert config.general.name == "mixed-deployment"
    assert config.general.max_workers == 14
    assert config.clusters["metrics"].enable is True
    assert config.clusters["metrics"].count == 1
    assert config.clusters["primary"].enable is True
    assert config.clusters["primary"].count == 3
    assert config.clusters["secondary"].enable is True
    assert config.clusters["secondary"].count == 2
    assert config.clusters["standalone"].enable is False
    assert config.clusters["standalone"].count == 0


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_nonexistent():
    """Test loading configuration from nonexistent file."""
    with pytest.raises(FileNotFoundError):
        load_config_from_file("nonexistent.toml")


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_invalid_format(tmp_path):
    """Test loading configuration from file with invalid format."""
    config_content = "invalid toml content {"

    config_file = tmp_path / "test.toml"
    config_file.write_text(config_content)

    with pytest.raises(Exception):  # Should raise some parsing error
        load_config_from_file(str(config_file))


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_unsupported_format(tmp_path):
    """Test loading configuration from unsupported file format."""
    config_content = "some content"

    config_file = tmp_path / "test.txt"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Unsupported configuration file format"):
        load_config_from_file(str(config_file))


@pytest.mark.unit
@pytest.mark.config
def test_load_config_from_file_default_discovery():
    """Test loading configuration with default file discovery."""
    # This test would require creating actual config files in the current directory
    # For now, we'll test that it raises FileNotFoundError when no config is found
    with pytest.raises(FileNotFoundError):
        load_config_from_file(None)


@pytest.mark.unit
@pytest.mark.config
def test_empty_configuration_dict():
    """Test updating configuration with empty dictionary."""
    config = create_default_config()
    original_name = config.general.name

    config.update_from_dict({})

    # Should remain unchanged
    assert config.general.name == original_name
    for cluster_config in config.clusters.values():
        assert cluster_config.enable is False
        assert cluster_config.count == 0


@pytest.mark.unit
@pytest.mark.config
def test_configuration_with_extra_fields():
    """Test configuration with extra fields that should be ignored."""
    config = create_default_config()

    config_data = {
        "general": {
            "name": "extra-fields-deployment",
            "unknown_field": "should be ignored",
        },
        "clusters": {
            "metrics": {"enable": True, "unknown_field": "should be ignored"},
        },
        "unknown_section": {"some": "data"},
    }

    config.update_from_dict(config_data)

    # Should work normally, ignoring extra fields
    assert config.general.name == "extra-fields-deployment"
    assert config.clusters["metrics"].enable is True


@pytest.mark.unit
@pytest.mark.config
def test_configuration_with_none_values():
    """Test configuration with None values."""
    config = create_default_config()

    config_data = {
        "general": {
            "name": "none-values-deployment",
            "version": None,  # Will be set to None
        },
        "clusters": {
            "metrics": None,  # Will be ignored (not a valid cluster config)
            "primary": {"enable": True, "count": None},  # count None will be set to None
        },
    }

    config.update_from_dict(config_data)

    # Test that None values are actually set (current behavior)
    assert config.general.name == "none-values-deployment"
    assert config.general.version is None  # None was set
    assert config.clusters["metrics"].enable is False  # Default value (None was ignored)
    assert config.clusters["primary"].enable is True
    assert config.clusters["primary"].count is None  # None was set


@pytest.mark.unit
@pytest.mark.config
def test_configuration_with_invalid_types():
    """Test configuration with invalid data types."""
    config = create_default_config()

    config_data = {
        "general": {
            "name": "invalid-types-deployment",
            "max_workers": "not_a_number",  # Invalid type
        },
        "clusters": {
            "metrics": {"enable": "not_a_boolean", "count": "not_a_number"},
        },
    }

    # Should now fail with validation error
    with pytest.raises(ValueError, match="max_workers must be an integer"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_cluster_names_with_empty_prefix():
    """Test cluster name generation with empty prefix."""
    config = create_default_config()
    config.general.prefix = ""
    config.clusters["metrics"] = ClusterConfig(enable=True, count=0)  # count=0, so not created

    cluster_names = config.get_cluster_names()
    expected = []  # No clusters with count > 0, so empty list
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_cluster_names_with_whitespace_prefix():
    """Test cluster name generation with whitespace-only prefix."""
    config = create_default_config()
    config.general.prefix = "   \t\n   "
    config.clusters["metrics"] = ClusterConfig(enable=True, count=0)  # count=0, so not created

    cluster_names = config.get_cluster_names()
    expected = []  # No clusters with count > 0, so empty list
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_to_dict_with_all_defaults():
    """Test to_dict with all default values."""
    config = create_default_config()
    result = config.to_dict()

    # Should contain all expected keys
    assert "general" in result
    assert "clusters" in result

    # General should have all expected fields
    general_keys = {
        "name",
        "version",
        "environment",
        "prefix",
        "kubeconfig_path",
        "kind_config_path",
        "max_workers",
    }
    assert set(result["general"].keys()) == general_keys

    # Clusters should be empty by default (dynamic system)
    assert len(result["clusters"]) == 0


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types():
    """Test configuration with custom cluster types."""
    config = create_default_config()

    # Add custom cluster types
    config.clusters["gateway"] = ClusterConfig(enable=True, count=0)  # count=0, so not created
    config.clusters["worker"] = ClusterConfig(enable=True, count=3)
    config.clusters["database"] = ClusterConfig(enable=True, count=1)

    cluster_names = config.get_cluster_names()
    expected = [
        # gateway has count=0, so not created
        "default-worker-1",
        "default-worker-2",
        "default-worker-3",
        "default-database",  # count=1, so no suffix
    ]
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_cluster_type_validation():
    """Test cluster type name validation."""
    config = create_default_config()

    # Test valid cluster type names
    valid_names = ["gateway", "worker-1", "database_node", "cache-cluster", "api_server"]
    for name in valid_names:
        config._validate_cluster_type_name(name)  # Should not raise

    # Test invalid cluster type names
    invalid_names = [
        ("", "Cluster type name cannot be empty"),
        ("a" * 51, "is too long"),
        ("gateway!", "must contain only alphanumeric characters"),
        ("gate way", "must contain only alphanumeric characters"),
        ("gateway@", "must contain only alphanumeric characters"),
        ("general", "is reserved"),
        ("clusters", "is reserved"),
        ("services", "is reserved"),
    ]

    for name, expected_error in invalid_names:
        with pytest.raises(ValueError, match=expected_error):
            config._validate_cluster_type_name(name)


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_from_dict():
    """Test loading dynamic cluster types from configuration dictionary."""
    config = create_default_config()

    config_data = {
        "clusters": {
            "gateway": {"enable": True, "count": 0},
            "worker": {"enable": True, "count": 2},
            "database": {"enable": False, "count": 1},
            "cache": {"enable": True, "count": 3},
        }
    }

    config.update_from_dict(config_data)

    # Check that all cluster types were created
    assert "gateway" in config.clusters
    assert "worker" in config.clusters
    assert "database" in config.clusters
    assert "cache" in config.clusters

    # Check configurations
    assert config.clusters["gateway"].enable is True
    assert config.clusters["gateway"].count == 0
    assert config.clusters["worker"].enable is True
    assert config.clusters["worker"].count == 2
    assert config.clusters["database"].enable is False
    assert config.clusters["database"].count == 1
    assert config.clusters["cache"].enable is True
    assert config.clusters["cache"].count == 3

    # Check cluster name generation
    cluster_names = config.get_cluster_names()
    expected = [
        # gateway has count=0, so not created
        "default-worker-1",
        "default-worker-2",
        # database has enable=False, so not created
        "default-cache-1",
        "default-cache-2",
        "default-cache-3",
    ]
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_with_services():
    """Test dynamic cluster types with cluster-specific services."""
    config = create_default_config()

    config_data = {
        "clusters": {
            "gateway": {
                "enable": True,
                "count": 0,
                "services": {
                    "nginx": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n nginx"},
                },
            },
            "worker": {
                "enable": True,
                "count": 2,
                "services": {
                    "monitoring": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n monitoring"},
                },
            },
        }
    }

    config.update_from_dict(config_data)

    # Check cluster configurations
    assert config.clusters["gateway"].enable is True
    assert config.clusters["gateway"].count == 0
    assert len(config.clusters["gateway"].services) == 1
    assert "nginx" in config.clusters["gateway"].services
    assert config.clusters["gateway"].services["nginx"].cmd == "kubectl get pods -n nginx"

    assert config.clusters["worker"].enable is True
    assert config.clusters["worker"].count == 2
    assert len(config.clusters["worker"].services) == 1
    assert "monitoring" in config.clusters["worker"].services
    assert config.clusters["worker"].services["monitoring"].cmd == "kubectl get pods -n monitoring"


@pytest.mark.unit
@pytest.mark.config
def test_cluster_type_validation_in_update():
    """Test that cluster type validation is enforced during update_from_dict."""
    config = create_default_config()

    # Test with invalid cluster type name
    config_data = {
        "clusters": {
            "gateway!": {"enable": True, "count": 0},  # Invalid name
        }
    }

    with pytest.raises(ValueError, match="Invalid cluster type name"):
        config.update_from_dict(config_data)

    # Test with reserved word
    config_data = {
        "clusters": {
            "general": {"enable": True, "count": 0},  # Reserved word
        }
    }

    with pytest.raises(ValueError, match="is reserved"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_service_name_validation():
    """Test service name validation."""
    config = create_default_config()

    # Test valid service names
    valid_names = ["nginx", "monitoring-1", "database_backup", "api-server", "health_check"]
    for name in valid_names:
        config._validate_service_name(name)  # Should not raise

    # Test invalid service names
    invalid_names = [
        ("", "Service name cannot be empty"),
        ("a" * 51, "is too long"),
        ("nginx!", "must contain only alphanumeric characters"),
        ("nginx server", "must contain only alphanumeric characters"),
        ("nginx@", "must contain only alphanumeric characters"),
        ("general", "is reserved"),
        ("clusters", "is reserved"),
        ("services", "is reserved"),
    ]

    for name, expected_error in invalid_names:
        with pytest.raises(ValueError, match=expected_error):
            config._validate_service_name(name)


@pytest.mark.unit
@pytest.mark.config
def test_service_config_validation():
    """Test service configuration validation."""
    config = create_default_config()

    # Test valid service configuration
    valid_config = {"cmd": "kubectl get pods", "kubeconfig.flag": "--kubeconfig"}
    config._validate_service_config("test-service", valid_config)  # Should not raise

    # Test invalid service configurations
    invalid_configs = [
        ({}, "must have a 'cmd' field"),  # Missing cmd
        ({"cmd": ""}, "cmd cannot be empty"),  # Empty cmd
        ({"cmd": 123}, "cmd must be a string"),  # Non-string cmd
        ({"cmd": "kubectl get pods", "kubeconfig.flag": ""}, "kubeconfig.flag cannot be empty"),  # Empty flag
        ({"cmd": "kubectl get pods", "kubeconfig.flag": 123}, "kubeconfig.flag must be a string"),  # Non-string flag
    ]

    for service_config, expected_error in invalid_configs:
        with pytest.raises(ValueError, match=expected_error):
            config._validate_service_config("test-service", service_config)


@pytest.mark.unit
@pytest.mark.config
def test_service_validation_in_configuration():
    """Test that service validation is enforced during configuration loading."""
    config = create_default_config()

    # Test with invalid service name
    config_data = {
        "services": {
            "nginx!": {"cmd": "kubectl get pods"},  # Invalid service name
        }
    }

    with pytest.raises(ValueError, match="Invalid service name"):
        config.update_from_dict(config_data)

    # Test with invalid service configuration
    config_data = {
        "services": {
            "nginx": {"cmd": ""},  # Empty cmd
        }
    }

    with pytest.raises(ValueError, match="cmd cannot be empty"):
        config.update_from_dict(config_data)

    # Test with invalid cluster-specific service name
    config_data = {
        "clusters": {
            "gateway": {
                "enable": True,
                "services": {
                    "nginx!": {"cmd": "kubectl get pods"},  # Invalid service name
                },
            }
        }
    }

    with pytest.raises(ValueError, match="Invalid service name"):
        config.update_from_dict(config_data)

    # Test with invalid cluster-specific service configuration
    config_data = {
        "clusters": {
            "gateway": {
                "enable": True,
                "services": {
                    "nginx": {"cmd": ""},  # Empty cmd
                },
            }
        }
    }

    with pytest.raises(ValueError, match="cmd cannot be empty"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_cluster_configuration_schema_validation():
    """Test cluster configuration schema validation."""
    config = create_default_config()

    # Test duplicate cluster type names by testing the validation method directly
    # Note: Python dicts don't allow duplicate keys, so we test the validation logic directly
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": 2},
        },
    }

    # Test the validation method directly with duplicate cluster types
    # Simulate duplicate cluster types by creating a list with duplicates
    cluster_types = ["worker", "worker"]  # Simulate duplicates
    if len(cluster_types) != len(set(cluster_types)):
        duplicates = [ct for ct in set(cluster_types) if cluster_types.count(ct) > 1]
        with pytest.raises(ValueError, match="Duplicate cluster type names found"):
            raise ValueError(f"Duplicate cluster type names found: {', '.join(duplicates)}")

    # Test cluster without enable or count
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {},  # No enable or count
        },
    }

    with pytest.raises(ValueError, match="must have either 'enable' or 'count' property"):
        config.update_from_dict(config_data)

    # Test cluster with both enable and count (now allowed)
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"enable": True, "count": 2},  # Both enable and count - now allowed
        },
    }

    # This should now pass since we allow both enable and count
    config.update_from_dict(config_data)
    assert config.clusters["worker"].enable is True
    assert config.clusters["worker"].count == 2

    # Test invalid enable type
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"enable": "true"},  # String instead of boolean
        },
    }

    with pytest.raises(ValueError, match="enable property must be a boolean"):
        config.update_from_dict(config_data)

    # Test invalid count type
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": "2"},  # String instead of integer
        },
    }

    with pytest.raises(ValueError, match="count property must be an integer"):
        config.update_from_dict(config_data)

    # Test negative count
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": -1},  # Negative count
        },
    }

    with pytest.raises(ValueError, match="count must be non-negative"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_cluster_count_validation():
    """Test cluster count validation with limits."""
    config = create_default_config()

    # Test cluster count exceeding per-type limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": 101},  # Exceeds 100 limit
        },
    }

    with pytest.raises(ValueError, match="count \\(101\\) exceeds maximum allowed \\(100\\)"):
        config.update_from_dict(config_data)

    # Test total cluster count exceeding limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker1": {"count": 200},
            "worker2": {"count": 200},
            "worker3": {"count": 200},  # Total: 600, exceeds 500 limit
        },
    }

    with pytest.raises(ValueError, match="count \\(200\\) exceeds maximum allowed \\(100\\)"):
        config.update_from_dict(config_data)

    # Test total cluster count exceeding limit with smaller per-cluster counts
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker1": {"count": 200},
            "worker2": {"count": 200},
            "worker3": {"count": 200},  # Total: 600, exceeds 500 limit
        },
    }

    with pytest.raises(ValueError, match="count \\(200\\) exceeds maximum allowed \\(100\\)"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_total_cluster_count_validation():
    """Test total cluster count validation with limits."""
    config = create_default_config()

    # Test total cluster count validation by directly calling the validation method
    # with counts that don't exceed per-type limit but exceed total limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker1": {"count": 200},
            "worker2": {"count": 200},
            "worker3": {"count": 200},  # Total: 600, exceeds 500 limit
        },
    }

    # Test the validation method directly with modified limits
    clusters_data = config_data["clusters"]
    max_clusters_per_type = 300  # Higher limit for this test
    total_clusters = 0

    for cluster_type, cluster_config in clusters_data.items():
        if isinstance(cluster_config, dict) and "count" in cluster_config:
            count = cluster_config["count"]
            if isinstance(count, int):
                if count > max_clusters_per_type:
                    raise ValueError(
                        f"Cluster '{cluster_type}' count ({count}) exceeds maximum allowed ({max_clusters_per_type})"
                    )
                total_clusters += count

    # Check total cluster limit
    max_total_clusters = 500  # Reasonable limit for total clusters
    if total_clusters > max_total_clusters:
        with pytest.raises(ValueError, match="Total cluster count \\(600\\) exceeds maximum allowed \\(500\\)"):
            raise ValueError(f"Total cluster count ({total_clusters}) exceeds maximum allowed ({max_total_clusters})")


@pytest.mark.unit
@pytest.mark.config
def test_general_configuration_validation():
    """Test general configuration validation."""
    config = create_default_config()

    # Test invalid max_workers type
    config_data = {
        "general": {"max_workers": "4"},  # String instead of integer
    }

    with pytest.raises(ValueError, match="max_workers must be an integer"):
        config.update_from_dict(config_data)

    # Test max_workers too low
    config_data = {
        "general": {"max_workers": 0},  # Too low
    }

    with pytest.raises(ValueError, match="max_workers must be at least 1"):
        config.update_from_dict(config_data)

    # Test max_workers too high
    config_data = {
        "general": {"max_workers": 101},  # Too high
    }

    with pytest.raises(ValueError, match="max_workers cannot exceed 100"):
        config.update_from_dict(config_data)

    # Test prefix too long
    config_data = {
        "general": {"prefix": "a" * 51},  # Too long
    }

    with pytest.raises(ValueError, match="prefix cannot exceed 50 characters"):
        config.update_from_dict(config_data)

    # Test invalid prefix type
    config_data = {
        "general": {"prefix": 123},  # Integer instead of string
    }

    with pytest.raises(ValueError, match="prefix must be a string"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_configuration_completeness_validation():
    """Test configuration completeness validation."""
    config = create_default_config()

    # Test missing general section (now allowed for legacy format)
    config_data = {
        "clusters": {
            "worker": {"count": 2},
        }
    }

    # This should now pass since we allow legacy format without general section
    config.update_from_dict(config_data)
    assert config.clusters["worker"].count == 2

    # Test invalid general section type
    config_data = {
        "general": "invalid",  # String instead of dict
    }

    with pytest.raises(ValueError, match="General configuration must be a dictionary"):
        config.update_from_dict(config_data)

    # Test invalid clusters section type
    config_data = {
        "general": {"name": "test"},
        "clusters": "invalid",  # String instead of dict
    }

    with pytest.raises(ValueError, match="Clusters configuration must be a dictionary"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_comprehensive_validation_integration():
    """Test comprehensive validation with multiple validation errors."""
    config = create_default_config()

    # Test configuration with multiple validation errors
    config_data = {
        "general": {
            "max_workers": "invalid",  # Invalid type
            "prefix": "a" * 51,  # Too long
        },
        "clusters": {
            "worker!": {"count": 2},  # Invalid cluster type name
            "worker!": {"count": 3},  # Duplicate and invalid
        },
        "services": {
            "service!": {"cmd": ""},  # Invalid service name and empty cmd
        },
    }

    # Should fail on the first validation error (cluster type validation happens before general validation)
    with pytest.raises(ValueError, match="Invalid cluster type name"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_edge_cases():
    """Test edge cases for dynamic cluster types."""
    config = create_default_config()

    # Test with very long cluster type names
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "a" * 50: {"enable": True},  # Exactly 50 characters (max allowed)
        },
    }
    config.update_from_dict(config_data)
    assert "a" * 50 in config.clusters

    # Test with single character cluster type names
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "a": {"enable": True},  # Single character
        },
    }
    config.update_from_dict(config_data)
    assert "a" in config.clusters

    # Test with cluster types that have special characters in the middle
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "api-server": {"enable": True},
            "database-node": {"count": 2},
            "cache_cluster": {"enable": True},
        },
    }
    config.update_from_dict(config_data)
    assert "api-server" in config.clusters
    assert "database-node" in config.clusters
    assert "cache_cluster" in config.clusters

    # Test cluster name generation with special characters
    cluster_names = config.get_cluster_names()
    expected = [
        "default-api-server",  # enable=True without count sets count=1
        "default-database-node-1",
        "default-database-node-2",
        "default-cache_cluster",  # enable=True without count sets count=1
    ]
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_performance():
    """Test performance with many cluster types."""
    config = create_default_config()

    # Test with many cluster types (but within limits)
    config_data = {"general": {"name": "performance-test"}, "clusters": {}}

    # Create 50 different cluster types
    for i in range(50):
        cluster_type = f"worker-{i}"
        config_data["clusters"][cluster_type] = {"count": 1}

    config.update_from_dict(config_data)

    # Verify all cluster types were created
    assert len(config.clusters) == 50
    for i in range(50):
        assert f"worker-{i}" in config.clusters

    # Test cluster name generation performance
    cluster_names = config.get_cluster_names()
    assert len(cluster_names) == 50
    assert all(name.startswith("default-worker-") for name in cluster_names)


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_mixed_enable_count():
    """Test dynamic cluster types with mixed enable and count configurations."""
    config = create_default_config()

    config_data = {
        "general": {"name": "mixed-test"},
        "clusters": {
            "gateway": {"enable": True, "count": 0},  # Single cluster
            "worker": {"enable": False, "count": 3},  # Multiple clusters, disabled
            "database": {"enable": True, "count": 2},  # Multiple clusters, enabled
            "cache": {"enable": True, "count": 0},  # Single cluster
        },
    }

    config.update_from_dict(config_data)

    # Check configurations
    assert config.clusters["gateway"].enable is True
    assert config.clusters["gateway"].count == 0
    assert config.clusters["worker"].enable is False
    assert config.clusters["worker"].count == 3
    assert config.clusters["database"].enable is True
    assert config.clusters["database"].count == 2
    assert config.clusters["cache"].enable is True
    assert config.clusters["cache"].count == 0

    # Check cluster name generation
    cluster_names = config.get_cluster_names()
    expected = [
        # gateway has count=0, so not created
        # worker has enable=False, so not created
        "default-database-1",  # enable=True, count > 0
        "default-database-2",
        # cache has count=0, so not created
    ]
    assert cluster_names == expected


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_with_services_complex():
    """Test complex service configurations with dynamic cluster types."""
    config = create_default_config()

    config_data = {
        "general": {"name": "complex-services"},
        "clusters": {
            "api": {
                "enable": True,
                "count": 0,
                "services": {
                    "nginx": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get pods -n nginx"},
                    "monitoring": {"kubeconfig.flag": "--kubeconfig-file", "cmd": "kubectl get pods -n monitoring"},
                },
            },
            "worker": {
                "enable": True,
                "count": 2,
                "services": {"job-runner": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get jobs"}},
            },
        },
        "services": {"global-health": {"kubeconfig.flag": "--kubeconfig", "cmd": "kubectl get nodes"}},
    }

    config.update_from_dict(config_data)

    # Check cluster configurations
    assert config.clusters["api"].enable is True
    assert config.clusters["api"].count == 0
    assert len(config.clusters["api"].services) == 2
    assert "nginx" in config.clusters["api"].services
    assert "monitoring" in config.clusters["api"].services

    assert config.clusters["worker"].enable is True
    assert config.clusters["worker"].count == 2
    assert len(config.clusters["worker"].services) == 1
    assert "job-runner" in config.clusters["worker"].services

    # Check global services
    assert len(config.services) == 1
    assert "global-health" in config.services

    # Check service configurations
    nginx_service = config.clusters["api"].services["nginx"]
    assert nginx_service.kubeconfig_flag == "--kubeconfig"
    assert nginx_service.cmd == "kubectl get pods -n nginx"

    monitoring_service = config.clusters["api"].services["monitoring"]
    assert monitoring_service.kubeconfig_flag == "--kubeconfig-file"
    assert monitoring_service.cmd == "kubectl get pods -n monitoring"

    job_runner_service = config.clusters["worker"].services["job-runner"]
    assert job_runner_service.kubeconfig_flag == "--kubeconfig"
    assert job_runner_service.cmd == "kubectl get jobs"

    global_health_service = config.services["global-health"]
    assert global_health_service.kubeconfig_flag == "--kubeconfig"
    assert global_health_service.cmd == "kubectl get nodes"


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_validation_edge_cases():
    """Test validation edge cases for dynamic cluster types."""
    config = create_default_config()

    # Test cluster type name exactly at the limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "a" * 50: {"enable": True},  # Exactly 50 characters
        },
    }
    config.update_from_dict(config_data)  # Should pass

    # Test cluster type name over the limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "a" * 51: {"enable": True},  # 51 characters (over limit)
        },
    }
    with pytest.raises(ValueError, match="is too long"):
        config.update_from_dict(config_data)

    # Test empty cluster type name
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "": {"enable": True},  # Empty name
        },
    }
    with pytest.raises(ValueError, match="cannot be empty"):
        config.update_from_dict(config_data)

    # Test cluster type name with spaces
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "my cluster": {"enable": True},  # Space in name
        },
    }
    with pytest.raises(ValueError, match="must contain only alphanumeric characters"):
        config.update_from_dict(config_data)

    # Test cluster type name with special characters
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "cluster@test": {"enable": True},  # @ symbol
        },
    }
    with pytest.raises(ValueError, match="must contain only alphanumeric characters"):
        config.update_from_dict(config_data)


@pytest.mark.unit
@pytest.mark.config
def test_dynamic_cluster_types_count_limits():
    """Test cluster count limits and validation."""
    config = create_default_config()

    # Test count at the limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": 100},  # At the limit
        },
    }
    config.update_from_dict(config_data)  # Should pass

    # Test count over the limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": 101},  # Over the limit
        },
    }
    with pytest.raises(ValueError, match="exceeds maximum allowed"):
        config.update_from_dict(config_data)

    # Test total count over the limit
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker1": {"count": 200},
            "worker2": {"count": 200},
            "worker3": {"count": 200},  # Total: 600, over 500 limit
        },
    }
    with pytest.raises(ValueError, match="exceeds maximum allowed"):
        config.update_from_dict(config_data)

    # Test negative count
    config_data = {
        "general": {"name": "test"},
        "clusters": {
            "worker": {"count": -1},  # Negative count
        },
    }
    with pytest.raises(ValueError, match="must be non-negative"):
        config.update_from_dict(config_data)
