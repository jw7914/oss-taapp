"""Unit tests for get tasks endpoint."""

from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient

from .conftest import HTTPStatus, assert_response_matches_mock


def test_get_tasks_success(
    service_client: TestClient,
    create_mock_task: Callable[..., Mock],
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests insert task fastapi endpoint success."""
    # Arrange
    mock_tasklist = create_mock_tasklist("tl_1", "groceries")
    mock_task = create_mock_task("tsk_1", "bananas")
    mock_task_client.list_tasks.return_value = [mock_task]

    # Act
    response = service_client.get(
        f"/tasks/{mock_tasklist.id}",
    )

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()

    assert len(data) == 1
    assert_response_matches_mock(data[0], mock_task)
    mock_task_client.list_tasks.assert_called_once()


def test_list_tasks_nonexistent_tasklist(
    service_client: TestClient,
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Tests insert task endpoint with non-existent tasklist expecting 500 Internal Server Error."""
    # Arrange
    nonexistent_tasklist_id = "nonexistent_tl_id"

    # Configure mock to raise an exception when trying to insert into non-existent tasklist
    mock_task_client.list_tasks.side_effect = Exception("Tasklist not found")

    # Act
    response = service_client.get(f"/tasks/{nonexistent_tasklist_id}")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR
    data = response.json()
    assert "detail" in data

    mock_task_client.list_tasks.assert_called_once()
