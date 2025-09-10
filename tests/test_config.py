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


class TestClusterConfig:
    """Test ClusterConfig dataclass."""

    def test_default_values(self):
        """Test that ClusterConfig has correct default values."""
        cluster = ClusterConfig()
        assert cluster.enable is False
        assert cluster.count == 0

    def test_custom_values(self):
        """Test ClusterConfig with custom values."""
        cluster = ClusterConfig(enable=True, count=3)
        assert cluster.enable is True
        assert cluster.count == 3

    def test_services_field(self):
        """Test that ClusterConfig has services field."""
        cluster = ClusterConfig()
        assert isinstance(cluster.services, dict)
        assert len(cluster.services) == 0

    def test_services_with_custom_values(self):
        """Test that ClusterConfig can have services."""
        service = ServiceConfig(kubeconfig_flag="--kubeconfig", cmd="kubectl get pods")
        cluster = ClusterConfig(enable=True, count=2, services={"pods": service})
        assert cluster.enable is True
        assert cluster.count == 2
        assert "pods" in cluster.services
        assert cluster.services["pods"].cmd == "kubectl get pods"


class TestGeneralConfig:
    """Test GeneralConfig dataclass."""

    def test_default_values(self):
        """Test that GeneralConfig has correct default values."""
        general = GeneralConfig()
        assert general.name == "default-deployment"
        assert general.version == "1.0.0"
        assert general.environment == "development"
        assert general.prefix == "default"
        assert general.kubeconfig_path == "kubeconfigs"
        assert general.kind_config_path == "kind-configs"
        assert general.max_workers == 4

    def test_custom_values(self):
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


class TestServiceConfig:
    """Test ServiceConfig dataclass."""

    def test_default_values(self):
        """Test that ServiceConfig has correct default values."""
        config = ServiceConfig()
        assert config.kubeconfig_flag == "--kubeconfig"
        assert config.cmd == ""

    def test_custom_values(self):
        """Test that ServiceConfig accepts custom values."""
        config = ServiceConfig(kubeconfig_flag="--kubeconfig-file", cmd="kubectl get pods -n kube-system")
        assert config.kubeconfig_flag == "--kubeconfig-file"
        assert config.cmd == "kubectl get pods -n kube-system"


class TestDeploymentConfig:
    """Test DeploymentConfig dataclass."""

    def test_default_configuration(self):
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

        # Test cluster configuration
        assert len(config.clusters) == 4
        assert "metrics" in config.clusters
        assert "primary" in config.clusters
        assert "secondary" in config.clusters
        assert "standalone" in config.clusters

        for cluster_type, cluster_config in config.clusters.items():
            assert isinstance(cluster_config, ClusterConfig)
            assert cluster_config.enable is False
            assert cluster_config.count == 0

        # Test services configuration
        assert isinstance(config.services, dict)
        assert len(config.services) == 0  # No services by default

    def test_update_from_dict_with_services(self):
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

    def test_update_from_dict_with_cluster_specific_services(self):
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

    def test_update_from_dict_new_format(self):
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

    def test_update_from_dict_legacy_format(self):
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

    def test_update_from_dict_mixed_format(self):
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
        # Note: The current implementation treats mixed format as legacy format
        # because not all cluster values are dictionaries
        # In legacy format, dict values are treated as invalid and ignored
        assert config.clusters["metrics"].enable is False  # Dict ignored in legacy format
        assert config.clusters["metrics"].count == 0  # Dict ignored in legacy format
        assert config.clusters["primary"].enable is True
        assert config.clusters["primary"].count == 3
        assert config.clusters["secondary"].enable is False  # Dict ignored in legacy format
        assert config.clusters["secondary"].count == 0  # Dict ignored in legacy format
        assert config.clusters["standalone"].enable is False
        assert config.clusters["standalone"].count == 0  # Boolean False becomes count 0

    def test_update_from_dict_partial_override(self):
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

    def test_update_from_dict_no_general_section(self):
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

    def test_get_cluster_names(self):
        """Test cluster name generation."""
        config = create_default_config()

        # Test with default configuration (no clusters)
        cluster_names = config.get_cluster_names()
        assert cluster_names == ["default-default"]  # Default fallback

        # Test with custom prefix
        config.general.prefix = "test-project"
        cluster_names = config.get_cluster_names()
        assert cluster_names == ["test-project-default"]  # Default fallback with custom prefix

        # Test with enabled clusters
        config.clusters["metrics"].enable = True
        config.clusters["primary"].count = 2
        config.clusters["secondary"].count = 1
        config.clusters["standalone"].count = 3

        cluster_names = config.get_cluster_names()
        expected = [
            "test-project-metrics",
            "test-project-primary-1",
            "test-project-primary-2",
            "test-project-secondary-1",
            "test-project-standalone-1",
            "test-project-standalone-2",
            "test-project-standalone-3",
        ]
        assert cluster_names == expected

    def test_get_cluster_names_with_special_characters(self):
        """Test cluster name generation with special characters in prefix."""
        config = create_default_config()
        config.general.prefix = "Test_Project@2024!"
        config.clusters["metrics"].enable = True
        config.clusters["primary"].count = 1

        cluster_names = config.get_cluster_names()
        expected = ["test-project-2024-metrics", "test-project-2024-primary-1"]
        assert cluster_names == expected

    def test_to_dict(self):
        """Test configuration to dictionary conversion."""
        config = create_default_config()
        config.general.name = "test-deployment"
        config.general.max_workers = 8
        config.clusters["metrics"].enable = True
        config.clusters["primary"].count = 2

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
        assert result["clusters"]["primary"]["enable"] is False
        assert result["clusters"]["primary"]["count"] == 2

        # Test services section
        assert "services" in result
        assert "pods" in result["services"]
        assert "nodes" in result["services"]
        assert result["services"]["pods"]["kubeconfig.flag"] == "--kubeconfig"
        assert result["services"]["pods"]["cmd"] == "kubectl get pods -n kube-system"
        assert result["services"]["nodes"]["kubeconfig.flag"] == "--kubeconfig-file"
        assert result["services"]["nodes"]["cmd"] == "kubectl get nodes"


