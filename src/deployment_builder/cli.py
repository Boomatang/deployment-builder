"""CLI module for deployment-builder tool."""

import multiprocessing as mp
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.prompt import Confirm

from deployment_builder import tui
from deployment_builder.config import default_config, load_config_from_file
from deployment_builder.kind import Kind
from deployment_builder.logging_config import (
    get_logger,
    log_command_end,
    log_command_start,
    log_error,
    log_timing_report,
    setup_logging,
)
from deployment_builder.plan import Plan, cluster_create_worker, cluster_delete_worker, service_worker


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
def create(config: Optional[Path], dry_run: bool):
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

    # Start timing
    start_time = time.time()

    # Log command start
    log_command_start("create", str(config) if config else None, dry_run=dry_run)

    success = True
    try:
        console = Console()
        console.print("Loading configuration")
        config_obj = load_config_from_file(str(config) if config else None)

        console.print("Building execution plan")
        engine = Kind()
        plan = Plan(config_obj, engine)

        ## Creation of the clusters
        cluster_queue = plan.cluster_queue()
        result_queue = mp.Queue()
        size = cluster_queue.qsize()

        if dry_run:
            console.print("Running dry run mode...")
            console.print("Following plan would be created")
            display = plan.as_text()
            for item in display:
                console.print(item)
            return

        processes = []
        for i in range(plan.workers):
            p = mp.Process(target=cluster_create_worker, args=(cluster_queue, result_queue, i))
            p.start()
            processes.append(p)

        tui.cluster_create(size, result_queue)

        for p in processes:
            p.join()

        ## Running of the cluster services
        services = plan.services_queue()
        result_queue = mp.Queue()
        size = services.qsize()

        processes = []
        for i in range(plan.workers):
            p = mp.Process(target=service_worker, args=(services, result_queue, i))
            p.start()
            processes.append(p)

        tui.service_run(size, result_queue)

        for p in processes:
            p.join()

    except FileNotFoundError as e:
        log_error(e, "create command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("create", success=False, message=f"File not found: {e}")
        success = False
    except ValueError as e:
        log_error(e, "create command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("create", success=False, message=f"Invalid value: {e}")
        success = False
    except Exception as e:
        log_error(e, "create command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("create", success=False, message=f"Unexpected error: {e}")
        success = False
    finally:
        duration_str = log_timing_report(start_time, "create", success=success)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        if not success:
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
    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("remove", str(config) if config else None, dry_run=dry_run, force=force)
    success = True

    try:
        console = Console()
        console.print("Loading configuration")
        config_obj = load_config_from_file(str(config) if config else None)

        console.print("Building execution plan")
        engine = Kind()
        plan = Plan(config_obj, engine)

        ## Creation of the clusters
        cluster_queue = plan.cluster_queue()
        result_queue = mp.Queue()
        size = cluster_queue.qsize()

        if dry_run:
            console.print("Running dry run mode...")
            console.print("Deleting clusters")
            for cluster in plan.cluster_names():
                console.print(f"\t{cluster}")
            return

        if not force:
            logger.info("Prompting user for confirmation")
            if not Confirm.ask(
                f"Are you sure you want to remove {plan.cluster_count()} kind clusters: {", ".join(plan.cluster_names())}?"
            ):
                logger.info("User cancelled the operation")
                console.print("[red]Operation cancelled.")
                log_command_end("remove", success=False, message="User cancelled")
                return

        # BUG: when the number of works is more that one.
        # The updating of kubeconfig can hit deadlocks.
        if plan.workers > 1:
            logger.warn("Updates to kubeconfig can cause lock errors, due to multi updates from kind")
        processes = []
        for i in range(plan.workers):
            p = mp.Process(target=cluster_delete_worker, args=(cluster_queue, result_queue, i))
            p.start()
            processes.append(p)

        tui.cluster_delete(size, result_queue)

        for p in processes:
            p.join()

    except FileNotFoundError as e:
        log_error(e, "remove command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("remove", success=False, message=f"File not found: {e}")
        success = False
    except ValueError as e:
        log_error(e, "remove command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("remove", success=False, message=f"Invalid value: {e}")
        success = False
    except Exception as e:
        log_error(e, "remove command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("remove", success=False, message=f"Unexpected error: {e}")
        success = False
    finally:
        duration_str = log_timing_report(start_time, "remove", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        if not success:
            raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    envvar="DEPLOYMENT_CONFIG",
    help="Path to configuration file. If not provided, looks for config files in current directory. Can also be set via DEPLOYMENT_CONFIG environment variable.",
)
def plan(config: Optional[Path]):
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
    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()
    success = True

    # Log command start
    log_command_start("plan", str(config) if config else None)

    try:
        console = Console()
        logger.info("Loading configuration")
        config_obj = load_config_from_file(str(config) if config else None)

        logger.info("Building execution plan")
        plan = Plan(config_obj, None)
        display = plan.as_text()
        for item in display:
            console.print(item)
        logger.info("Successfully displayed execution plan")
        log_command_end("plan", success=True)

    except FileNotFoundError as e:
        log_error(e, "plan command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("plan", success=False, message=f"File not found: {e}")
        success = False
    except ValueError as e:
        log_error(e, "plan command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("plan", success=False, message=f"Invalid value: {e}")
        success = False
    except Exception as e:
        log_error(e, "plan command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("plan", success=False, message=f"Unexpected error: {e}")
        success = False
    finally:
        duration_str = log_timing_report(start_time, "plan", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        if not success:
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
    # Start timing
    start_time = time.time()

    # Get logger instance
    logger = get_logger()
    success = True

    # Log command start
    log_command_start("defaults", None)

    try:
        console = Console()

        # Create default configuration
        logger.info("Creating default configuration object")

        # Display default values in dot-separated format
        logger.info("Displaying default configuration values")
        console.print("Default Configuration Values:")
        console.print("=" * 50)

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
        formatted_lines = format_config_dict(default_config)
        logger.debug(f"Formatted {len(formatted_lines)} configuration lines")

        for line in sorted(formatted_lines):
            console.print(line)

        logger.info("Successfully displayed default configuration values")
        log_command_end("defaults", success=True)

    except Exception as e:
        log_error(e, "displaying default configuration values")
        log_command_end("defaults", success=False)
        success = False
    finally:
        duration_str = log_timing_report(start_time, "defaults", success=False)
        click.echo(f"⏱️  Total execution time: {duration_str}")
        if not success:
            raise click.Abort()


if __name__ == "__main__":
    cli()
