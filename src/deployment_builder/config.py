"""Configuration management for deployment-builder tool."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ClusterConfig:
    """Configuration for a specific cluster type."""

    enable: bool = False
    count: int = 0


@dataclass
class GeneralConfig:
    """Configuration for the general section."""

    name: str = "default-deployment"
    version: str = "1.0.0"
    environment: str = "development"
    prefix: str = "default"
    kubeconfig_path: str = "kubeconfigs"
    kind_config_path: str = "kind-configs"


@dataclass
class DeploymentConfig:
    """Main configuration object with all default values."""

    # General configuration section
    general: GeneralConfig = field(default_factory=GeneralConfig)

    # Cluster configuration
    clusters: Dict[str, ClusterConfig] = field(
        default_factory=lambda: {
            "metrics": ClusterConfig(enable=False, count=0),
            "primary": ClusterConfig(enable=False, count=0),
            "secondary": ClusterConfig(enable=False, count=0),
            "standard": ClusterConfig(enable=False, count=0),
        }
    )

    def update_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from a dictionary (loaded from config file).

        Args:
            config_data: Configuration data loaded from file
        """
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

        # Update cluster configuration
        if "clusters" in config_data:
            clusters_data = config_data["clusters"]

            # Handle new structured format: [clusters.metrics], [clusters.primary], etc.
            if isinstance(clusters_data, dict) and all(
                isinstance(v, dict) for v in clusters_data.values() if v is not None
            ):
                # New structured format
                for cluster_type, cluster_config in clusters_data.items():
                    if cluster_type in self.clusters and isinstance(cluster_config, dict):
                        if "enable" in cluster_config:
                            self.clusters[cluster_type].enable = cluster_config["enable"]
                        if "count" in cluster_config:
                            self.clusters[cluster_type].count = cluster_config["count"]
            else:
                # Legacy format: metrics = true, primary = 2, etc.
                for cluster_type, value in clusters_data.items():
                    if cluster_type in self.clusters:
                        if isinstance(value, bool):
                            self.clusters[cluster_type].enable = value
                            self.clusters[cluster_type].count = 1 if value else 0
                        elif isinstance(value, int):
                            self.clusters[cluster_type].enable = value > 0
                            self.clusters[cluster_type].count = value

    def get_cluster_names(self) -> list[str]:
        """Get list of cluster names based on current configuration.

        Returns:
            List of cluster names to create
        """
        import re

        # Sanitize prefix from general section
        prefix = re.sub(r"[^a-z0-9-]", "-", self.general.prefix.lower())
        prefix = re.sub(r"-+", "-", prefix)
        prefix = prefix.strip("-")

        if not prefix:
            prefix = "default"

        cluster_names = []

        # Metrics cluster (single)
        if self.clusters["metrics"].enable:
            cluster_names.append(f"{prefix}-metrics")

        # Primary clusters
        for i in range(1, self.clusters["primary"].count + 1):
            cluster_names.append(f"{prefix}-primary-{i}")

        # Secondary clusters
        for i in range(1, self.clusters["secondary"].count + 1):
            cluster_names.append(f"{prefix}-secondary-{i}")

        # Standard clusters
        for i in range(1, self.clusters["standard"].count + 1):
            cluster_names.append(f"{prefix}-standard-{i}")

        # If no clusters defined, create a default one
        if not cluster_names:
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
            },
            "clusters": {
                cluster_type: {"enable": cluster_config.enable, "count": cluster_config.count}
                for cluster_type, cluster_config in self.clusters.items()
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
