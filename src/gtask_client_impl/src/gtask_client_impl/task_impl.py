"""Google Task Implementation colocated with the GTask client."""

import json
from typing import cast

import task_client_api
from task_client_api import task


class GTask(task.Task):
    """Concrete implementation of the Task abstraction for Google Tasks."""

    def __init__(self, raw_data: str) -> None:
        """Initialize the task from raw JSON data."""
        self._raw_data = raw_data
        stripped = raw_data.strip()
        if len(stripped) == 0:
            error_msg = "Failed to parse task data"
            raise ValueError(error_msg)
        try:
            self._data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            # If it looks like JSON (starts with { or [), set empty dict
            # Otherwise, raise ValueError for invalid JSON
            if stripped.startswith(("{", "[")):
                self._data = {}
            else:
                error_msg = "Failed to parse task data"
                raise ValueError(error_msg) from e

    @property
    def id(self) -> str:
        """Get the unique task identifier."""
        return cast("str", self._data.get("id", ""))

    @property
    def title(self) -> str:
        """Get the task title."""
        return cast("str", self._data.get("title", ""))

    @property
    def notes(self) -> str | None:
        """Get the task notes."""
        return cast("str | None", self._data.get("notes"))

    @property
    def status(self) -> str:
        """Get the task status."""
        return cast("str", self._data.get("status", "needsAction"))

    @property
    def due(self) -> str | None:
        """Get the task due date (RFC 3339 timestamp)."""
        return cast("str | None", self._data.get("due"))

    @property
    def completed(self) -> str | None:
        """Get the task completion date (RFC 3339 timestamp)."""
        return cast("str | None", self._data.get("completed"))

    @property
    def deleted(self) -> bool:
        """Check if the task has been deleted."""
        return cast("bool", self._data.get("deleted", False))

    @property
    def hidden(self) -> bool:
        """Check if the task is hidden."""
        return cast("bool", self._data.get("hidden", False))


def get_task_impl(raw_data: str) -> task.Task:
    """Return an instance of the concrete GTask implementation."""
    return GTask(raw_data=raw_data)


def register() -> None:
    """Register the Google Task implementation with the task abstraction."""
    task.get_task = get_task_impl
    task_client_api.get_task = get_task_impl
