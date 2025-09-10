"""Integration with kind CLI for Kubernetes cluster management."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import yaml

from .logging_config import get_logger


def run_kind_command(
    command: str,
    cluster_name: str,
    log_output: bool = False,
    kubeconfig_file: Optional[Path] = None,
    kind_config_file: Optional[Path] = None,
) -> Tuple[bool, str, str]:
    """Run a kind command and return success status and output.

    Args:
        command: The kind command to run ('create' or 'delete')
        cluster_name: Name of the cluster to create/delete
        log_output: Whether to log the command output to the log file
        kubeconfig_file: Path to the kubeconfig file for this cluster
        kind_config_file: Path to the kind configuration file for this cluster

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

    # Add kubeconfig flag if provided
    env = None
    if kubeconfig_file:
        cmd.extend(["--kubeconfig", str(kubeconfig_file)])
        logger.debug(f"Using kubeconfig: {kubeconfig_file}")

    # Add kind config file if provided (only for create command)
    if kind_config_file and command == "create":
        cmd.extend(["--config", str(kind_config_file)])
        logger.debug(f"Using kind config: {kind_config_file}")

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


def create_cluster(
    cluster_name: str,
    log_output: bool = False,
    kubeconfig_file: Optional[Path] = None,
    kind_config_file: Optional[Path] = None,
) -> bool:
    """Create a kind cluster.

    Args:
        cluster_name: Name of the cluster to create
        log_output: Whether to log the command output to the log file
        kubeconfig_file: Path to the kubeconfig file for this cluster
        kind_config_file: Path to the kind configuration file for this cluster

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()
    logger.info(f"Creating kind cluster: {cluster_name}")

    success, stdout, stderr = run_kind_command("create", cluster_name, log_output, kubeconfig_file, kind_config_file)

    if success:
        logger.info(f"Successfully created cluster: {cluster_name}")
        return True
    else:
        logger.error(f"Failed to create cluster: {cluster_name}")
        if stderr:
            logger.error(f"Error details: {stderr}")
        return False


def delete_cluster(cluster_name: str, log_output: bool = False, kubeconfig_file: Optional[Path] = None) -> bool:
    """Delete a kind cluster.

    Args:
        cluster_name: Name of the cluster to delete
        log_output: Whether to log the command output to the log file
        kubeconfig_file: Path to the kubeconfig file for this cluster

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()
    logger.info(f"Deleting kind cluster: {cluster_name}")

    success, stdout, stderr = run_kind_command("delete", cluster_name, log_output, kubeconfig_file)

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


