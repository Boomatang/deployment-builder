"""CLI module for deployment-builder tool."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import click
import tomli
import yaml

from .logging_config import (
    setup_logging,
    get_logger,
    log_command_start,
    log_command_end,
    log_config_loaded,
    log_error,
    log_timing_report,
)
from .kind_integration import (
    create_cluster,
    delete_cluster,
    create_multiple_clusters,
    delete_multiple_clusters,
    check_kind_available,
    get_cluster_name_from_config,
    get_cluster_names_from_config,
    create_clusters_with_services,
    get_execution_plan,
)


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
        if config_path.suffix.lower() in [".toml"]:
            with open(config_path, "rb") as f:
                config_data = tomli.load(f)
        elif config_path.suffix.lower() in [".json"]:
            with open(config_path, "r") as f:
                config_data = json.load(f)
        elif config_path.suffix.lower() in [".yaml", ".yml"]:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
        else:
            logger.error(f"Unsupported configuration file format: {config_path.suffix}")
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")

        # Note: [general] section handling is now done in the DeploymentConfig object

        log_config_loaded(config_data, str(config_path))
        return config_data

    except Exception as e:
        log_error(e, f"loading configuration from {config_path}")
        raise


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the logging level for the tool.",
)
@click.version_option()
def cli(log_level: str):
    """Deployment Builder - A CLI tool for managing kind Kubernetes clusters with dynamic cluster types.

    This tool supports creating and managing multiple kind clusters based on configuration files.
    You can define any cluster types you need for your specific use case, with support for both
    single clusters (enable: true/false) and multiple clusters (count: number).

    Examples:
        # Create clusters from configuration
        deploy create --config my-config.toml

        # Preview what would be created
        deploy create --dry-run

        # Show default configuration values
        deploy defaults
    """
    # Set up logging with the specified level
    setup_logging(log_level=log_level)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    envvar="DEPLOYMENT_CONFIG",
    help="Path to configuration file. If not provided, looks for config files in current directory. Can also be set via DEPLOYMENT_CONFIG environment variable.",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would be created without actually creating it.",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    help="Number of workers for parallel service execution. Overrides config value.",
)
@click.option(
    "--load-balancer",
    type=click.Choice(["round_robin", "least_loaded", "priority_based"], case_sensitive=False),
    help="Load balancing strategy for service execution. Overrides config value.",
)
def create(config: Optional[Path], dry_run: bool, workers: Optional[int], load_balancer: Optional[str]):
    """Create kind clusters based on configuration file.

    This command creates multiple kind clusters according to your configuration file.
    You can define any cluster types you need with dynamic cluster type support.

    Configuration supports:
    - Single clusters: [clusters.my-cluster] with enable = true
    - Multiple clusters: [clusters.my-cluster] with count = 3
    - Global services: [services] section for all clusters
    - Cluster-specific services: [clusters.my-cluster.services] section

    Examples:
        # Create clusters from config file
        deploy create --config my-config.toml

        # Preview what would be created
        deploy create --dry-run

        # Use environment variable for config
        DEPLOYMENT_CONFIG=my-config.yaml deploy create
    """
    import time

    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("create", str(config) if config else None, dry_run=dry_run)

    try:
        from .config import load_config_from_file

        # Load configuration using the new configuration object
        config_obj = load_config_from_file(str(config) if config else None)

        # Extract cluster names from configuration object
        cluster_names = config_obj.get_cluster_names()
        logger.info(f"Will create {len(cluster_names)} clusters: {cluster_names}")

        if dry_run:
            logger.info("Executing dry run for create command")
            click.echo("DRY RUN: Would create kind clusters with the following configuration:")
            click.echo(json.dumps(config_obj.to_dict(), indent=2))
            click.echo(f"Clusters to create: {', '.join(cluster_names)}")

            # Show execution plan if services are configured
            if (
                any(len(cluster_config.services) > 0 for cluster_config in config_obj.clusters.values())
                or len(config_obj.services) > 0
            ):
                click.echo("\nExecution Plan:")
                click.echo("=" * 50)
                plan_result = get_execution_plan(config_obj, show_timeline=True, show_dependencies=True)
                if "error" not in plan_result:
                    click.echo(f"Total services: {plan_result['total_services']}")
                    click.echo(f"Clusters: {', '.join(plan_result['clusters'])}")
                    click.echo(f"Cluster types: {', '.join(plan_result['cluster_types'])}")
                    if plan_result["summary"]:
                        summary = plan_result["summary"]
                        click.echo(f"Estimated duration: {summary['estimated_duration']:.1f} seconds")
                        click.echo(f"Parallel groups: {summary['parallel_groups']}")
                        click.echo(f"Max workers: {summary['max_workers']}")
                else:
                    click.echo(f"Error generating execution plan: {plan_result['error']}")

            log_command_end("create", success=True, message="Dry run completed")
            # Log timing report for dry run
            duration_str = log_timing_report(start_time, "create", success=True, cluster_count=len(cluster_names))
            click.echo(f"⏱️  Total execution time: {duration_str}")
        else:
            # Check if kind is available
            if not check_kind_available():
                click.echo("Error: kind CLI is not available. Please install kind first.", err=True)
                click.echo("Visit: https://kind.sigs.k8s.io/", err=True)
                log_command_end("create", success=False, message="kind CLI not available")
                raise click.Abort()

            logger.info("Starting kind cluster creation with queue-based service execution")
            click.echo(f"Creating {len(cluster_names)} kind clusters with parallel service execution...")

            # Use queue-based cluster creation
            success, created_clusters = create_clusters_with_services(
                config_obj,
                dry_run=False,
                use_queue=True,
                max_workers=workers,
                load_balancer_strategy=load_balancer or "round_robin",
            )

            if success and created_clusters:
                click.echo(f"✓ Successfully created {len(created_clusters)} clusters: {', '.join(created_clusters)}")
                log_command_end(
                    "create", success=True, message=f"All {len(created_clusters)} clusters created successfully"
                )
                # Log timing report
                duration_str = log_timing_report(
                    start_time, "create", success=True, cluster_count=len(created_clusters)
                )
                click.echo(f"⏱️  Total execution time: {duration_str}")
            else:
                click.echo("✗ Failed to create clusters", err=True)
                log_command_end("create", success=False, message="Failed to create clusters")
                # Log timing report
                duration_str = log_timing_report(start_time, "create", success=False, cluster_count=len(cluster_names))
                click.echo(f"⏱️  Total execution time: {duration_str}")
                raise click.Abort()

    except FileNotFoundError as e:
        log_error(e, "create command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("create", success=False, message=f"File not found: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "create", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()
    except ValueError as e:
        log_error(e, "create command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("create", success=False, message=f"Invalid value: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "create", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()
    except Exception as e:
        log_error(e, "create command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("create", success=False, message=f"Unexpected error: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "create", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    envvar="DEPLOYMENT_CONFIG",
    help="Path to configuration file. If not provided, looks for config files in current directory. Can also be set via DEPLOYMENT_CONFIG environment variable.",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would be removed without actually removing it.",
)
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation.")
def remove(config: Optional[Path], dry_run: bool, force: bool):
    """Remove kind clusters based on configuration file.

    This command removes multiple kind clusters according to your configuration file.
    It will remove all clusters defined in your configuration, including dynamic cluster types.

    Examples:
        # Remove clusters from config file
        deploy remove --config my-config.toml

        # Preview what would be removed
        deploy remove --dry-run

        # Force removal without confirmation
        deploy remove --force
    """
    import time

    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("remove", str(config) if config else None, dry_run=dry_run, force=force)

    try:
        from .config import load_config_from_file

        # Load configuration using the new configuration object
        config_obj = load_config_from_file(str(config) if config else None)

        # Extract cluster names from configuration object
        cluster_names = config_obj.get_cluster_names()
        logger.info(f"Will remove {len(cluster_names)} clusters: {cluster_names}")

        if dry_run:
            logger.info("Executing dry run for remove command")
            click.echo("DRY RUN: Would remove kind clusters with the following configuration:")
            click.echo(json.dumps(config_obj.to_dict(), indent=2))
            click.echo(f"Clusters to remove: {', '.join(cluster_names)}")
            log_command_end("remove", success=True, message="Dry run completed")
            # Log timing report for dry run
            duration_str = log_timing_report(start_time, "remove", success=True, cluster_count=len(cluster_names))
            click.echo(f"⏱️  Total execution time: {duration_str}")
        else:
            if not force:
                logger.info("Prompting user for confirmation")
                if not click.confirm(
                    f"Are you sure you want to remove {len(cluster_names)} kind clusters: {', '.join(cluster_names)}?"
                ):
                    logger.info("User cancelled the operation")
                    click.echo("Operation cancelled.")
                    log_command_end("remove", success=False, message="User cancelled")
                    return

            # Check if kind is available
            if not check_kind_available():
                click.echo("Error: kind CLI is not available. Please install kind first.", err=True)
                click.echo("Visit: https://kind.sigs.k8s.io/", err=True)
                log_command_end("remove", success=False, message="kind CLI not available")
                raise click.Abort()

            logger.info("Starting kind cluster removal")
            click.echo(f"Removing {len(cluster_names)} kind clusters in parallel...")

            # Determine if we should log kind output (debug level)
            log_kind_output = logger.level <= 10  # DEBUG level

            # Delete the clusters
            results = delete_multiple_clusters(
                config_obj.to_dict(), log_output=log_kind_output, max_workers=config_obj.general.max_workers
            )

            # Report results
            successful = [name for name, success in results.items() if success]
            failed = [name for name, success in results.items() if not success]

            if successful:
                click.echo(f"✓ Successfully removed {len(successful)} clusters: {', '.join(successful)}")

            if failed:
                click.echo(f"✗ Failed to remove {len(failed)} clusters: {', '.join(failed)}", err=True)

            if failed:
                log_command_end("remove", success=False, message=f"Failed to remove {len(failed)} clusters")
                # Log timing report
                duration_str = log_timing_report(start_time, "remove", success=False, cluster_count=len(cluster_names))
                click.echo(f"⏱️  Total execution time: {duration_str}")
                raise click.Abort()
            else:
                log_command_end("remove", success=True, message=f"All {len(successful)} clusters removed successfully")
                # Log timing report
                duration_str = log_timing_report(start_time, "remove", success=True, cluster_count=len(successful))
                click.echo(f"⏱️  Total execution time: {duration_str}")

    except FileNotFoundError as e:
        log_error(e, "remove command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("remove", success=False, message=f"File not found: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "remove", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()
    except ValueError as e:
        log_error(e, "remove command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("remove", success=False, message=f"Invalid value: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "remove", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()
    except Exception as e:
        log_error(e, "remove command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("remove", success=False, message=f"Unexpected error: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "remove", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    envvar="DEPLOYMENT_CONFIG",
    help="Path to configuration file. If not provided, looks for config files in current directory. Can also be set via DEPLOYMENT_CONFIG environment variable.",
)
@click.option(
    "--timeline",
    "-t",
    is_flag=True,
    help="Show detailed execution timeline with start/end times.",
)
@click.option(
    "--dependencies",
    "-d",
    is_flag=True,
    help="Show service dependencies and relationships.",
)
@click.option(
    "--cluster-types",
    help="Filter by specific cluster types (comma-separated).",
)
def plan(config: Optional[Path], timeline: bool, dependencies: bool, cluster_types: Optional[str]):
    """Show execution plan for services without creating clusters.

    This command analyzes your configuration and shows how services would be executed
    using the queue system, including execution order, dependencies, and timeline.

    Examples:
        # Show basic execution plan
        deploy plan --config my-config.toml

        # Show detailed timeline
        deploy plan --config my-config.toml --timeline

        # Show dependencies
        deploy plan --config my-config.toml --dependencies

        # Filter by cluster types
        deploy plan --config my-config.toml --cluster-types worker,database
    """
    import time

    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("plan", str(config) if config else None, timeline=timeline, dependencies=dependencies)

    try:
        from .config import load_config_from_file

        # Load configuration using the new configuration object
        config_obj = load_config_from_file(str(config) if config else None)

        # Parse cluster types filter
        cluster_type_filter = None
        if cluster_types:
            cluster_type_filter = [ct.strip() for ct in cluster_types.split(",")]
            logger.info(f"Filtering by cluster types: {cluster_type_filter}")

        # Get execution plan
        logger.info("Generating execution plan")
        plan_result = get_execution_plan(
            config_obj, cluster_names=None, show_timeline=timeline, show_dependencies=dependencies  # Show all clusters
        )

        if "error" in plan_result:
            click.echo(f"Error generating execution plan: {plan_result['error']}", err=True)
            log_command_end("plan", success=False, message=f"Error: {plan_result['error']}")
            raise click.Abort()

        # Filter by cluster types if specified
        if cluster_type_filter:
            filtered_services = [
                service for service in plan_result["services"] if service["cluster_type"] in cluster_type_filter
            ]
            plan_result["services"] = filtered_services
            plan_result["total_services"] = len(filtered_services)
            plan_result["clusters"] = list(set(service["cluster_name"] for service in filtered_services))
            plan_result["cluster_types"] = list(set(service["cluster_type"] for service in filtered_services))

        # Display execution plan
        click.echo("Execution Plan")
        click.echo("=" * 50)
        click.echo(f"Total services: {plan_result['total_services']}")
        click.echo(f"Clusters: {', '.join(plan_result['clusters'])}")
        click.echo(f"Cluster types: {', '.join(plan_result['cluster_types'])}")

        if plan_result["summary"]:
            summary = plan_result["summary"]
            click.echo(f"Estimated duration: {summary['estimated_duration']:.1f} seconds")
            click.echo(f"Parallel groups: {summary['parallel_groups']}")
            click.echo(f"Max workers: {summary['max_workers']}")

        # Show services
        if plan_result["services"]:
            click.echo("\nServices:")
            click.echo("-" * 30)
            for service in plan_result["services"]:
                deps_str = f" (depends on: {', '.join(service['dependencies'])})" if service["dependencies"] else ""
                click.echo(
                    f"  {service['cluster_name']}: {service['service_name']} (priority: {service['priority']}, duration: {service['estimated_duration']:.1f}s){deps_str}"
                )

        # Show timeline if requested
        if timeline and "timeline" in plan_result:
            click.echo("\nExecution Timeline:")
            click.echo("-" * 30)
            for item in plan_result["timeline"]:
                click.echo(f"  {item['service_name']} on {item['cluster_name']}:")
                click.echo(f"    Start: {item['estimated_start']}")
                click.echo(f"    End: {item['estimated_end']}")
                click.echo(f"    Duration: {item['estimated_duration']:.1f}s")
                click.echo()

        # Show dependencies if requested
        if dependencies and "dependencies" in plan_result:
            click.echo("\nService Dependencies:")
            click.echo("-" * 30)
            for service_key, deps in plan_result["dependencies"].items():
                if deps:
                    click.echo(f"  {service_key} depends on: {', '.join(deps)}")
                else:
                    click.echo(f"  {service_key} has no dependencies")

        logger.info("Successfully displayed execution plan")
        log_command_end("plan", success=True)
        duration_str = log_timing_report(start_time, "plan", success=True)
        click.echo(f"\n⏱️  Total execution time: {duration_str}")

    except FileNotFoundError as e:
        log_error(e, "plan command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("plan", success=False, message=f"File not found: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "plan", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()
    except ValueError as e:
        log_error(e, "plan command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("plan", success=False, message=f"Invalid value: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "plan", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()
    except Exception as e:
        log_error(e, "plan command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("plan", success=False, message=f"Unexpected error: {e}")
        # Log timing report for error
        duration_str = log_timing_report(start_time, "plan", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()


@cli.command()
def defaults():
    """Show the default configuration values used by the tool.

    This command displays all default configuration values in a dot-separated format.
    Note that cluster types are defined dynamically in your configuration file - there
    are no default cluster types. You define exactly the cluster types you need.

    Examples:
        # Show all default values
        deploy defaults

        # Show defaults with debug logging
        deploy --log-level=debug defaults
    """
    import time

    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("defaults", None)

    try:
        from .config import create_default_config

        # Create default configuration
        logger.info("Creating default configuration object")
        default_config = create_default_config()

        # Display default values in dot-separated format
        logger.info("Displaying default configuration values")
        click.echo("Default Configuration Values:")
        click.echo("=" * 50)

        def format_config_dict(data, prefix=""):
            """Recursively format configuration dictionary with dot notation."""
            lines = []
            for key, value in data.items():
                current_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    lines.extend(format_config_dict(value, current_key))
                else:
                    lines.append(f"{current_key} = {value}")
            return lines

        # Format and display the configuration
        config_dict = default_config.to_dict()
        formatted_lines = format_config_dict(config_dict)
        logger.debug(f"Formatted {len(formatted_lines)} configuration lines")

        for line in sorted(formatted_lines):
            click.echo(line)

        logger.info("Successfully displayed default configuration values")
        log_command_end("defaults", success=True)
        duration_str = log_timing_report(start_time, "defaults", success=True)

    except Exception as e:
        log_error(e, "displaying default configuration values")
        log_command_end("defaults", success=False)
        duration_str = log_timing_report(start_time, "defaults", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
