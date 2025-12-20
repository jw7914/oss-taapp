"""Unit tests for get task endpoint."""

from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient

from .conftest import HTTPStatus, assert_response_matches_mock


def test_get_task_success(
    service_client: TestClient,
    create_mock_task: Callable[..., Mock],
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests get task fastapi endpoint success."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    mock_task = create_mock_task("tsk_1", "bananas")
    mock_task_client.get_task.return_value = mock_task

    # Act
    response = service_client.get(
        f"/tasks/{mock_tasklist.id}/{mock_task.id}",
    )

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()

    assert_response_matches_mock(data, mock_task)
    mock_task_client.get_task.assert_called_once_with(mock_tasklist.id, mock_task.id)


def test_get_task_not_found(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests get task endpoint with non-existent task expecting 500 Internal Server Error."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    nonexistent_task_id = "nonexistent_task_id"

    # Configure mock to raise an exception when trying to get non-existent task
    mock_task_client.get_task.side_effect = Exception("Task not found")

    # Act
    response = service_client.get(f"/tasks/{mock_tasklist.id}/{nonexistent_task_id}")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR
    data = response.json()
    assert "detail" in data
    assert "Task not found" in data["detail"]

    mock_task_client.get_task.assert_called_once_with(mock_tasklist.id, nonexistent_task_id)


def test_get_task_client_error(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests get task endpoint with client error expecting 500 Internal Server Error."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    task_id = "tsk_1"

    # Configure mock to raise a different exception
    mock_task_client.get_task.side_effect = RuntimeError("Connection error")

    # Act
    response = service_client.get(f"/tasks/{mock_tasklist.id}/{task_id}")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR
    data = response.json()
    assert "detail" in data
    assert "Connection error" in data["detail"]

    mock_task_client.get_task.assert_called_once_with(mock_tasklist.id, task_id)
