"""Unit tests for insert task endpoint."""

from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient

from .conftest import HTTPStatus, assert_response_matches_mock


def test_insert_task_success(
    service_client: TestClient,
    create_mock_task: Callable[..., Mock],
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests insert task fastapi endpoint success."""
    # Arrange
    mock_task = create_mock_task("tsk_1", "bananas")
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")

    mock_task_client.list_tasklists.return_value = [mock_tasklist]
    mock_task_client.insert_task.return_value = mock_task

    # Act
    task_data = {
        "title": "This is a new task",
        "notes": "Task notes",
        "status": "needsAction",
    }

    response = service_client.post(f"/tasks/{mock_tasklist.id}", json=task_data)

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()

    assert_response_matches_mock(data, mock_task)

    mock_task_client.insert_task.assert_called_once()


def test_insert_task_invalid_date_format(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests insert task endpoint with invalid date format expecting 400 Bad Request."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    mock_task_client.list_tasklists.return_value = [mock_tasklist]

    # Act
    task_data = {
        "title": "Task with bad date",
        "notes": "This task has an invalid date format",
        "status": "needsAction",
        "due": "invalid-date-format",  # This should cause a ValueError
    }

    response = service_client.post(f"/tasks/{mock_tasklist.id}", json=task_data)

    # Assert
    assert http_status(response.status_code) == http_status.BAD_REQUEST
    data = response.json()
    assert "detail" in data

    mock_task_client.insert_task.assert_not_called()


def test_insert_task_nonexistent_tasklist(
    service_client: TestClient,
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests insert task endpoint with non-existent tasklist expecting 500 Internal Server Error."""
    # Arrange
    nonexistent_tasklist_id = "nonexistent_tl_id"

    # Configure mock to raise an exception when trying to insert into non-existent tasklist
    mock_task_client.insert_task.side_effect = Exception("Tasklist not found")

    # Act
    task_data = {
        "title": "Task for non-existent list",
        "notes": "This task is for a tasklist that doesn't exist",
        "status": "needsAction",
    }

    response = service_client.post(f"/tasks/{nonexistent_tasklist_id}", json=task_data)

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR
    data = response.json()
    assert "detail" in data

    mock_task_client.insert_task.assert_called_once()
