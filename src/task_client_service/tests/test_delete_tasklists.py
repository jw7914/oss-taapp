"""Tests for DELETE /tasklists."""

from __future__ import annotations

from typing import Any

import pytest

from task_client_service.dependencies import get_task_client  # type: ignore[import-untyped]

HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404
HTTP_500_INTERNAL_SERVER_ERROR = 500


class _FakeTasklist:
    """Simple tasklist used for router tests."""

    def __init__(self, tasklist_id: str, title: str = "dummy") -> None:
        self.id = tasklist_id
        self.title = title
        self.etag = "etag"
        self.updated = "2025-01-01T00:00:00Z"
        self.self_link = f"https://example.com/{tasklist_id}"


@pytest.mark.usefixtures("service_client")
class TestDeleteTasklist:
    """Covers delete-tasklist router branches."""

    def _override(self, service_client: Any, client: Any) -> None:
        # mypy: service_client is a pytest fixture (runtime TestClient)
        service_client.app.dependency_overrides[get_task_client] = lambda: client

    def test_delete_default_tasklist_400(self, service_client: Any) -> None:
        """Deleting the first (default) tasklist should return 400."""

        class FakeClient:
            def list_tasklists(self) -> list[_FakeTasklist]:
                return [
                    _FakeTasklist("tl_default", "Default"),
                    _FakeTasklist("tl_other", "Other"),
                ]

            def delete_tasklist(self, tasklist_id: str) -> bool:
                return True

        self._override(service_client, FakeClient())

        resp = service_client.delete("/tasklists/tl_default")
        assert resp.status_code == HTTP_400_BAD_REQUEST
        assert "cannot delete default tasklist" in resp.json()["detail"]

    def test_delete_missing_tasklist_404(self, service_client: Any) -> None:
        """Deleting a tasklist that is not present should return 404."""

        class FakeClient:
            def list_tasklists(self) -> list[_FakeTasklist]:
                return [_FakeTasklist("tl_1"), _FakeTasklist("tl_2")]

            def delete_tasklist(self, tasklist_id: str) -> bool:
                return True

        self._override(service_client, FakeClient())

        resp = service_client.delete("/tasklists/not-exist")
        assert resp.status_code == HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"]

    def test_delete_ok_returns_200(self, service_client: Any) -> None:
        """Deleting a non-default, existing tasklist should return 200 with detail."""

        class FakeClient:
            def list_tasklists(self) -> list[_FakeTasklist]:
                return [
                    _FakeTasklist("tl_default", "Default"),
                    _FakeTasklist("tl_2", "Second"),
                ]

            def delete_tasklist(self, tasklist_id: str) -> bool:
                return True

        self._override(service_client, FakeClient())

        resp = service_client.delete("/tasklists/tl_2")
        assert resp.status_code == HTTP_200_OK
        data = resp.json()
        assert "Tasklist 'Second' deleted." in data["detail"]

    def test_delete_client_returns_false_500(self, service_client: Any) -> None:
        """If backend delete returns False, router should respond 500."""

        class FakeClient:
            def list_tasklists(self) -> list[_FakeTasklist]:
                return [
                    _FakeTasklist("tl_default", "Default"),
                    _FakeTasklist("tl_1", "First"),
                ]

            def delete_tasklist(self, tasklist_id: str) -> bool:
                return False

        self._override(service_client, FakeClient())

        resp = service_client.delete("/tasklists/tl_1")
        assert resp.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to delete tasklist 'tl_1'" in resp.json()["detail"]

    def test_delete_client_raises_500(self, service_client: Any) -> None:
        """If backend delete raises, router should respond 500."""

        class FakeClient:
            def list_tasklists(self) -> list[_FakeTasklist]:
                return [
                    _FakeTasklist("tl_default", "Default"),
                    _FakeTasklist("tl_1", "First"),
                ]

            def delete_tasklist(self, tasklist_id: str) -> bool:
                msg = "boom"
                raise RuntimeError(msg)

        self._override(service_client, FakeClient())

        resp = service_client.delete("/tasklists/tl_1")
        assert resp.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal error while deleting tasklist" in resp.json()["detail"]
