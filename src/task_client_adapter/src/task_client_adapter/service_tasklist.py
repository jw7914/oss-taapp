"""Simple models for API responses."""

import json
from typing import cast

import task_client_api
from task_client_api import tasklist


class ServiceTaskList(tasklist.TaskList):
    """TaskList implementation that wraps service response data."""

    def __init__(self, raw_data: str) -> None:
        """Initialize the tasklist from raw JSON data."""
        self._raw_data = raw_data
        try:
            self._data = json.loads(raw_data)
        except json.JSONDecodeError:
            self._data = {}

    @property
    def id(self) -> str:
        """Get the unique task list identifier."""
        return cast("str", self._data.get("id", ""))

    @property
    def title(self) -> str:
        """Get the task list title."""
        return cast("str", self._data.get("title", ""))

    @property
    def etag(self) -> str:
        """Get the ETag of the resource."""
        return cast("str", self._data.get("etag", ""))

    @property
    def updated(self) -> str:
        """Get the last modification time of the task list (RFC 3339 timestamp)."""
        return cast("str", self._data.get("updated", ""))

    @property
    def self_link(self) -> str:
        """Get the URL pointing to this task list."""
        return cast("str", self._data.get("self_link", ""))


def get_service_tasklist_impl(raw_data: str) -> task_client_api.TaskList:
    """Return an instance of the concrete ServiceTaskList implementation."""
    return ServiceTaskList(raw_data=raw_data)


def register() -> None:
    """Register the Service TaskList implementation with the tasklist abstraction."""
    tasklist.get_tasklist = get_service_tasklist_impl  # type: ignore[assignment]
    task_client_api.get_tasklist = get_service_tasklist_impl  # type: ignore[assignment]
