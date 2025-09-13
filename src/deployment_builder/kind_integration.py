"""Integration with kind CLI for Kubernetes cluster management."""

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from rich import print

from .config import Config, get_cluster_names
from .execution_planner import ExecutionPlanner
from .load_balancer import create_load_balancer
from .logging_config import get_logger
from .queue import ServiceQueue, WorkerPool


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


def _create_single_cluster_parallel(
    cluster_name: str,
    log_output: bool = False,
    kubeconfig_dir: Optional[Path] = None,
    kind_config_dir: Optional[Path] = None,
    config_data: Optional[dict] = None,
    services: Optional[dict] = None,
) -> Tuple[str, bool]:
    """Create a single cluster (for parallel execution).

    Args:
        cluster_name: Name of the cluster to create
        log_output: Whether to log the command output to the log file
        kubeconfig_dir: Directory to save kubeconfig file
        kind_config_dir: Directory to save kind config file
        config_data: Configuration data for generating kind config
        services: Dictionary of services to execute after cluster creation

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

        # Execute services if cluster creation was successful and services are configured
        if success and kubeconfig_file:
            # Determine which services to run for this cluster
            cluster_services = {}

            # Add global services
            global_services = services.get("global", {})
            if global_services:
                cluster_services.update(global_services)

            # Add cluster-specific services based on cluster name
            cluster_type = _get_cluster_type_from_name(cluster_name)
            if cluster_type and cluster_type in services:
                cluster_services.update(services[cluster_type])

            if cluster_services:
                logger.info(f"Executing {len(cluster_services)} services for cluster: {cluster_name}")
                service_results = execute_services_for_cluster(
                    cluster_name, cluster_services, kubeconfig_file, log_output
                )

                # Log service results
                successful_services = sum(1 for _, success, _, _ in service_results if success)
                total_services = len(service_results)

                if total_services > 0:
                    logger.info(
                        f"✓ Executed {successful_services}/{total_services} services successfully for {cluster_name}"
                    )

                    # Log any failed services
                    for service_name, service_success, _, stderr in service_results:
                        if not service_success:
                            logger.error(f"✗ Service '{service_name}' failed on {cluster_name}: {stderr}")
            else:
                logger.debug(f"No services configured for cluster: {cluster_name}")

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
    cluster_names = get_cluster_names(config_data)
    results = {}

    # Get kubeconfig and kind config directories
    kubeconfig_dir = get_kubeconfig_path_from_config(config_data)
    kind_config_dir = get_kind_config_path_from_config(config_data)
    logger.info(f"Kubeconfig directory: {kubeconfig_dir}")
    logger.info(f"Kind config directory: {kind_config_dir}")

    # Extract services configuration
    services = {}

    # Add global services
    global_services = config_data.get("services", {})
    if global_services:
        services["global"] = global_services
        logger.info(f"Global services configured: {list(global_services.keys())}")

    # Add cluster-specific services
    clusters_config = config_data.get("clusters", {})
    if isinstance(clusters_config, dict):
        for cluster_type, cluster_config in clusters_config.items():
            if isinstance(cluster_config, dict) and "services" in cluster_config:
                cluster_services = cluster_config["services"]
                if cluster_services:
                    services[cluster_type] = cluster_services
                    logger.info(f"Services configured for {cluster_type}: {list(cluster_services.keys())}")

    if not services:
        logger.info("No services configured")

    # Calculate optimal number of workers
    optimal_workers = min(len(cluster_names), max_workers)
    print(cluster_names)
    print("the number of works is: ", optimal_workers)
    if optimal_workers == 1:
        logger.info(f"Creating {len(cluster_names)} clusters sequentially")
        # Use sequential execution for small numbers
        for cluster_name in cluster_names:
            cluster_name, success = _create_single_cluster_parallel(
                cluster_name, log_output, kubeconfig_dir, kind_config_dir, config_data, services
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
                    services,
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


def delete_multiple_clusters(config_data: dict, log_output: bool = False) -> dict[str, bool]:
    """Delete multiple clusters based on configuration.

    Args:
        config_data: The loaded configuration data
        log_output: Whether to log the command output to the log file
    Returns:
        Dictionary mapping cluster names to success status
    """
    logger = get_logger()
    cluster_names = get_cluster_names(config_data)
    results = {}

    # Get kubeconfig and kind config directories
    kubeconfig_dir = get_kubeconfig_path_from_config(config_data)
    kind_config_dir = get_kind_config_path_from_config(config_data)
    logger.info(f"Kubeconfig directory: {kubeconfig_dir}")
    logger.info(f"Kind config directory: {kind_config_dir}")

    logger.info(f"Deleting {len(cluster_names)} clusters sequentially")
    # Use sequential execution for small numbers
    for cluster_name in cluster_names:
        cluster_name, success = _delete_single_cluster_parallel(
            cluster_name, log_output, kubeconfig_dir, kind_config_dir
        )
        results[cluster_name] = success

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


def _get_cluster_type_from_name(cluster_name: str) -> Optional[str]:
    """Extract cluster type from cluster name.

    Args:
        cluster_name: Name of the cluster (e.g., "my-project-primary-1")

    Returns:
        Cluster type (e.g., "primary") or None if not found
    """
    # Extract cluster type from cluster name pattern: prefix-type-number
    parts = cluster_name.split("-")
    if len(parts) >= 2:
        # Look for cluster type in the middle parts (skip prefix, skip number if present)
        # Pattern: prefix-type or prefix-type-number
        if len(parts) == 2:
            # Single cluster: prefix-type
            return parts[1]
        elif len(parts) >= 3:
            # Multiple clusters: prefix-type-number
            # The cluster type is the second-to-last part
            return parts[-2]
    return None


def get_cluster_name_from_config(config_data: dict) -> str:
    """Extract single cluster name from configuration data (backward compatibility).

    Args:
        config_data: The loaded configuration data

    Returns:
        Cluster name to use for kind operations
    """
    cluster_names = get_cluster_names(config_data)
    return cluster_names[0] if cluster_names else "default"


def execute_service_command(
    service_name: str,
    service_config: dict,
    cluster_name: str,
    kubeconfig_file: Path,
    log_output: bool = False,
) -> Tuple[bool, str, str]:
    """Execute a service command against a specific cluster.

    Args:
        service_name: Name of the service (for logging)
        service_config: Service configuration containing cmd and kubeconfig_flag
        cluster_name: Name of the cluster to run the command against
        kubeconfig_file: Path to the kubeconfig file for this cluster
        log_output: Whether to log the command output to the log file

    Returns:
        Tuple of (success, stdout, stderr)
    """
    logger = get_logger()

    try:
        cmd = service_config.get("cmd", "")
        kubeconfig_flag = service_config.get("kubeconfig.flag", "--kubeconfig")

        if not cmd:
            logger.warning(f"Service '{service_name}' has no command defined, skipping")
            return True, "", ""

        # Build the command with kubeconfig flag
        full_cmd = [cmd.split()[0]] + cmd.split()[1:] + [kubeconfig_flag, str(kubeconfig_file)]

        logger.info(f"Executing service '{service_name}' on cluster '{cluster_name}': {cmd}")
        logger.debug(f"Full command: {' '.join(full_cmd)}")

        # Execute the command
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        success = result.returncode == 0

        if success:
            logger.info(f"Service '{service_name}' completed successfully on cluster '{cluster_name}'")
        else:
            logger.error(
                f"Service '{service_name}' failed on cluster '{cluster_name}' with return code {result.returncode}"
            )
            logger.error(f"Error output: {result.stderr}")

        if log_output and result.stdout:
            logger.debug(f"Service '{service_name}' stdout: {result.stdout}")
        if log_output and result.stderr:
            logger.debug(f"Service '{service_name}' stderr: {result.stderr}")

        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        logger.error(f"Service '{service_name}' timed out on cluster '{cluster_name}'")
        return False, "", "Command timed out"
    except Exception as e:
        logger.error(f"Error executing service '{service_name}' on cluster '{cluster_name}': {e}")
        return False, "", str(e)


def execute_services_for_cluster(
    cluster_name: str,
    services: dict,
    kubeconfig_file: Path,
    log_output: bool = False,
) -> List[Tuple[str, bool, str, str]]:
    """Execute all services for a specific cluster.

    Args:
        cluster_name: Name of the cluster
        services: Dictionary of service configurations
        kubeconfig_file: Path to the kubeconfig file for this cluster
        log_output: Whether to log the command output to the log file

    Returns:
        List of tuples (service_name, success, stdout, stderr)
    """
    logger = get_logger()
    results = []

    if not services:
        logger.debug(f"No services configured for cluster '{cluster_name}'")
        return results

    logger.info(f"Executing {len(services)} services for cluster '{cluster_name}'")

    for service_name, service_config in services.items():
        logger.debug(f"Executing service '{service_name}' on cluster '{cluster_name}'")
        success, stdout, stderr = execute_service_command(
            service_name, service_config, cluster_name, kubeconfig_file, log_output
        )
        results.append((service_name, success, stdout, stderr))

    return results


def execute_services_for_all_clusters(
    cluster_names: List[str],
    services: dict,
    kubeconfig_path: str,
    log_output: bool = False,
) -> Dict[str, List[Tuple[str, bool, str, str]]]:
    """Execute services for all clusters.

    Args:
        cluster_names: List of cluster names
        services: Dictionary of service configurations
        kubeconfig_path: Path to the kubeconfig directory
        log_output: Whether to log the command output to the log file

    Returns:
        Dictionary mapping cluster names to their service execution results
    """
    logger = get_logger()
    all_results = {}

    if not services:
        logger.info("No services configured, skipping service execution")
        return all_results

    logger.info(f"Executing services for {len(cluster_names)} clusters")

    for cluster_name in cluster_names:
        kubeconfig_file = Path(kubeconfig_path) / f"{cluster_name}.kubeconfig"

        if not kubeconfig_file.exists():
            logger.warning(f"Kubeconfig file not found for cluster '{cluster_name}', skipping services")
            all_results[cluster_name] = []
            continue

        cluster_results = execute_services_for_cluster(cluster_name, services, kubeconfig_file, log_output)
        all_results[cluster_name] = cluster_results

    return all_results


def create_clusters_with_services(
    config,
    dry_run: bool = False,
    use_queue: bool = True,
    max_workers: Optional[int] = None,
    load_balancer_strategy: str = "round_robin",
) -> Tuple[bool, List[str]]:
    """Create clusters and execute services using the queue system.

    Args:
        config: Deployment configuration
        dry_run: If True, only show what would be done without executing
        use_queue: If True, use queue system for service execution
        max_workers: Maximum number of workers for service execution
        load_balancer_strategy: Load balancing strategy for service execution

    Returns:
        Tuple of (success, list of created cluster names)
    """
    logger = get_logger()

    if dry_run:
        logger.info("DRY RUN: Would create clusters and execute services")
        cluster_names = config.get_cluster_names()
        logger.info(f"Would create clusters: {cluster_names}")
        return True, cluster_names

    # Get cluster names from config
    cluster_names = get_cluster_names(config)
    if not cluster_names:
        logger.warning("No clusters to create")
        return True, []

    logger.info(f"Creating {len(cluster_names)} clusters with queue-based service execution")

    # Create clusters first (using existing parallel logic)
    cluster_results = {}
    cluster_results = create_multiple_clusters(
        config, log_output=True, max_workers=config[Config.GENERAL.value][Config.MAX_WORKERS.value]
    )

    # Check if any clusters were created successfully
    successful_clusters = [name for name, success in cluster_results.items() if success]
    if not successful_clusters:
        logger.error("No clusters were created successfully")
        return False, []

    logger.info(f"Successfully created {len(successful_clusters)} clusters: {successful_clusters}")

    # Execute services using queue system if requested
    if use_queue and successful_clusters:
        service_success = execute_services_from_queue(
            config,
            successful_clusters,
            max_workers=max_workers or config[Config.GENERAL.value][Config.MAX_WORKERS.value],
            load_balancer_strategy=load_balancer_strategy,
        )

        if not service_success:
            logger.warning("Some services failed to execute, but clusters were created successfully")

    return True, successful_clusters


def execute_services_from_queue(
    config,
    cluster_names: List[str],
    max_workers: int = 4,
    load_balancer_strategy: str = "round_robin",
) -> bool:
    """Execute services using the queue system.

    Args:
        config: Deployment configuration
        cluster_names: List of cluster names to execute services for
        max_workers: Maximum number of workers for service execution
        load_balancer_strategy: Load balancing strategy for service execution

    Returns:
        True if all services executed successfully, False otherwise
    """
    logger = get_logger()

    # Create execution planner
    planner = ExecutionPlanner(config)

    # Create execution plan
    try:
        execution_plan = planner.create_execution_plan()
        logger.info(f"Created execution plan with {len(execution_plan)} service items")

        # Filter execution plan to only include the specified clusters
        filtered_plan = [item for item in execution_plan if item.cluster_name in cluster_names]

        if not filtered_plan:
            logger.info("No services to execute for the specified clusters")
            return True

        logger.info(f"Executing {len(filtered_plan)} service items for {len(cluster_names)} clusters")

    except Exception as e:
        logger.error(f"Failed to create execution plan: {e}")
        return False

    # Create service queue
    queue = ServiceQueue(max_workers=max_workers)

    # Create load balancer
    try:
        load_balancer = create_load_balancer(load_balancer_strategy)
        logger.info(f"Using load balancer: {load_balancer_strategy}")
    except ValueError as e:
        logger.error(f"Invalid load balancer strategy: {e}")
        return False

    # Add service items to queue
    for item in filtered_plan:
        queue.add_service_item(item)

    # Create and start worker pool
    worker_pool = WorkerPool(max_workers=max_workers, queue=queue)
    queue.workers = worker_pool.workers  # Link workers to queue

    try:
        # Start workers
        worker_pool.start_workers()
        logger.info(f"Started {max_workers} workers for service execution")

        # Wait for all services to complete
        while not queue.is_empty():
            time.sleep(0.1)  # Small delay to avoid busy waiting

        # Get final status
        status = queue.get_queue_status()
        logger.info(
            f"Service execution completed: {status['completed_count']} completed, {status['failed_count']} failed"
        )

        # Check if all services completed successfully
        all_successful = status["failed_count"] == 0

        if all_successful:
            logger.info("All services executed successfully")
        else:
            logger.warning(f"{status['failed_count']} services failed to execute")

        return all_successful

    except Exception as e:
        logger.error(f"Error during service execution: {e}")
        return False

    finally:
        # Clean up workers
        worker_pool.stop_workers()
        queue.shutdown()


def get_execution_plan(
    config,
    cluster_names: Optional[List[str]] = None,
    show_timeline: bool = False,
    show_dependencies: bool = False,
) -> Dict[str, any]:
    """Get execution plan for services.

    Args:
        config: Deployment configuration
        cluster_names: Optional list of cluster names to filter by
        show_timeline: Whether to include timeline information
        show_dependencies: Whether to include dependency information

    Returns:
        Dictionary containing execution plan information
    """
    logger = get_logger()

    # Create execution planner
    planner = ExecutionPlanner(config)

    try:
        # Create execution plan
        execution_plan = planner.create_execution_plan()

        # Filter by cluster names if specified
        if cluster_names:
            execution_plan = [item for item in execution_plan if item.cluster_name in cluster_names]

        # Build result
        result = {
            "total_services": len(execution_plan),
            "clusters": list(set(item.cluster_name for item in execution_plan)),
            "cluster_types": list(set(item.cluster_type for item in execution_plan)),
            "services": [
                {
                    "cluster_name": item.cluster_name,
                    "cluster_type": item.cluster_type,
                    "service_name": item.service_name,
                    "priority": item.priority,
                    "estimated_duration": item.estimated_duration,
                    "dependencies": item.dependencies,
                }
                for item in execution_plan
            ],
        }

        # Add timeline if requested
        if show_timeline:
            result["timeline"] = planner.get_execution_timeline()

        # Add dependencies if requested
        if show_dependencies:
            result["dependencies"] = planner.calculate_dependencies()

        # Add execution summary
        result["summary"] = planner.get_execution_summary()

        return result

    except Exception as e:
        logger.error(f"Failed to create execution plan: {e}")
        return {"error": str(e), "total_services": 0, "clusters": [], "cluster_types": [], "services": []}
