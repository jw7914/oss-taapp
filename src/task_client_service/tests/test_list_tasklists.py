"""Tests for GET /tasklists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from task_client_service import fast_api_service

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import Mock

    import pytest
    from fastapi.testclient import TestClient

    from .conftest import HTTPStatus


def test_list_tasklists_success(
    service_client: TestClient,
    mock_task_client: Mock,
    create_mock_tasklist: Callable[..., Mock],
    http_status: type[HTTPStatus],
) -> None:
    """Test successful retrieval of tasklists."""
    # Arrange
    NUM_OF_TASKLISTS = 2  # noqa: N806
    sample_tasklists = [
        create_mock_tasklist("tl1", "title-tl1"),
        create_mock_tasklist("tl2", "title-tl2"),
    ]
    mock_task_client.list_tasklists.return_value = sample_tasklists

    # Act
    response = service_client.get("/tasklists")

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()

    assert len(data) == NUM_OF_TASKLISTS
    assert data[0]["id"] == "tl1"
    assert data[0]["title"] == "title-tl1"
    assert data[1]["id"] == "tl2"
    assert data[1]["title"] == "title-tl2"

    # Verify the mock was called correctly
    mock_task_client.list_tasklists.assert_called_once()


def test_list_tasklists_empty_list(
    service_client: TestClient,
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Test when no tasklists are returned."""
    # Arrange
    mock_task_client.list_tasklists.return_value = []

    # Act
    response = service_client.get("/tasklists")

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()
    assert data == []

    # Verify the mock was called correctly
    mock_task_client.list_tasklists.assert_called_once()


def test_list_tasklists_single_tasklist(
    service_client: TestClient,
    mock_task_client: Mock,
    create_mock_tasklist: Callable[..., Mock],
    http_status: type[HTTPStatus],
) -> None:
    """Test with a single tasklist."""
    # Arrange
    single_tasklist = create_mock_tasklist("single_tl", "Single Tasklist")
    mock_task_client.list_tasklists.return_value = [single_tasklist]

    # Act
    response = service_client.get("/tasklists")

    # Assert
    assert http_status(response.status_code) == http_status.OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "single_tl"
    assert data[0]["title"] == "Single Tasklist"

    # Verify the mock was called correctly
    mock_task_client.list_tasklists.assert_called_once()


def test_list_tasklists_server_error(
    service_client: TestClient,
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
) -> None:
    """Test when the task client raises an exception."""
    # Arrange
    mock_task_client.list_tasklists.side_effect = RuntimeError("backend died")

    # Act
    response = service_client.get("/tasklists")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR
    data = response.json()
    assert "detail" in data
    assert "backend died" in data["detail"]

    # Verify the mock was called correctly
    mock_task_client.list_tasklists.assert_called_once()


def test_lifespan_starts_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan should init client and shut down cleanly."""

    class DummyClient:
        """Fake task client."""

    def fake_get_client(*, interactive: bool = False) -> DummyClient:
        return DummyClient()

    monkeypatch.setattr(fast_api_service, "get_client", fake_get_client)

    from fastapi.testclient import TestClient

    with TestClient(fast_api_service.app):
        pass


def test_lifespan_init_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan should handle RuntimeError from get_client gracefully."""
    err_msg = "boom from get_client"

    def fake_get_client(*, interactive: bool = False) -> None:
        raise RuntimeError(err_msg)

    monkeypatch.setattr(fast_api_service, "get_client", fake_get_client)

    from fastapi.testclient import TestClient

    # The lifespan catches RuntimeError and handles it gracefully,
    # so the TestClient should initialize successfully with task_client set to None
    # Note: We use fast_api_service.app directly instead of client.app to avoid
    # mypy type issues with TestClient.app, since TestClient.app is typed as Callable
    # in some contexts but is actually the FastAPI app instance at runtime.
    with TestClient(fast_api_service.app):
        # Verify that the app state has task_client set to None
        assert fast_api_service.app.state.task_client is None
