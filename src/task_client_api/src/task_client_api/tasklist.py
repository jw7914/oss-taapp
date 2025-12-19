"""TaskList contract - Core task list representation."""

from abc import ABC, abstractmethod


class TaskList(ABC):
    """Abstract base class representing a Google Task List."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the task list."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return the title of the task list. Maximum length: 1024 characters."""
        raise NotImplementedError

    @property
    @abstractmethod
    def etag(self) -> str:
        """Return the ETag of the resource."""
        raise NotImplementedError

    @property
    @abstractmethod
    def updated(self) -> str:
        """Return the last modification time of the task list (RFC 3339 timestamp)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def self_link(self) -> str:
        """Return the URL pointing to this task list."""
        raise NotImplementedError


def get_tasklist(raw_data: str) -> TaskList:
    """Return an instance of a TaskList.

    Args:
        task_list_id (str): The unique identifier for the task list.
        raw_data (str): The raw data used to construct the task list.

    Returns:
        TaskList: An instance conforming to the TaskList contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
