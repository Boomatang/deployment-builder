"""Configuration management for deployment-builder tool."""

import json
import os
import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from rich import print

from .logging_config import get_logger, log_config_loaded, log_error

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


class Config(Enum):
    NAME = "name"
    VERSION = "version"
    ENVIRONMENT = "environment"
    PREFIX = "prefix"
    KUBECONFIG_PATH = "kubeconfig_path"
    KIND_CONFIG_PATH = "kind_config_path"
    MAX_WORKERS = "max_workers"
    CLUSTERS = "clusters"
    SERVICES = "services"
    ENABLE = "enable"
    COUNT = "count"
    GENERAL = "general"


default_config = {
    Config.GENERAL.value: {
        Config.NAME.value: "defualt-deployment",
        Config.VERSION.value: "1.0.0",
        Config.ENVIRONMENT.value: "development",
        Config.PREFIX.value: "default",
        Config.KUBECONFIG_PATH.value: "kubeconfigs",
        Config.KIND_CONFIG_PATH.value: "kind-configs",
        Config.MAX_WORKERS.value: 4,
    },
    Config.SERVICES.value: {},
    Config.CLUSTERS.value: {},
}


def merge(a: dict, b: dict) -> dict:
    for key in a:
        if key in b:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                a[key].update(merge(a[key], b[key]))
            else:
                a[key] = b[key]

    for key in b:
        if key not in a:
            a[key] = b[key]
    return a


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file.

    Args:
        config_path: Path to config file. If None, looks for config in current directory.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file format is not supported.
    """
    logger = get_logger()

    if config_path is None:
        # Look for common config file names in current directory, TOML first
        config_files = [
            "config.toml",
            "deployment.toml",
            "config.json",
            "config.yaml",
            "config.yml",
            "deployment.json",
            "deployment.yaml",
            "deployment.yml",
        ]
        logger.debug(f"Searching for config files in current directory: {config_files}")

        for config_file in config_files:
            if os.path.exists(config_file):
                config_path = config_file
                logger.info(f"Found configuration file: {config_file}")
                break
        else:
            logger.error("No configuration file found in current directory")
            raise FileNotFoundError("No configuration file found in current directory")

    config_path = Path(config_path)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    logger.info(f"Loading configuration from: {config_path}")

    try:
        # Load based on file extension
        with open(config_path, "rb") as f:
            if config_path.suffix.lower() in [".toml"]:
                config_data = tomllib.load(f)
            elif config_path.suffix.lower() in [".json"]:
                config_data = json.load(f)
            elif config_path.suffix.lower() in [".yaml", ".yml"]:
                config_data = yaml.safe_load(f)
            else:
                logger.error(f"Unsupported configuration file format: {config_path.suffix}")
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")

        log_config_loaded(config_data, str(config_path))
        return config_data

    except Exception as e:
        log_error(e, f"loading configuration from {config_path}")
        raise


def load_config_from_file(config_path: Optional[str] = None) -> Dict:
    """Load configuration from file and return a DeploymentConfig object."""

    config_data = load_config(config_path)
    config = merge(default_config, config_data)

    return config


def get_cluster_names(config: dict) -> list[str]:
    prefix = config[Config.GENERAL.value][Config.PREFIX.value]
    clusters = []
    for cluster in config[Config.CLUSTERS.value]:
        c = config[Config.CLUSTERS.value][cluster]
        if Config.ENABLE.value in c and c[Config.ENABLE.value]:
            clusters.append("-".join([prefix, cluster]))
            continue
        for num in range(c.get(Config.COUNT.value, 0)):
            clusters.append("-".join([prefix, cluster, str(num + 1)]))

    return clusters
