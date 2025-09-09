"""Logging configuration for deployment-builder."""

import logging
import logging.handlers
import os
import time
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up logging configuration for the deployment-builder tool.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default location.
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("deployment_builder")

    # Set the log level first
    logger.setLevel(getattr(logging, log_level.upper()))

    # Only set up handlers if they don't exist
    if not logger.handlers:
        # Set default log file if not provided
        if log_file is None:
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "deployment_builder.log"

        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))  # Match logger level
        file_handler.setFormatter(detailed_formatter)

        # Add handler to logger
        logger.addHandler(file_handler)

        # Prevent propagation to root logger to avoid duplicate messages
        logger.propagate = False
    else:
        # Update log level for existing logger and handlers
        logger.setLevel(getattr(logging, log_level.upper()))
        for handler in logger.handlers:
            handler.setLevel(getattr(logging, log_level.upper()))

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name. If None, returns the main logger.

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"deployment_builder.{name}")
    return logging.getLogger("deployment_builder")


def log_command_start(command: str, config_file: Optional[str] = None, **kwargs) -> None:
    """Log the start of a command execution.

    Args:
        command: Command being executed (create, remove, etc.)
        config_file: Configuration file being used
        **kwargs: Additional parameters to log
    """
    logger = get_logger()
    logger.info(f"Starting {command} command")

    if config_file:
        logger.info(f"Using configuration file: {config_file}")
    else:
        logger.info("Using default configuration file discovery")

    if kwargs:
        logger.info(f"Command parameters: {kwargs}")


def log_command_end(command: str, success: bool = True, message: Optional[str] = None) -> None:
    """Log the end of a command execution.

    Args:
        command: Command that was executed
        success: Whether the command succeeded
        message: Optional message to log
    """
    logger = get_logger()
    status = "completed successfully" if success else "failed"
    logger.info(f"{command} command {status}")

    if message:
        logger.info(f"Result: {message}")


def log_config_loaded(config_data: dict, config_file: str) -> None:
    """Log configuration data that was loaded.

    Args:
        config_data: The loaded configuration data
        config_file: Path to the configuration file
    """
    logger = get_logger()
    logger.info(f"Configuration loaded from {config_file}")
    logger.debug(f"Configuration data: {config_data}")


def log_error(error: Exception, context: str = "") -> None:
    """Log an error with context.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
    """
    logger = get_logger()
    if context:
        logger.error(f"Error in {context}: {type(error).__name__}: {error}")
    else:
        logger.error(f"Error: {type(error).__name__}: {error}")
    logger.debug("Full error traceback:", exc_info=True)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.2f}s"


def log_timing_report(start_time: float, command: str, success: bool, cluster_count: int = 0) -> str:
    """Log a timing report for command execution.

    Args:
        start_time: Start time of the command
        command: Name of the command executed
        success: Whether the command was successful
        cluster_count: Number of clusters processed

    Returns:
        Formatted duration string
    """
    logger = get_logger()
    end_time = time.time()
    duration = end_time - start_time

    status = "successfully" if success else "with errors"
    duration_str = format_duration(duration)

    if cluster_count > 0:
        logger.info(f"Timing Report: {command} command completed {status} in {duration_str} ({cluster_count} clusters)")
        logger.info(f"Average time per cluster: {format_duration(duration / cluster_count)}")
    else:
        logger.info(f"Timing Report: {command} command completed {status} in {duration_str}")

    return duration_str
