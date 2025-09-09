"""Integration with kind CLI for Kubernetes cluster management."""

import subprocess
import sys
from typing import Optional, Tuple

from .logging_config import get_logger


def run_kind_command(command: str, cluster_name: str, log_output: bool = False) -> Tuple[bool, str, str]:
    """Run a kind command and return success status and output.

    Args:
        command: The kind command to run ('create' or 'delete')
        cluster_name: Name of the cluster to create/delete
        log_output: Whether to log the command output to the log file

    Returns:
        Tuple of (success, stdout, stderr)
    """
    logger = get_logger()

    if command not in ["create", "delete"]:
        raise ValueError(f"Invalid kind command: {command}. Must be 'create' or 'delete'")

    # Build the kind command
    if command == "create":
        cmd = ["kind", "create", "cluster", "--name", cluster_name]
    else:  # delete
        cmd = ["kind", "delete", "cluster", "--name", cluster_name]

    logger.info(f"Running kind command: {' '.join(cmd)}")

    try:
        # Run the command and capture output
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False  # Don't raise exception on non-zero exit
        )

        success = result.returncode == 0

        if success:
            logger.info(f"Kind {command} command completed successfully")
        else:
            logger.error(f"Kind {command} command failed with return code {result.returncode}")

        # Log output if requested (debug level) or if there was an error
        if log_output or not success:
            if result.stdout:
                logger.debug(f"Kind stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Kind stderr: {result.stderr}")

        return success, result.stdout, result.stderr

    except FileNotFoundError:
        error_msg = "kind command not found. Please install kind (https://kind.sigs.k8s.io/)"
        logger.error(error_msg)
        return False, "", error_msg
    except Exception as e:
        error_msg = f"Error running kind command: {e}"
        logger.error(error_msg)
        return False, "", error_msg


def create_cluster(cluster_name: str, log_output: bool = False) -> bool:
    """Create a kind cluster.

    Args:
        cluster_name: Name of the cluster to create
        log_output: Whether to log the command output to the log file

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()
    logger.info(f"Creating kind cluster: {cluster_name}")

    success, stdout, stderr = run_kind_command("create", cluster_name, log_output)

    if success:
        logger.info(f"Successfully created cluster: {cluster_name}")
        return True
    else:
        logger.error(f"Failed to create cluster: {cluster_name}")
        if stderr:
            logger.error(f"Error details: {stderr}")
        return False


def delete_cluster(cluster_name: str, log_output: bool = False) -> bool:
    """Delete a kind cluster.

    Args:
        cluster_name: Name of the cluster to delete
        log_output: Whether to log the command output to the log file

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()
    logger.info(f"Deleting kind cluster: {cluster_name}")

    success, stdout, stderr = run_kind_command("delete", cluster_name, log_output)

    if success:
        logger.info(f"Successfully deleted cluster: {cluster_name}")
        return True
    else:
        logger.error(f"Failed to delete cluster: {cluster_name}")
        if stderr:
            logger.error(f"Error details: {stderr}")
        return False


def check_kind_available() -> bool:
    """Check if kind CLI is available.

    Returns:
        True if kind is available, False otherwise
    """
    logger = get_logger()

    try:
        result = subprocess.run(["kind", "version"], capture_output=True, text=True, check=False)

        if result.returncode == 0:
            logger.debug(f"Kind is available: {result.stdout.strip()}")
            return True
        else:
            logger.warning("Kind command failed, may not be properly installed")
            return False

    except FileNotFoundError:
        logger.warning("Kind command not found")
        return False
    except Exception as e:
        logger.warning(f"Error checking kind availability: {e}")
        return False


def get_cluster_names_from_config(config_data: dict) -> list[str]:
    """Extract cluster names from configuration data based on cluster types.

    Args:
        config_data: The loaded configuration data

    Returns:
        List of cluster names to create
    """
    logger = get_logger()

    # Get prefix from config
    prefix = config_data.get("prefix", "default")

    # Sanitize prefix
    import re

    prefix = re.sub(r"[^a-z0-9-]", "-", prefix.lower())
    prefix = re.sub(r"-+", "-", prefix)
    prefix = prefix.strip("-")

    if not prefix:
        prefix = "default"

    cluster_names = []
    clusters_config = config_data.get("clusters", {})

    # Metrics cluster (single)
    if clusters_config.get("metrics", False):
        cluster_names.append(f"{prefix}-metrics")
        logger.info("Including metrics cluster")

    # Primary clusters
    primary_count = clusters_config.get("primary", 0)
    for i in range(1, primary_count + 1):
        cluster_names.append(f"{prefix}-primary-{i}")
        logger.info(f"Including primary cluster {i}")

    # Secondary clusters
    secondary_count = clusters_config.get("secondary", 0)
    for i in range(1, secondary_count + 1):
        cluster_names.append(f"{prefix}-secondary-{i}")
        logger.info(f"Including secondary cluster {i}")

    # Standard clusters
    standard_count = clusters_config.get("standard", 0)
    for i in range(1, standard_count + 1):
        cluster_names.append(f"{prefix}-standard-{i}")
        logger.info(f"Including standard cluster {i}")

    # If no clusters defined, create a default one
    if not cluster_names:
        cluster_names.append(f"{prefix}-default")
        logger.info("No cluster configuration found, creating default cluster")

    logger.info(f"Generated {len(cluster_names)} cluster names: {cluster_names}")
    return cluster_names


def create_multiple_clusters(config_data: dict, log_output: bool = False) -> dict[str, bool]:
    """Create multiple clusters based on configuration.

    Args:
        config_data: The loaded configuration data
        log_output: Whether to log the command output to the log file

    Returns:
        Dictionary mapping cluster names to success status
    """
    logger = get_logger()
    cluster_names = get_cluster_names_from_config(config_data)
    results = {}

    logger.info(f"Creating {len(cluster_names)} clusters")

    for cluster_name in cluster_names:
        logger.info(f"Creating cluster: {cluster_name}")
        success = create_cluster(cluster_name, log_output)
        results[cluster_name] = success

        if success:
            logger.info(f"✓ Successfully created cluster: {cluster_name}")
        else:
            logger.error(f"✗ Failed to create cluster: {cluster_name}")

    successful = sum(1 for success in results.values() if success)
    logger.info(f"Cluster creation completed: {successful}/{len(cluster_names)} successful")

    return results


def delete_multiple_clusters(config_data: dict, log_output: bool = False) -> dict[str, bool]:
    """Delete multiple clusters based on configuration.

    Args:
        config_data: The loaded configuration data
        log_output: Whether to log the command output to the log file

    Returns:
        Dictionary mapping cluster names to success status
    """
    logger = get_logger()
    cluster_names = get_cluster_names_from_config(config_data)
    results = {}

    logger.info(f"Deleting {len(cluster_names)} clusters")

    for cluster_name in cluster_names:
        logger.info(f"Deleting cluster: {cluster_name}")
        success = delete_cluster(cluster_name, log_output)
        results[cluster_name] = success

        if success:
            logger.info(f"✓ Successfully deleted cluster: {cluster_name}")
        else:
            logger.error(f"✗ Failed to delete cluster: {cluster_name}")

    successful = sum(1 for success in results.values() if success)
    logger.info(f"Cluster deletion completed: {successful}/{len(cluster_names)} successful")

    return results


def get_cluster_name_from_config(config_data: dict) -> str:
    """Extract single cluster name from configuration data (backward compatibility).

    Args:
        config_data: The loaded configuration data

    Returns:
        Cluster name to use for kind operations
    """
    cluster_names = get_cluster_names_from_config(config_data)
    return cluster_names[0] if cluster_names else "default"