class TestConfigurationFileLoading:
    """Test configuration loading from files."""

    def test_load_config_from_file_toml(self):
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            config = load_config_from_file(temp_file)

            assert config.general.name == "toml-deployment"
            assert config.general.version == "2.0.0"
            assert config.general.max_workers == 6
            assert config.clusters["metrics"].enable is True
            assert config.clusters["primary"].count == 2

        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_json(self):
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_content, f)
            temp_file = f.name

        try:
            config = load_config_from_file(temp_file)

            assert config.general.name == "json-deployment"
            assert config.general.version == "3.0.0"
            assert config.general.max_workers == 8
            assert config.clusters["metrics"].enable is True
            assert config.clusters["primary"].count == 3

        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_yaml(self):
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            config = load_config_from_file(temp_file)

            assert config.general.name == "yaml-deployment"
            assert config.general.version == "4.0.0"
            assert config.general.max_workers == 10
            assert config.clusters["metrics"].enable is True
            assert config.clusters["primary"].count == 4

        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_with_services(self):
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            config = load_config_from_file(temp_file)

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

        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_legacy_format(self):
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            config = load_config_from_file(temp_file)

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

        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_mixed_format(self):
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            config = load_config_from_file(temp_file)

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

        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_nonexistent(self):
        """Test loading configuration from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("nonexistent.toml")

    def test_load_config_from_file_invalid_format(self):
        """Test loading configuration from file with invalid format."""
        config_content = "invalid toml content {"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            with pytest.raises(Exception):  # Should raise some parsing error
                load_config_from_file(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_unsupported_format(self):
        """Test loading configuration from unsupported file format."""
        config_content = "some content"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported configuration file format"):
                load_config_from_file(temp_file)
        finally:
            Path(temp_file).unlink()

    def test_load_config_from_file_default_discovery(self):
        """Test loading configuration with default file discovery."""
        # This test would require creating actual config files in the current directory
        # For now, we'll test that it raises FileNotFoundError when no config is found
        with pytest.raises(FileNotFoundError):
            load_config_from_file(None)


class TestConfigurationEdgeCases:
    """Test edge cases and error handling in configuration."""

    def test_empty_configuration_dict(self):
        """Test updating configuration with empty dictionary."""
        config = create_default_config()
        original_name = config.general.name

        config.update_from_dict({})

        # Should remain unchanged
        assert config.general.name == original_name
        for cluster_config in config.clusters.values():
            assert cluster_config.enable is False
            assert cluster_config.count == 0

    def test_configuration_with_extra_fields(self):
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

    def test_configuration_with_none_values(self):
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

    def test_configuration_with_invalid_types(self):
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

        # Should not crash, but may not work as expected
        # The exact behavior depends on how Python handles type coercion
        config.update_from_dict(config_data)

        assert config.general.name == "invalid-types-deployment"
        # max_workers might be coerced to int or remain as string depending on implementation

    def test_cluster_names_with_empty_prefix(self):
        """Test cluster name generation with empty prefix."""
        config = create_default_config()
        config.general.prefix = ""
        config.clusters["metrics"].enable = True

        cluster_names = config.get_cluster_names()
        expected = ["default-metrics"]  # Should fall back to "default"
        assert cluster_names == expected

    def test_cluster_names_with_whitespace_prefix(self):
        """Test cluster name generation with whitespace-only prefix."""
        config = create_default_config()
        config.general.prefix = "   \t\n   "
        config.clusters["metrics"].enable = True

        cluster_names = config.get_cluster_names()
        expected = ["default-metrics"]  # Should fall back to "default"
        assert cluster_names == expected

    def test_to_dict_with_all_defaults(self):
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

        # Clusters should have all expected cluster types
        cluster_keys = {"metrics", "primary", "secondary", "standalone"}
        assert set(result["clusters"].keys()) == cluster_keys

        # Each cluster should have enable and count
        for cluster_config in result["clusters"].values():
            assert "enable" in cluster_config
            assert "count" in cluster_config
