"""Unit tests for delete task endpoint."""

from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient

from .conftest import HTTPStatus


def test_delete_task_success(
    service_client: TestClient,
    create_mock_task: Callable[..., Mock],
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests delete task fastapi endpoint success."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    mock_task = create_mock_task("tsk_1", "bananas")
    mock_task_client.delete_task.return_value = True

    # Act
    response = service_client.delete(
        f"/tasks/{mock_tasklist.id}/{mock_task.id}",
    )

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()
    assert "detail" in data
    assert f"Task '{mock_task.id}' deleted from tasklist '{mock_tasklist.id}'." in data["detail"]

    mock_task_client.delete_task.assert_called_once_with(mock_tasklist.id, mock_task.id)


def test_delete_task_not_found(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests delete task endpoint with non-existent task expecting 404 Not Found."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    nonexistent_task_id = "nonexistent_task_id"

    # Configure mock to return False when trying to delete non-existent task
    mock_task_client.delete_task.return_value = False

    # Act
    response = service_client.delete(f"/tasks/{mock_tasklist.id}/{nonexistent_task_id}")

    # Assert
    assert http_status(response.status_code) == http_status.NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert f"Task '{nonexistent_task_id}' not found" in data["detail"]

    mock_task_client.delete_task.assert_called_once_with(mock_tasklist.id, nonexistent_task_id)


def test_delete_task_tasklist_not_found(
    service_client: TestClient,
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests delete task endpoint with non-existent tasklist expecting 500 Internal Server Error."""
    # Arrange
    nonexistent_tasklist_id = "nonexistent_tl_id"
    task_id = "tsk_1"

    # Configure mock to return False when trying to delete from non-existent tasklist
    mock_task_client.delete_task.return_value = False

    # Act
    response = service_client.delete(f"/tasks/{nonexistent_tasklist_id}/{task_id}")

    # Assert
    assert http_status(response.status_code) == http_status.NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert f"Task '{task_id}' not found" in data["detail"]

    mock_task_client.delete_task.assert_called_once_with(nonexistent_tasklist_id, task_id)
