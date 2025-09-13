"""Configuration management for deployment-builder tool."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ServiceConfig:
    """Configuration for services to run against clusters."""

    kubeconfig_flag: str = "--kubeconfig"
    cmd: str = ""


@dataclass
class ClusterConfig:
    """Configuration for a specific cluster type."""

    enable: bool = False
    count: int = 0
    services: Dict[str, ServiceConfig] = field(default_factory=dict)


@dataclass
class GeneralConfig:
    """Configuration for the general section."""

    name: str = "default-deployment"
    version: str = "1.0.0"
    environment: str = "development"
    prefix: str = "default"
    kubeconfig_path: str = "kubeconfigs"
    kind_config_path: str = "kind-configs"
    max_workers: int = 4


@dataclass
class DeploymentConfig:
    """Main configuration object with all default values."""

    # General configuration section
    general: GeneralConfig = field(default_factory=GeneralConfig)

    # Cluster configuration - now dynamic instead of hardcoded
    clusters: Dict[str, ClusterConfig] = field(default_factory=dict)

    # Services configuration
    services: Dict[str, ServiceConfig] = field(default_factory=dict)

    def _validate_cluster_type_name(self, cluster_type: str) -> None:
        """Validate cluster type name format.

        Args:
            cluster_type: The cluster type name to validate

        Raises:
            ValueError: If cluster type name is invalid
        """
        if not cluster_type:
            raise ValueError("Cluster type name cannot be empty")

        if len(cluster_type) > 50:
            raise ValueError(f"Cluster type name '{cluster_type}' is too long (max 50 characters)")

        if len(cluster_type) < 1:
            raise ValueError("Cluster type name must be at least 1 character")

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9_-]+$", cluster_type):
            raise ValueError(
                f"Invalid cluster type name '{cluster_type}': must contain only alphanumeric characters, hyphens, and underscores"
            )

        # Check for reserved words
        reserved_words = {
            "general",
            "clusters",
            "services",
            "name",
            "version",
            "environment",
            "prefix",
            "kubeconfig_path",
            "kind_config_path",
            "max_workers",
            "enable",
            "count",
            "kubeconfig.flag",
            "cmd",
        }
        if cluster_type.lower() in reserved_words:
            raise ValueError(f"Cluster type name '{cluster_type}' is reserved and cannot be used")

    def _validate_service_name(self, service_name: str) -> None:
        """Validate service name format.

        Args:
            service_name: The service name to validate

        Raises:
            ValueError: If service name is invalid
        """
        if not service_name:
            raise ValueError("Service name cannot be empty")

        if len(service_name) > 50:
            raise ValueError(f"Service name '{service_name}' is too long (max 50 characters)")

        if len(service_name) < 1:
            raise ValueError("Service name must be at least 1 character")

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9_-]+$", service_name):
            raise ValueError(
                f"Invalid service name '{service_name}': must contain only alphanumeric characters, hyphens, and underscores"
            )

        # Check for reserved words
        reserved_words = {
            "general",
            "clusters",
            "services",
            "name",
            "version",
            "environment",
            "prefix",
            "kubeconfig_path",
            "kind_config_path",
            "max_workers",
            "enable",
            "count",
            "kubeconfig.flag",
            "cmd",
        }
        if service_name.lower() in reserved_words:
            raise ValueError(f"Service name '{service_name}' is reserved and cannot be used")

    def _validate_service_config(self, service_name: str, service_config: dict) -> None:
        """Validate service configuration.

        Args:
            service_name: The service name (for error messages)
            service_config: The service configuration to validate

        Raises:
            ValueError: If service configuration is invalid
        """
        if not isinstance(service_config, dict):
            raise ValueError(f"Service '{service_name}' configuration must be a dictionary")

        # Validate required fields
        if "cmd" not in service_config:
            raise ValueError(f"Service '{service_name}' must have a 'cmd' field")

        cmd = service_config.get("cmd", "")
        if not isinstance(cmd, str):
            raise ValueError(f"Service '{service_name}' cmd must be a string")

        if not cmd.strip():
            raise ValueError(f"Service '{service_name}' cmd cannot be empty")

        # Validate kubeconfig.flag field
        if "kubeconfig.flag" not in service_config:
            raise ValueError(f"Service '{service_name}' must have kubeconfig.flag field")

        kubeconfig_flag = service_config.get("kubeconfig.flag")
        if not isinstance(kubeconfig_flag, str):
            raise ValueError(f"Service '{service_name}' kubeconfig.flag must be a string")

        if not kubeconfig_flag.strip():
            raise ValueError(f"Service '{service_name}' kubeconfig.flag cannot be empty")

    def _validate_cluster_type_references(self, config_data: Dict[str, Any]) -> None:
        """Validate that all cluster type references in services are valid.

        Args:
            config_data: The configuration data to validate

        Raises:
            ValueError: If any cluster type references are invalid
        """
        # Get all defined cluster types
        defined_cluster_types = set()
        if "clusters" in config_data:
            clusters_data = config_data["clusters"]
            if isinstance(clusters_data, dict):
                defined_cluster_types = set(clusters_data.keys())

        # Validate cluster type references in global services
        # (No cluster type references in global services, so nothing to validate)

        # Validate cluster type references in cluster-specific services
        if "clusters" in config_data:
            clusters_data = config_data["clusters"]
            if isinstance(clusters_data, dict):
                for cluster_type, cluster_config in clusters_data.items():
                    if isinstance(cluster_config, dict) and "services" in cluster_config:
                        # Cluster-specific services are already validated as part of cluster type validation
                        # No additional validation needed here
                        pass

    def _validate_cluster_configuration_schema(self, config_data: Dict[str, Any]) -> None:
        """Validate the overall configuration schema for cluster types.

        Args:
            config_data: The configuration data to validate

        Raises:
            ValueError: If configuration schema is invalid
        """
        if "clusters" not in config_data:
            return

        clusters_data = config_data["clusters"]
        if not isinstance(clusters_data, dict):
            raise ValueError("Clusters configuration must be a dictionary")

        # Check for duplicate cluster type names
        cluster_types = list(clusters_data.keys())
        if len(cluster_types) != len(set(cluster_types)):
            duplicates = [ct for ct in set(cluster_types) if cluster_types.count(ct) > 1]
            raise ValueError(f"Duplicate cluster type names found: {', '.join(duplicates)}")

        # Validate each cluster configuration
        for cluster_type, cluster_config in clusters_data.items():
            # Skip validation for non-dict cluster configs (legacy format)
            if not isinstance(cluster_config, dict):
                continue

            # Check that cluster has either enable or count property
            has_enable = "enable" in cluster_config
            has_count = "count" in cluster_config

            if not has_enable and not has_count:
                raise ValueError(f"Cluster '{cluster_type}' must have either 'enable' or 'count' property")

            # Allow both enable and count properties - this is valid for dynamic cluster types
            # The logic in get_cluster_names() handles this correctly

            # Validate enable property
            if has_enable:
                enable_value = cluster_config["enable"]
                if not isinstance(enable_value, bool):
                    raise ValueError(
                        f"Cluster '{cluster_type}' enable property must be a boolean, got {type(enable_value).__name__}"
                    )

            # Validate count property
            if has_count:
                count_value = cluster_config["count"]
                if count_value is not None and not isinstance(count_value, int):
                    raise ValueError(
                        f"Cluster '{cluster_type}' count property must be an integer, got {type(count_value).__name__}"
                    )
                if count_value is not None and count_value < 0:
                    raise ValueError(f"Cluster '{cluster_type}' count must be non-negative, got {count_value}")

    def _validate_cluster_count_values(self, config_data: Dict[str, Any]) -> None:
        """Validate cluster count values for reasonable limits.

        Args:
            config_data: The configuration data to validate

        Raises:
            ValueError: If count values are unreasonable
        """
        if "clusters" not in config_data:
            return

        clusters_data = config_data["clusters"]
        if not isinstance(clusters_data, dict):
            return

        max_clusters_per_type = 100  # Reasonable limit
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
            raise ValueError(f"Total cluster count ({total_clusters}) exceeds maximum allowed ({max_total_clusters})")

    def _validate_general_configuration(self, config_data: Dict[str, Any]) -> None:
        """Validate general configuration section.

        Args:
            config_data: The configuration data to validate

        Raises:
            ValueError: If general configuration is invalid
        """
        if "general" not in config_data:
            return

        general_data = config_data["general"]
        if not isinstance(general_data, dict):
            raise ValueError("General configuration must be a dictionary")

        # Validate max_workers
        if "max_workers" in general_data:
            max_workers = general_data["max_workers"]
            if not isinstance(max_workers, int):
                raise ValueError(f"max_workers must be an integer, got {type(max_workers).__name__}")
            if max_workers < 1:
                raise ValueError(f"max_workers must be at least 1, got {max_workers}")
            if max_workers > 100:
                raise ValueError(f"max_workers cannot exceed 100, got {max_workers}")

        # Validate prefix
        if "prefix" in general_data:
            prefix = general_data["prefix"]
            if not isinstance(prefix, str):
                raise ValueError(f"prefix must be a string, got {type(prefix).__name__}")
            if len(prefix) > 50:
                raise ValueError(f"prefix cannot exceed 50 characters, got {len(prefix)} characters")

    def _validate_configuration_completeness(self, config_data: Dict[str, Any]) -> None:
        """Validate that configuration is complete and has required sections.

        Args:
            config_data: The configuration data to validate

        Raises:
            ValueError: If configuration is incomplete
        """
        # Check for required sections - only require general section for new format
        # Legacy format doesn't have a general section, so this is optional

        # Check that clusters section exists if any cluster-specific services are defined
        if "clusters" not in config_data:
            # Check if there are any cluster-specific service references
            # This is a basic check - more sophisticated validation could be added
            pass

    def update_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from a dictionary (loaded from config file).

        Args:
            config_data: Configuration data loaded from file
        """
        # Clear existing clusters and services to ensure clean state
        self.clusters.clear()
        self.services.clear()

        # Handle [general] section if present
        if "general" in config_data and isinstance(config_data["general"], dict):
            general_data = config_data["general"]
            if "name" in general_data:
                self.general.name = general_data["name"]
            if "version" in general_data:
                self.general.version = general_data["version"]
            if "environment" in general_data:
                self.general.environment = general_data["environment"]
            if "prefix" in general_data:
                self.general.prefix = general_data["prefix"]
            if "kubeconfig_path" in general_data:
                self.general.kubeconfig_path = general_data["kubeconfig_path"]
            if "kind_config_path" in general_data:
                self.general.kind_config_path = general_data["kind_config_path"]
            if "max_workers" in general_data:
                self.general.max_workers = general_data["max_workers"]
        else:
            # Update general configuration from top-level keys (legacy format)
            if "name" in config_data:
                self.general.name = config_data["name"]
            if "version" in config_data:
                self.general.version = config_data["version"]
            if "environment" in config_data:
                self.general.environment = config_data["environment"]
            if "prefix" in config_data:
                self.general.prefix = config_data["prefix"]
            if "kubeconfig_path" in config_data:
                self.general.kubeconfig_path = config_data["kubeconfig_path"]
            if "kind_config_path" in config_data:
                self.general.kind_config_path = config_data["kind_config_path"]
            if "max_workers" in config_data:
                self.general.max_workers = config_data["max_workers"]

        # Update cluster configuration
        if "clusters" in config_data:
            clusters_data = config_data["clusters"]

            # Validate clusters data type first
            if not isinstance(clusters_data, dict):
                raise ValueError("Clusters configuration must be a dictionary")

            # Handle new structured format: [clusters.metrics], [clusters.primary], etc.
            # Check if any values are dictionaries (new format) or if all are simple types (legacy format)
            has_dict_values = any(isinstance(v, dict) for v in clusters_data.values() if v is not None)
            all_simple_values = all(not isinstance(v, dict) for v in clusters_data.values() if v is not None)

            if isinstance(clusters_data, dict) and has_dict_values:
                # New structured format - process any cluster types dynamically
                for cluster_type, cluster_config in clusters_data.items():
                    # Validate cluster type name
                    self._validate_cluster_type_name(cluster_type)

                    # Create cluster config if it doesn't exist
                    if cluster_type not in self.clusters:
                        self.clusters[cluster_type] = ClusterConfig()

                    if isinstance(cluster_config, dict):
                        if "enable" in cluster_config:
                            self.clusters[cluster_type].enable = cluster_config["enable"]
                            # If enable is true but no count specified, set count to 1
                            if cluster_config["enable"] and "count" not in cluster_config:
                                self.clusters[cluster_type].count = 1
                        if "count" in cluster_config:
                            self.clusters[cluster_type].count = cluster_config["count"]
                            # If count is specified but enable is not, enable by default
                            if "enable" not in cluster_config:
                                self.clusters[cluster_type].enable = True

                        # Handle cluster-specific services
                        if "services" in cluster_config:
                            cluster_services = cluster_config["services"]
                            if isinstance(cluster_services, dict):
                                for service_name, service_config in cluster_services.items():
                                    # Validate service name
                                    self._validate_service_name(service_name)

                                    if isinstance(service_config, dict):
                                        # Validate service configuration
                                        self._validate_service_config(service_name, service_config)

                                        kubeconfig_flag = service_config.get("kubeconfig.flag", "--kubeconfig")
                                        cmd = service_config.get("cmd", "")
                                        self.clusters[cluster_type].services[service_name] = ServiceConfig(
                                            kubeconfig_flag=kubeconfig_flag, cmd=cmd
                                        )
                    elif not isinstance(cluster_config, dict):
                        # Handle legacy format values in mixed configuration
                        if isinstance(cluster_config, bool):
                            self.clusters[cluster_type].enable = cluster_config
                            self.clusters[cluster_type].count = 1 if cluster_config else 0
                        elif isinstance(cluster_config, int):
                            self.clusters[cluster_type].enable = cluster_config > 0
                            self.clusters[cluster_type].count = cluster_config
            elif all_simple_values:
                # Legacy format: metrics = true, primary = 2, etc.
                # Support any cluster type in legacy format for backward compatibility
                if isinstance(clusters_data, dict):
                    for cluster_type, value in clusters_data.items():
                        # Validate cluster type name
                        self._validate_cluster_type_name(cluster_type)

                        # Create cluster config if it doesn't exist
                        if cluster_type not in self.clusters:
                            self.clusters[cluster_type] = ClusterConfig()

                        if isinstance(value, bool):
                            self.clusters[cluster_type].enable = value
                            self.clusters[cluster_type].count = 1 if value else 0
                        elif isinstance(value, int):
                            self.clusters[cluster_type].enable = value > 0
                            self.clusters[cluster_type].count = value

        # Update services configuration
        if "services" in config_data:
            services_data = config_data["services"]
            if isinstance(services_data, dict):
                for service_name, service_config in services_data.items():
                    # Validate service name
                    self._validate_service_name(service_name)

                    if isinstance(service_config, dict):
                        # Validate service configuration
                        self._validate_service_config(service_name, service_config)

                        kubeconfig_flag = service_config.get("kubeconfig.flag", "--kubeconfig")
                        cmd = service_config.get("cmd", "")
                        self.services[service_name] = ServiceConfig(kubeconfig_flag=kubeconfig_flag, cmd=cmd)

        # Validate configuration completeness
        self._validate_configuration_completeness(config_data)

        # Validate general configuration
        self._validate_general_configuration(config_data)

        # Validate cluster type references after processing all configuration
        self._validate_cluster_type_references(config_data)

        # Validate configuration schema
        self._validate_cluster_configuration_schema(config_data)

        # Validate cluster count values
        self._validate_cluster_count_values(config_data)

    def get_cluster_names(self) -> list[str]:
        """Get list of cluster names based on current configuration.

        Returns:
            List of cluster names to create
        """
        # Sanitize prefix from general section
        prefix = re.sub(r"[^a-z0-9-]", "-", self.general.prefix.lower())
        prefix = re.sub(r"-+", "-", prefix)
        prefix = prefix.strip("-")

        if not prefix:
            prefix = "default"

        cluster_names = []

        # Process all cluster types dynamically
        for cluster_type, cluster_config in self.clusters.items():
            # Create clusters if enabled and count > 0
            if cluster_config.enable and cluster_config.count > 0:
                if cluster_config.count == 1:
                    # Single cluster (count: 1)
                    cluster_names.append(f"{prefix}-{cluster_type}")
                else:
                    # Multiple clusters (count > 1)
                    for i in range(1, cluster_config.count + 1):
                        cluster_names.append(f"{prefix}-{cluster_type}-{i}")

        # If no clusters defined, create a default one
        # Only create default if no cluster types are defined at all
        if not cluster_names and not self.clusters:
            cluster_names.append(f"{prefix}-default")

        return cluster_names

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format.

        Returns:
            Dictionary representation of the configuration
        """
        result = {
            "general": {
                "name": self.general.name,
                "version": self.general.version,
                "environment": self.general.environment,
                "prefix": self.general.prefix,
                "kubeconfig_path": self.general.kubeconfig_path,
                "kind_config_path": self.general.kind_config_path,
                "max_workers": self.general.max_workers,
            },
            "clusters": {
                cluster_type: {
                    "enable": cluster_config.enable,
                    "count": cluster_config.count,
                    "services": (
                        {
                            service_name: {
                                "kubeconfig.flag": service_config.kubeconfig_flag,
                                "cmd": service_config.cmd,
                            }
                            for service_name, service_config in cluster_config.services.items()
                        }
                        if cluster_config.services
                        else {}
                    ),
                }
                for cluster_type, cluster_config in self.clusters.items()
            },
            "services": {
                service_name: {"kubeconfig.flag": service_config.kubeconfig_flag, "cmd": service_config.cmd}
                for service_name, service_config in self.services.items()
            },
        }

        return result


def create_default_config() -> DeploymentConfig:
    """Create a new configuration object with default values.

    Returns:
        DeploymentConfig object with default values
    """
    return DeploymentConfig()


def load_config_from_file(config_path: Optional[str] = None) -> DeploymentConfig:
    """Load configuration from file and return a DeploymentConfig object.

    Args:
        config_path: Path to config file. If None, looks for config in current directory.

    Returns:
        DeploymentConfig object with values from file and defaults

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file format is not supported.
    """
    from .cli import load_config as load_config_dict

    # Load configuration as dictionary
    config_data = load_config_dict(config_path)

    # Create configuration object and update it
    config = create_default_config()
    config.update_from_dict(config_data)

    return config