def _calculate_optimal_workers(cluster_count: int, max_workers: int = 4) -> int:
    """Calculate the optimal number of workers for parallel execution.

    Args:
        cluster_count: Number of clusters to process
        max_workers: Maximum number of workers to use

    Returns:
        Optimal number of workers
    """
    # Don't use more workers than clusters
    optimal_workers = min(cluster_count, max_workers)

    # For very small numbers, use sequential execution
    # No special case for small cluster counts; always use optimal_workers

    return optimal_workers


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

    # Handle new structured format: [clusters.metrics], [clusters.primary], etc.
    # Check if all cluster values are dictionaries (new format)
    if isinstance(clusters_config, dict) and all(
        isinstance(v, dict) for v in clusters_config.values() if v is not None
    ):
        # New structured format
        logger.debug("Using new structured cluster configuration format")

        # Metrics cluster (single)
        metrics_config = clusters_config.get("metrics", {})
        if isinstance(metrics_config, dict) and metrics_config.get("enable", False):
            cluster_names.append(f"{prefix}-metrics")
            logger.info("Including metrics cluster")

        # Primary clusters
        primary_config = clusters_config.get("primary", {})
        if isinstance(primary_config, dict):
            primary_count = primary_config.get("count", 0)
            for i in range(1, primary_count + 1):
                cluster_names.append(f"{prefix}-primary-{i}")
                logger.info(f"Including primary cluster {i}")

        # Secondary clusters
        secondary_config = clusters_config.get("secondary", {})
        if isinstance(secondary_config, dict):
            secondary_count = secondary_config.get("count", 0)
            for i in range(1, secondary_count + 1):
                cluster_names.append(f"{prefix}-secondary-{i}")
                logger.info(f"Including secondary cluster {i}")

        # Standard clusters
        standard_config = clusters_config.get("standard", {})
        if isinstance(standard_config, dict):
            standard_count = standard_config.get("count", 0)
            for i in range(1, standard_count + 1):
                cluster_names.append(f"{prefix}-standard-{i}")
                logger.info(f"Including standard cluster {i}")

    else:
        # Legacy format: metrics = true, primary = 2, etc.
        # Also handle mixed format by treating each cluster type individually
        logger.debug("Using legacy cluster configuration format")

        # Metrics cluster (single)
        metrics_value = clusters_config.get("metrics", False)
        if isinstance(metrics_value, dict):
            # New format within legacy detection
            if metrics_value.get("enable", False):
                cluster_names.append(f"{prefix}-metrics")
                logger.info("Including metrics cluster")
        elif metrics_value:
            # Legacy format
            cluster_names.append(f"{prefix}-metrics")
            logger.info("Including metrics cluster")

        # Primary clusters
        primary_value = clusters_config.get("primary", 0)
        if isinstance(primary_value, dict):
            # New format within legacy detection
            primary_count = primary_value.get("count", 0)
        else:
            # Legacy format
            primary_count = primary_value
        for i in range(1, primary_count + 1):
            cluster_names.append(f"{prefix}-primary-{i}")
            logger.info(f"Including primary cluster {i}")

        # Secondary clusters
        secondary_value = clusters_config.get("secondary", 0)
        if isinstance(secondary_value, dict):
            # New format within legacy detection
            secondary_count = secondary_value.get("count", 0)
        else:
            # Legacy format
            secondary_count = secondary_value
        for i in range(1, secondary_count + 1):
            cluster_names.append(f"{prefix}-secondary-{i}")
            logger.info(f"Including secondary cluster {i}")

        # Standard clusters
        standard_value = clusters_config.get("standard", 0)
        if isinstance(standard_value, dict):
            # New format within legacy detection
            standard_count = standard_value.get("count", 0)
        else:
            # Legacy format
            standard_count = standard_value
        for i in range(1, standard_count + 1):
            cluster_names.append(f"{prefix}-standard-{i}")
            logger.info(f"Including standard cluster {i}")

    # If no clusters defined, create a default one
    if not cluster_names:
        cluster_names.append(f"{prefix}-default")
        logger.info("No cluster configuration found, creating default cluster")

    logger.info(f"Generated {len(cluster_names)} cluster names: {cluster_names}")
    return cluster_names


def get_cluster_names_from_config_object(config: "DeploymentConfig") -> list[str]:
    """Extract cluster names from a DeploymentConfig object.

    Args:
        config: The DeploymentConfig object

    Returns:
        List of cluster names to create
    """
    logger = get_logger()
    logger.debug("Using DeploymentConfig object for cluster name generation")

    cluster_names = config.get_cluster_names()
    logger.info(f"Generated {len(cluster_names)} cluster names: {cluster_names}")
    return cluster_names


