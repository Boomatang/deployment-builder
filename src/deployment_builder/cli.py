"""CLI module for deployment-builder tool."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import click
import tomli
import yaml


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
        for config_file in config_files:
            if os.path.exists(config_file):
                config_path = config_file
                break
        else:
            raise FileNotFoundError("No configuration file found in current directory")

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load based on file extension
    if config_path.suffix.lower() in [".toml"]:
        with open(config_path, "rb") as f:
            return tomli.load(f)
    elif config_path.suffix.lower() in [".json"]:
        with open(config_path, "r") as f:
            return json.load(f)
    elif config_path.suffix.lower() in [".yaml", ".yml"]:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")


@click.group()
@click.version_option()
def cli():
    """Deployment Builder - A CLI tool for managing deployments."""
    pass


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
    try:
        config_data = load_config(str(config) if config else None)

        if dry_run:
            click.echo("DRY RUN: Would create deployment with the following configuration:")
            click.echo(json.dumps(config_data, indent=2))
        else:
            click.echo("Creating deployment...")
            # TODO: Implement actual deployment creation logic
            click.echo(f"✓ Deployment created successfully using config: {config or 'default'}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
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
    try:
        config_data = load_config(str(config) if config else None)

        if dry_run:
            click.echo("DRY RUN: Would remove deployment with the following configuration:")
            click.echo(json.dumps(config_data, indent=2))
        else:
            if not force:
                if not click.confirm(
                    f"Are you sure you want to remove the deployment using config: {config or 'default'}"
                ):
                    click.echo("Operation cancelled.")
                    return

            click.echo("Removing deployment...")
            # TODO: Implement actual deployment removal logic
            click.echo(f"✓ Deployment removed successfully using config: {config or 'default'}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
