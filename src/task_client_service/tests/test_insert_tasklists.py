"""Tests for POST /tasklists."""

from __future__ import annotations

from typing import TYPE_CHECKING

import task_client_api
from task_client_api import tasklist as tasklist_protocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import Mock

    import pytest
    from fastapi.testclient import TestClient

    from .conftest import HTTPStatus


def test_insert_ok(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: service builds tasklist and client inserts it."""
    # Arrange
    mock_tasklist = create_mock_tasklist("generated-id", "My New Task List")

    def fake_get_service_tasklist(_: str) -> Mock:
        return mock_tasklist

    monkeypatch.setattr(task_client_api, "get_tasklist", fake_get_service_tasklist)
    monkeypatch.setattr(
        tasklist_protocol,
        "get_tasklist",
        fake_get_service_tasklist,
        raising=False,
    )

    mock_task_client.insert_tasklist.return_value = mock_tasklist

    # Act
    resp = service_client.post("/tasklists", json={"title": "My New Task List"})

    # Assert
    assert http_status(resp.status_code) == http_status.OK
    data = resp.json()
    assert data["id"] == "generated-id"
    assert data["title"] == "My New Task List"

    # Verify the mock was called correctly
    mock_task_client.insert_tasklist.assert_called_once()


def test_insert_conflict_409(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If client raises ValueError, router should return 409."""
    # Arrange
    mock_tasklist = create_mock_tasklist("dup-id", "Dup Title")

    def fake_get_service_tasklist(_: str) -> Mock:
        return mock_tasklist

    monkeypatch.setattr(task_client_api, "get_tasklist", fake_get_service_tasklist)
    monkeypatch.setattr(
        tasklist_protocol,
        "get_tasklist",
        fake_get_service_tasklist,
        raising=False,
    )

    mock_task_client.insert_tasklist.side_effect = ValueError("already exists")

    # Act
    resp = service_client.post("/tasklists", json={"title": "Dup Title"})

    # Assert
    assert http_status(resp.status_code) == http_status.CONFLICT
    assert "already exists" in resp.json()["detail"]

    # Verify the mock was called correctly
    mock_task_client.insert_tasklist.assert_called_once()


def test_insert_other_error_500(
    service_client: TestClient,
    create_mock_tasklist: Callable[..., Mock],
    mock_task_client: Mock,
    http_status: type[HTTPStatus],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If client raises non-ValueError, router should return 500."""
    # Arrange
    mock_tasklist = create_mock_tasklist("some-id", "Err Title")

    def fake_get_service_tasklist(_: str) -> Mock:
        return mock_tasklist

    monkeypatch.setattr(task_client_api, "get_tasklist", fake_get_service_tasklist)
    monkeypatch.setattr(
        tasklist_protocol,
        "get_tasklist",
        fake_get_service_tasklist,
        raising=False,
    )

    mock_task_client.insert_tasklist.side_effect = RuntimeError("unexpected")

    # Act
    resp = service_client.post("/tasklists", json={"title": "Err Title"})

    # Assert
    assert http_status(resp.status_code) == http_status.INTERNAL_SERVER_ERROR
    assert "unexpected" in resp.json()["detail"]

    # Verify the mock was called correctly
    mock_task_client.insert_tasklist.assert_called_once()