def _create_single_cluster_parallel(
    cluster_name: str,
    log_output: bool = False,
    kubeconfig_dir: Optional[Path] = None,
    kind_config_dir: Optional[Path] = None,
    config_data: Optional[dict] = None,
) -> Tuple[str, bool]:
    """Create a single cluster (for parallel execution).

    Args:
        cluster_name: Name of the cluster to create
        log_output: Whether to log the command output to the log file
        kubeconfig_dir: Directory to save kubeconfig file
        kind_config_dir: Directory to save kind config file
        config_data: Configuration data for generating kind config

    Returns:
        Tuple of (cluster_name, success)
    """
    logger = get_logger()
    start_time = time.time()
    logger.info(f"🚀 Starting parallel creation of cluster: {cluster_name}")

    # Get kubeconfig file path
    kubeconfig_file = None
    if kubeconfig_dir:
        kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"

    # Generate and save kind config if needed
    kind_config_file = None
    if kind_config_dir and config_data:
        kind_config = generate_kind_config(cluster_name, config_data)
        if save_kind_config(cluster_name, kind_config, kind_config_dir):
            kind_config_file = kind_config_dir / f"{cluster_name}-kind-config.yaml"

    success = create_cluster(cluster_name, log_output, kubeconfig_file, kind_config_file)

    # Extract kubeconfig if cluster creation was successful
    if success and kubeconfig_dir:
        kubeconfig_success = extract_kubeconfig(cluster_name, kubeconfig_dir)
        if not kubeconfig_success:
            logger.warning(f"Failed to extract kubeconfig for {cluster_name}, but cluster was created")

    end_time = time.time()
    duration = end_time - start_time

    if success:
        logger.info(f"✓ Successfully created cluster: {cluster_name} (took {duration:.2f}s)")
    else:
        logger.error(f"✗ Failed to create cluster: {cluster_name} (took {duration:.2f}s)")

    return cluster_name, success


def create_multiple_clusters(config_data: dict, log_output: bool = False, max_workers: int = 4) -> dict[str, bool]:
    """Create multiple clusters based on configuration using parallel execution.

    Args:
        config_data: The loaded configuration data
        log_output: Whether to log the command output to the log file
        max_workers: Maximum number of parallel workers

    Returns:
        Dictionary mapping cluster names to success status
    """
    logger = get_logger()
    cluster_names = get_cluster_names_from_config(config_data)
    results = {}

    # Get kubeconfig and kind config directories
    kubeconfig_dir = get_kubeconfig_path_from_config(config_data)
    kind_config_dir = get_kind_config_path_from_config(config_data)
    logger.info(f"Kubeconfig directory: {kubeconfig_dir}")
    logger.info(f"Kind config directory: {kind_config_dir}")

    # Calculate optimal number of workers
    optimal_workers = _calculate_optimal_workers(len(cluster_names), max_workers)

    if optimal_workers == 1:
        logger.info(f"Creating {len(cluster_names)} clusters sequentially")
        # Use sequential execution for small numbers
        for cluster_name in cluster_names:
            cluster_name, success = _create_single_cluster_parallel(
                cluster_name, log_output, kubeconfig_dir, kind_config_dir, config_data
            )
            results[cluster_name] = success
    else:
        logger.info(f"Creating {len(cluster_names)} clusters in parallel ({optimal_workers} workers)")
        logger.info(f"Starting parallel execution for clusters: {', '.join(cluster_names)}")

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            # Submit all cluster creation tasks
            future_to_cluster = {
                executor.submit(
                    _create_single_cluster_parallel,
                    cluster_name,
                    log_output,
                    kubeconfig_dir,
                    kind_config_dir,
                    config_data,
                ): cluster_name
                for cluster_name in cluster_names
            }

            # Process completed tasks as they finish
            completed = 0
            total = len(cluster_names)
            for future in as_completed(future_to_cluster):
                cluster_name, success = future.result()
                results[cluster_name] = success
                completed += 1
                logger.info(f"Progress: {completed}/{total} clusters completed")

    successful = sum(1 for success in results.values() if success)
    logger.info(f"Cluster creation completed: {successful}/{len(cluster_names)} successful")

    return results


