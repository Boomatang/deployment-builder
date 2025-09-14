"""Test the logging sytsem"""

import time

import pytest

from deployment_builder.logging_config import (
    format_duration,
    log_command_end,
    log_command_start,
    log_error,
    log_timing_report,
)

testdata = [
    ("create", "Starting create command", None, "Using default configuration file discovery"),
    ("create", "Starting create command", {"dummy": "config"}, "Using configuration file"),
]


@pytest.mark.unit
@pytest.mark.parametrize("command,line1,config,line2", testdata)
def test_log_command_start(caplog, command, line1, config, line2):
    """test the format of the logs for starting a command run"""

    log_command_start(command, config_file=config)
    assert line1 in caplog.text
    assert line2 in caplog.text


testdata = [
    ("create", True, None, "create command completed successfully", ""),
    ("create", True, "super", "create command completed successfully", "Result: super"),
    ("create", False, None, "create command failed", ""),
    ("create", False, "bad", "create command failed", "Result: bad"),
]


@pytest.mark.unit
@pytest.mark.parametrize("command,success,message,line1,line2", testdata)
def test_log_command_end(caplog, command, success, message, line1, line2):
    """test the format of the logs for command stopped"""

    log_command_end(command, success, message=message)
    assert line1 in caplog.text
    assert line2 in caplog.text


testdata = [
    (FileExistsError, "my error", "Error in my error", "<class 'FileExistsError'>"),
    (FileExistsError, None, "", "Error: type: <class 'FileExistsError'>"),
]


@pytest.mark.unit
@pytest.mark.parametrize("error,message,line1,line2", testdata)
def test_log_error(caplog, error, message, line1, line2):
    """test the format for logging errors"""

    log_error(error, message)
    assert line1 in caplog.text
    assert line2 in caplog.text


testdata = [
    (00.111, "0.11 seconds"),
    (10.111, "10.11 seconds"),
    (100.111, "1m 40.11s"),
    (3850.111, "1h 4m 10.11s"),
]


@pytest.mark.unit
@pytest.mark.parametrize("seconds,expected", testdata)
def test_format_duration(seconds, expected):
    """test the format of seconds to hunman readable"""
    result = format_duration(seconds)
    assert result == expected


testdata = [
    (100, 700, "create", True, 0, "Timing Report: create command completed successfully in 10m 0.00s", ""),
    (100, 700, "create", False, 0, "Timing Report: create command completed with errors in 10m 0.00s", ""),
    (
        100,
        700,
        "create",
        True,
        2,
        "Timing Report: create command completed successfully in 10m 0.00s (2 clusters)",
        "Average time per cluster: 5m 0.00s",
    ),
    (
        100,
        700,
        "create",
        False,
        2,
        "Timing Report: create command completed with errors in 10m 0.00s (2 clusters)",
        "Average time per cluster: 5m 0.00s",
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize("start,end,command,success,count,line1,line2", testdata)
def test_log_timing_report(caplog, mocker, start, end, command, success, count, line1, line2):
    """test the format of seconds to hunman readable"""

    mock_time = mocker.patch("time.time")
    mock_time.return_value = end

    log_timing_report(start, command, success, cluster_count=count)
    assert line1 in caplog.text
    assert line2 in caplog.text
