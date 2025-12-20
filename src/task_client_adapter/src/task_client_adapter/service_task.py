"""Simple models for API responses."""

import json
from typing import cast

import task_client_api
from task_client_api import task


class ServiceTask(task.Task):
    """Task implementation that wraps service response data."""

    def __init__(self, raw_data: str) -> None:
        """Initialize the task from raw JSON data."""
        self._raw_data = raw_data
        try:
            self._data = json.loads(raw_data)
        except json.JSONDecodeError:
            self._data = {}

    @property
    def id(self) -> str:
        """Return the unique identifier of the task."""
        return cast("str", self._data.get("id", ""))

    @property
    def title(self) -> str:
        """Return the title of the task. Maximum length: 1024 characters."""
        return cast("str", self._data.get("title", ""))

    @property
    def notes(self) -> str | None:
        """Return the notes describing the task. Maximum length: 8192 characters."""
        return cast("str | None", self._data.get("notes"))

    @property
    def status(self) -> str:
        """Return the status of the task. Either 'needsAction' or 'completed'."""
        return cast("str", self._data.get("status", "needsAction"))

    @property
    def due(self) -> str | None:
        """Return the due date of the task (RFC 3339 timestamp)."""
        return cast("str | None", self._data.get("due"))

    @property
    def completed(self) -> str | None:
        """Return the completion date of the task (RFC 3339 timestamp)."""
        return cast("str | None", self._data.get("completed"))

    @property
    def deleted(self) -> bool:
        """Return whether the task has been deleted."""
        return cast("bool", self._data.get("deleted", False))

    @property
    def hidden(self) -> bool:
        """Return whether the task is hidden."""
        return cast("bool", self._data.get("hidden", False))


def get_service_task_impl(raw_data: str) -> task_client_api.Task:
    """Return an instance of the concrete ServiceTask implementation."""
    return ServiceTask(raw_data=raw_data)


def register() -> None:
    """Register the Service Task implementation with the task abstraction."""
    task.get_task = get_service_task_impl  # type: ignore[assignment]
    task_client_api.get_task = get_service_task_impl  # type: ignore[assignment]
