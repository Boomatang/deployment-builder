"""Configuration management for deployment-builder tool."""

import json
import os
import tomllib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from deployment_builder.keywords import (
    CLUSTERS,
    ENVIRONMENT,
    GENERAL,
    KIND_CONFIG_PATH,
    KUBECONFIG_PATH,
    MAX_WORKERS,
    NAME,
    PREFIX,
    SERVICES,
    VERSION,
)
from deployment_builder.logging_config import get_logger, log_config_loaded, log_error


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
    GENERAL: {
        NAME: "defualt-deployment",
        VERSION: "1.0.0",
        ENVIRONMENT: "development",
        PREFIX: "default",
        KUBECONFIG_PATH: "kubeconfigs",
        KIND_CONFIG_PATH: "kind-configs",
        MAX_WORKERS: 4,
    },
    SERVICES: {},
    CLUSTERS: {},
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