def _delete_single_cluster_parallel(
    cluster_name: str,
    log_output: bool = False,
    kubeconfig_dir: Optional[Path] = None,
    kind_config_dir: Optional[Path] = None,
) -> Tuple[str, bool]:
    """Delete a single cluster (for parallel execution).

    Args:
        cluster_name: Name of the cluster to delete
        log_output: Whether to log the command output to the log file
        kubeconfig_dir: Directory containing kubeconfig file
        kind_config_dir: Directory containing kind config file

    Returns:
        Tuple of (cluster_name, success)
    """
    logger = get_logger()
    start_time = time.time()
    logger.info(f"🗑️  Starting parallel deletion of cluster: {cluster_name}")

    # Get kubeconfig file path
    kubeconfig_file = None
    if kubeconfig_dir:
        kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"

    # Remove kubeconfig and kind config first (before cluster deletion)
    if kubeconfig_dir:
        remove_kubeconfig(cluster_name, kubeconfig_dir)
    if kind_config_dir:
        remove_kind_config(cluster_name, kind_config_dir)

    success = delete_cluster(cluster_name, log_output, kubeconfig_file)

    end_time = time.time()
    duration = end_time - start_time

    if success:
        logger.info(f"✓ Successfully deleted cluster: {cluster_name} (took {duration:.2f}s)")
    else:
        logger.error(f"✗ Failed to delete cluster: {cluster_name} (took {duration:.2f}s)")

    return cluster_name, success


def delete_multiple_clusters(config_data: dict, log_output: bool = False, max_workers: int = 4) -> dict[str, bool]:
    """Delete multiple clusters based on configuration using parallel execution.

    Args:
        config_data: The loaded configuration data
        log_output: Whether to log the command output to the log file
        max_workers: Maximum number of parallel workers

    Returns:
        Dictionary mapping cluster names to success status
    """
    logger = get_logger()
    cluster_names = get_cluster_names_from_config(config_data)
    results = {}

    # Get kubeconfig and kind config directories
    kubeconfig_dir = get_kubeconfig_path_from_config(config_data)
    kind_config_dir = get_kind_config_path_from_config(config_data)
    logger.info(f"Kubeconfig directory: {kubeconfig_dir}")
    logger.info(f"Kind config directory: {kind_config_dir}")

    # Calculate optimal number of workers
    optimal_workers = _calculate_optimal_workers(len(cluster_names), max_workers)

    if optimal_workers == 1:
        logger.info(f"Deleting {len(cluster_names)} clusters sequentially")
        # Use sequential execution for small numbers
        for cluster_name in cluster_names:
            cluster_name, success = _delete_single_cluster_parallel(
                cluster_name, log_output, kubeconfig_dir, kind_config_dir
            )
            results[cluster_name] = success
    else:
        logger.info(f"Deleting {len(cluster_names)} clusters in parallel ({optimal_workers} workers)")
        logger.info(f"Starting parallel execution for clusters: {', '.join(cluster_names)}")

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            # Submit all cluster deletion tasks
            future_to_cluster = {
                executor.submit(
                    _delete_single_cluster_parallel, cluster_name, log_output, kubeconfig_dir, kind_config_dir
                ): cluster_name
                for cluster_name in cluster_names
            }

            # Process completed tasks as they finish
            completed = 0
            total = len(cluster_names)
            for future in as_completed(future_to_cluster):
                cluster_name, success = future.result()
                results[cluster_name] = success
                completed += 1
                logger.info(f"Progress: {completed}/{total} clusters completed")

    successful = sum(1 for success in results.values() if success)
    logger.info(f"Cluster deletion completed: {successful}/{len(cluster_names)} successful")

    return results


def get_kubeconfig_path_from_config(config_data: dict) -> Path:
    """Get kubeconfig directory path from configuration.

    Args:
        config_data: The loaded configuration data

    Returns:
        Path to kubeconfig directory
    """
    kubeconfig_path = config_data.get("kubeconfig_path", "kubeconfigs")
    return Path(kubeconfig_path).resolve()


def get_kind_config_path_from_config(config_data: dict) -> Path:
    """Get kind config directory path from configuration.

    Args:
        config_data: The loaded configuration data

    Returns:
        Path to kind config directory
    """
    kind_config_path = config_data.get("kind_config_path", "kind-configs")
    return Path(kind_config_path).resolve()


