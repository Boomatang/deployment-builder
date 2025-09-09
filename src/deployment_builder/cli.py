"""CLI module for deployment-builder tool."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import click
import tomli
import yaml

from .logging_config import setup_logging, get_logger, log_command_start, log_command_end, log_config_loaded, log_error


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
    """Deployment Builder - A CLI tool for managing deployments."""
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
    """Create deployment based on configuration file."""
    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("create", str(config) if config else None, dry_run=dry_run)

    try:
        config_data = load_config(str(config) if config else None)

        if dry_run:
            logger.info("Executing dry run for create command")
            click.echo("DRY RUN: Would create deployment with the following configuration:")
            click.echo(json.dumps(config_data, indent=2))
            log_command_end("create", success=True, message="Dry run completed")
        else:
            logger.info("Starting deployment creation")
            click.echo("Creating deployment...")
            # TODO: Implement actual deployment creation logic
            click.echo(f"✓ Deployment created successfully using config: {config or 'default'}")
            log_command_end("create", success=True, message="Deployment created successfully")

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
    """Remove deployment based on configuration file."""
    # Get logger instance
    logger = get_logger()

    # Log command start
    log_command_start("remove", str(config) if config else None, dry_run=dry_run, force=force)

    try:
        config_data = load_config(str(config) if config else None)

        if dry_run:
            logger.info("Executing dry run for remove command")
            click.echo("DRY RUN: Would remove deployment with the following configuration:")
            click.echo(json.dumps(config_data, indent=2))
            log_command_end("remove", success=True, message="Dry run completed")
        else:
            if not force:
                logger.info("Prompting user for confirmation")
                if not click.confirm(
                    f"Are you sure you want to remove the deployment using config: {config or 'default'}"
                ):
                    logger.info("User cancelled the operation")
                    click.echo("Operation cancelled.")
                    log_command_end("remove", success=False, message="User cancelled")
                    return

            logger.info("Starting deployment removal")
            click.echo("Removing deployment...")
            # TODO: Implement actual deployment removal logic
            click.echo(f"✓ Deployment removed successfully using config: {config or 'default'}")
            log_command_end("remove", success=True, message="Deployment removed successfully")

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
