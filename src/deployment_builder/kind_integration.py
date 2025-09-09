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


def get_cluster_name_from_config(config_data: dict) -> str:
    """Extract cluster name from configuration data.

    Args:
        config_data: The loaded configuration data

    Returns:
        Cluster name to use for kind operations
    """
    # Try to get cluster name from various possible keys
    cluster_name = config_data.get("cluster_name") or config_data.get("name") or config_data.get("cluster") or "default"

    # Ensure cluster name is valid for kind (lowercase, alphanumeric, hyphens)
    import re

    cluster_name = re.sub(r"[^a-z0-9-]", "-", cluster_name.lower())
    cluster_name = re.sub(r"-+", "-", cluster_name)  # Replace multiple hyphens with single
    cluster_name = cluster_name.strip("-")  # Remove leading/trailing hyphens

    if not cluster_name:
        cluster_name = "default"

    return cluster_name
