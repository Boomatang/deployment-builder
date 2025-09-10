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
    """Deployment Builder - A CLI tool for managing kind Kubernetes clusters."""
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
    """Create kind cluster based on configuration file."""
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

            logger.info("Starting kind cluster creation")
            click.echo(f"Creating {len(cluster_names)} kind clusters in parallel...")

            # Determine if we should log kind output (debug level)
            log_kind_output = logger.level <= 10  # DEBUG level

            # Create the clusters
            results = create_multiple_clusters(
                config_obj.to_dict(), log_output=log_kind_output, max_workers=config_obj.general.max_workers
            )

            # Report results
            successful = [name for name, success in results.items() if success]
            failed = [name for name, success in results.items() if not success]

            if successful:
                click.echo(f"✓ Successfully created {len(successful)} clusters: {', '.join(successful)}")

            if failed:
                click.echo(f"✗ Failed to create {len(failed)} clusters: {', '.join(failed)}", err=True)

            if failed:
                log_command_end("create", success=False, message=f"Failed to create {len(failed)} clusters")
                # Log timing report
                duration_str = log_timing_report(start_time, "create", success=False, cluster_count=len(cluster_names))
                click.echo(f"⏱️  Total execution time: {duration_str}")
                raise click.Abort()
            else:
                log_command_end("create", success=True, message=f"All {len(successful)} clusters created successfully")
                # Log timing report
                duration_str = log_timing_report(start_time, "create", success=True, cluster_count=len(successful))
                click.echo(f"⏱️  Total execution time: {duration_str}")

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
    """Remove kind cluster based on configuration file."""
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
def defaults():
    """Show the default configuration values used by the tool."""
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
