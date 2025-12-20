"""Test configuration for task client service (Google Tasks)."""

from collections.abc import Callable, Generator
from enum import Enum
from typing import cast
from unittest.mock import Mock, create_autospec, patch

import pytest
from fastapi.testclient import TestClient
from task_client_api import Task as ServiceTask
from task_client_api import TaskList as ServiceTaskList
from task_client_api.client import Client

from task_client_service import app
from task_client_service.dependencies import get_task_client


class HTTPStatus(Enum):
    """HTTP status codes used in the API."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


def assert_response_matches_mock(data: dict[str, str | bool | None], mock_obj: Mock) -> None:
    """Assert that the data matches the mock object."""
    for key, value in data.items():
        assert value == getattr(mock_obj, key), (
            f"Mismatch for key '{key}': expected {getattr(mock_obj, key)}, got {value}"
        )


@pytest.fixture
def http_status() -> type[HTTPStatus]:
    """Provide HTTP status codes enum."""
    return HTTPStatus


@pytest.fixture
def create_mock_tasklist() -> Callable[..., Mock]:
    """Create a mock TaskList object matching the TaskList contract."""

    def _create_mock_tasklist(
        tl_id: str,
        title: str,
        *,
        etag: str = "etag-123",
        updated: str = "2025-01-01T00:00:00.000Z",
        self_link: str = "https://example.com/tasks/lists/tl_id",
    ) -> Mock:
        mock_tl = create_autospec(ServiceTaskList, spec_set=True, instance=True)
        mock_tl.id = tl_id
        mock_tl.title = title
        mock_tl.etag = etag
        mock_tl.updated = updated
        mock_tl.self_link = self_link
        return cast("Mock", mock_tl)

    return _create_mock_tasklist


@pytest.fixture
def create_mock_task() -> Callable[..., Mock]:
    """Create a mock Task object matching the Task contract."""

    def _create_mock_task(  # noqa: PLR0913
        task_id: str,
        title: str,
        *,
        notes: str | None = None,
        status: str = "needsAction",
        due: str | None = None,
        completed: str | None = None,
        deleted: bool = False,
        hidden: bool = False,
    ) -> Mock:
        mock_task = create_autospec(ServiceTask, spec_set=True, instance=True)
        mock_task.id = task_id
        mock_task.title = title
        mock_task.notes = notes
        mock_task.status = status
        mock_task.due = due
        mock_task.completed = completed
        mock_task.deleted = deleted
        mock_task.hidden = hidden
        return cast("Mock", mock_task)

    return _create_mock_task


@pytest.fixture
def mock_task_client() -> Mock:
    """Provide a mock task client."""
    return cast("Mock", create_autospec(Client, spec_set=True, instance=True))


@pytest.fixture
def service_client(mock_task_client: Mock) -> TestClient:
    """Provide a test client with mocked dependencies."""
    app.dependency_overrides[get_task_client] = lambda: mock_task_client
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_webbrowser() -> Generator[None, None, None]:
    """Mock webbrowser.open to prevent opening browser during tests."""
    # Note: webbrowser is no longer used in fast_api_service, but we keep this
    # fixture for compatibility and to prevent any webbrowser usage elsewhere
    with patch("webbrowser.open"):
        yield


@pytest.fixture(autouse=True)
def setup_test(mock_task_client: Mock) -> None:
    """Reset mock state before each test (but reuse the same mock object)."""
    mock_task_client.reset_mock()

    # Tasklist endpoints
    mock_task_client.list_tasklists.side_effect = None
    mock_task_client.insert_tasklist.side_effect = None
    mock_task_client.delete_tasklist.side_effect = None

    # Task endpoints
    mock_task_client.list_tasks.side_effect = None
    mock_task_client.get_task.side_effect = None
    mock_task_client.insert_task.side_effect = None
    mock_task_client.delete_task.side_effect = None
