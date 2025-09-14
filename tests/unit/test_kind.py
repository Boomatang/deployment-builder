"""
test that look at the kind integration.
This will be using mocks :(
"""

import pytest
from pytest_mock import mocker

from deployment_builder.kind import Kind


@pytest.mark.kind
@pytest.mark.unit
def test_create_success(mocker: mocker):
    """check that the correct code runs if the cluster creation was a success"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="Cluster created successfully", stderr="")

    kind = Kind()
    kind.create("test-cluster")

    mock_run.assert_called_once_with(
        ["kind", "create", "cluster", "--name", "test-cluster"], capture_output=True, text=True, check=False
    )


@pytest.mark.kind
@pytest.mark.unit
def test_create_failure(mocker: mocker):
    """check that the correct code runs if the cluster creation was a success"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=1, stdout="", stderr="Cluster was not created")

    kind = Kind()
    kind.create("test-cluster")

    mock_run.assert_called_once_with(
        ["kind", "create", "cluster", "--name", "test-cluster"], capture_output=True, text=True, check=False
    )

    assert mock_run.return_value.returncode == 1


@pytest.mark.kind
@pytest.mark.unit
def test_delete_success(mocker: mocker):
    """check that the correct code runs if the cluster creation was a success"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="Cluster delete successfully", stderr="")

    kind = Kind()
    kind.delete("test-cluster")

    mock_run.assert_called_once_with(
        ["kind", "delete", "cluster", "--name", "test-cluster"], capture_output=True, text=True, check=False
    )
