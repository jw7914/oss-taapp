"""Google TaskList Implementation colocated with the GTask client."""

import json
from typing import cast

import task_client_api
from task_client_api import tasklist


class GTaskList(tasklist.TaskList):
    """Concrete implementation of the TaskList abstraction for Google TaskLists."""

    def __init__(self, raw_data: str) -> None:
        """Initialize the tasklist from raw JSON data."""
        self._raw_data = raw_data
        try:
            self._data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            error_msg = "Failed to parse tasklist data"
            raise ValueError(error_msg) from e

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
        return cast("str", self._data.get("selfLink", ""))


def get_tasklist_impl(raw_data: str) -> tasklist.TaskList:
    """Return an instance of the concrete GTaskList implementation."""
    return GTaskList(raw_data=raw_data)


def register() -> None:
    """Register the Google TaskList implementation with the tasklist abstraction."""
    tasklist.get_tasklist = get_tasklist_impl
    task_client_api.get_tasklist = get_tasklist_impl