def generate_kind_config(cluster_name: str, config_data: dict) -> dict:
    """Generate a kind cluster configuration YAML.

    Args:
        cluster_name: Name of the cluster
        config_data: The loaded configuration data

    Returns:
        Dictionary representing the kind configuration
    """
    # Base kind configuration
    kind_config = {
        "kind": "Cluster",
        "apiVersion": "kind.x-k8s.io/v1alpha4",
        "name": cluster_name,
    }

    # Add networking configuration if specified
    if "networking" in config_data:
        kind_config["networking"] = config_data["networking"]

    # Add feature gates if specified
    if "feature_gates" in config_data:
        kind_config["featureGates"] = config_data["feature_gates"]

    # Add runtime config if specified
    if "runtime_config" in config_data:
        kind_config["runtimeConfig"] = config_data["runtime_config"]

    # Add nodes configuration if specified
    if "nodes" in config_data:
        kind_config["nodes"] = config_data["nodes"]

    return kind_config


def save_kind_config(cluster_name: str, kind_config: dict, config_dir: Path) -> bool:
    """Save kind configuration to a YAML file.

    Args:
        cluster_name: Name of the cluster
        kind_config: The kind configuration dictionary
        config_dir: Directory to save the config file

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()

    try:
        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create config file path
        config_file = config_dir / f"{cluster_name}-kind-config.yaml"

        # Write YAML configuration
        with open(config_file, "w") as f:
            yaml.dump(kind_config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"✓ Kind config saved to: {config_file}")
        return True

    except Exception as e:
        logger.error(f"Error saving kind config for {cluster_name}: {e}")
        return False


def remove_kind_config(cluster_name: str, config_dir: Path) -> bool:
    """Remove kind configuration file for a specific cluster.

    Args:
        cluster_name: Name of the cluster
        config_dir: Directory containing the config file

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()

    config_file = config_dir / f"{cluster_name}-kind-config.yaml"

    try:
        if config_file.exists():
            config_file.unlink()
            logger.info(f"✓ Kind config removed: {config_file}")
            return True
        else:
            logger.debug(f"Kind config file not found: {config_file}")
            return True  # Not an error if file doesn't exist

    except Exception as e:
        logger.error(f"Error removing kind config for {cluster_name}: {e}")
        return False


def extract_kubeconfig(cluster_name: str, kubeconfig_dir: Path) -> bool:
    """Extract kubeconfig for a specific cluster.

    Args:
        cluster_name: Name of the cluster
        kubeconfig_dir: Directory to save the kubeconfig file

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()

    # Ensure kubeconfig directory exists
    kubeconfig_dir.mkdir(parents=True, exist_ok=True)

    # Create kubeconfig file path
    kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"

    try:
        # Extract kubeconfig using kind
        cmd = ["kind", "get", "kubeconfig", "--name", cluster_name]
        logger.debug(f"Extracting kubeconfig for {cluster_name}: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Write kubeconfig to file
        with open(kubeconfig_file, "w") as f:
            f.write(result.stdout)

        logger.info(f"✓ Kubeconfig saved to: {kubeconfig_file}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract kubeconfig for {cluster_name}: {e}")
        logger.debug(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error saving kubeconfig for {cluster_name}: {e}")
        return False


def remove_kubeconfig(cluster_name: str, kubeconfig_dir: Path) -> bool:
    """Remove kubeconfig file for a specific cluster.

    Args:
        cluster_name: Name of the cluster
        kubeconfig_dir: Directory containing the kubeconfig file

    Returns:
        True if successful, False otherwise
    """
    logger = get_logger()

    kubeconfig_file = kubeconfig_dir / f"{cluster_name}.kubeconfig"

    try:
        if kubeconfig_file.exists():
            kubeconfig_file.unlink()
            logger.info(f"✓ Kubeconfig removed: {kubeconfig_file}")
            return True
        else:
            logger.debug(f"Kubeconfig file not found: {kubeconfig_file}")
            return True  # Not an error if file doesn't exist

    except Exception as e:
        logger.error(f"Error removing kubeconfig for {cluster_name}: {e}")
        return False


def get_cluster_name_from_config(config_data: dict) -> str:
    """Extract single cluster name from configuration data (backward compatibility).

    Args:
        config_data: The loaded configuration data

    Returns:
        Cluster name to use for kind operations
    """
    cluster_names = get_cluster_names_from_config(config_data)
    return cluster_names[0] if cluster_names else "default"
