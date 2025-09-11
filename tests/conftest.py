"""Shared pytest fixtures for deployment-builder tests."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def examples_dir():
    """Path to the examples directory containing test configuration files."""
    return Path(__file__).parent.parent / "examples"


@pytest.fixture
def example_files():
    """List of example configuration files for testing."""
    return ["config.toml", "deployment.toml", "config.json", "deployment.yaml"]


@pytest.fixture
def cli_runner():
    """Fixture for running CLI commands with proper error handling."""

    def _run_command(command_args, expect_success=True):
        cmd = ["poetry", "run", "deploy"] + command_args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        if expect_success:
            assert result.returncode == 0, f"Command failed: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        else:
            assert result.returncode != 0, f"Command should have failed but succeeded: {cmd}\nSTDOUT: {result.stdout}"

        return result

    return _run_command


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "general": {"name": "test-deployment", "version": "1.0.0", "environment": "test", "prefix": "test-project"},
        "clusters": {"primary": {"count": 1}, "secondary": {"count": 0}},
    }
