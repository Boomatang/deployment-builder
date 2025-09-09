"""CLI module for deployment-builder tool."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import click
import tomli
import yaml

from .logging_config import setup_logging, get_logger, log_command_start, log_command_end, log_config_loaded, log_error
from .kind_integration import create_cluster, delete_cluster, check_kind_available, get_cluster_name_from_config


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
    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("create", str(config) if config else None, dry_run=dry_run)

    try:
        config_data = load_config(str(config) if config else None)

        # Extract cluster name from configuration
        cluster_name = get_cluster_name_from_config(config_data)
        logger.info(f"Using cluster name: {cluster_name}")

        if dry_run:
            logger.info("Executing dry run for create command")
            click.echo("DRY RUN: Would create kind cluster with the following configuration:")
            click.echo(json.dumps(config_data, indent=2))
            click.echo(f"Cluster name: {cluster_name}")
            log_command_end("create", success=True, message="Dry run completed")
        else:
            # Check if kind is available
            if not check_kind_available():
                click.echo("Error: kind CLI is not available. Please install kind first.", err=True)
                click.echo("Visit: https://kind.sigs.k8s.io/", err=True)
                log_command_end("create", success=False, message="kind CLI not available")
                raise click.Abort()

            logger.info("Starting kind cluster creation")
            click.echo(f"Creating kind cluster '{cluster_name}'...")

            # Determine if we should log kind output (debug level)
            log_kind_output = logger.level <= 10  # DEBUG level

            # Create the cluster
            success = create_cluster(cluster_name, log_output=log_kind_output)

            if success:
                click.echo(f"✓ Kind cluster '{cluster_name}' created successfully")
                log_command_end("create", success=True, message=f"Cluster '{cluster_name}' created successfully")
            else:
                click.echo(f"✗ Failed to create kind cluster '{cluster_name}'", err=True)
                log_command_end("create", success=False, message=f"Failed to create cluster '{cluster_name}'")
                raise click.Abort()

    except FileNotFoundError as e:
        log_error(e, "create command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("create", success=False, message=f"File not found: {e}")
        raise click.Abort()
    except ValueError as e:
        log_error(e, "create command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("create", success=False, message=f"Invalid value: {e}")
        raise click.Abort()
    except Exception as e:
        log_error(e, "create command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("create", success=False, message=f"Unexpected error: {e}")
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
    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("remove", str(config) if config else None, dry_run=dry_run, force=force)

    try:
        config_data = load_config(str(config) if config else None)

        # Extract cluster name from configuration
        cluster_name = get_cluster_name_from_config(config_data)
        logger.info(f"Using cluster name: {cluster_name}")

        if dry_run:
            logger.info("Executing dry run for remove command")
            click.echo("DRY RUN: Would remove kind cluster with the following configuration:")
            click.echo(json.dumps(config_data, indent=2))
            click.echo(f"Cluster name: {cluster_name}")
            log_command_end("remove", success=True, message="Dry run completed")
        else:
            if not force:
                logger.info("Prompting user for confirmation")
                if not click.confirm(f"Are you sure you want to remove the kind cluster '{cluster_name}'?"):
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
            click.echo(f"Removing kind cluster '{cluster_name}'...")

            # Determine if we should log kind output (debug level)
            log_kind_output = logger.level <= 10  # DEBUG level

            # Delete the cluster
            success = delete_cluster(cluster_name, log_output=log_kind_output)

            if success:
                click.echo(f"✓ Kind cluster '{cluster_name}' removed successfully")
                log_command_end("remove", success=True, message=f"Cluster '{cluster_name}' removed successfully")
            else:
                click.echo(f"✗ Failed to remove kind cluster '{cluster_name}'", err=True)
                log_command_end("remove", success=False, message=f"Failed to remove cluster '{cluster_name}'")
                raise click.Abort()

    except FileNotFoundError as e:
        log_error(e, "remove command - file not found")
        click.echo(f"Error: {e}", err=True)
        log_command_end("remove", success=False, message=f"File not found: {e}")
        raise click.Abort()
    except ValueError as e:
        log_error(e, "remove command - invalid value")
        click.echo(f"Error: {e}", err=True)
        log_command_end("remove", success=False, message=f"Invalid value: {e}")
        raise click.Abort()
    except Exception as e:
        log_error(e, "remove command - unexpected error")
        click.echo(f"Unexpected error: {e}", err=True)
        log_command_end("remove", success=False, message=f"Unexpected error: {e}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
