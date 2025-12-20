"""Tasks contract - Core task representation."""

from abc import ABC, abstractmethod


class Task(ABC):
    """Abstract base class representing a Google Task."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the task."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return the title of the task. Maximum length: 1024 characters."""
        raise NotImplementedError

    @property
    @abstractmethod
    def notes(self) -> str | None:
        """Return the notes describing the task. Maximum length: 8192 characters."""
        raise NotImplementedError

    @property
    @abstractmethod
    def status(self) -> str:
        """Return the status of the task. Either 'needsAction' or 'completed'."""
        raise NotImplementedError

    @property
    @abstractmethod
    def due(self) -> str | None:
        """Return the due date of the task (RFC 3339 timestamp)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def completed(self) -> str | None:
        """Return the completion date of the task (RFC 3339 timestamp)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def deleted(self) -> bool:
        """Return whether the task has been deleted."""
        raise NotImplementedError

    @property
    @abstractmethod
    def hidden(self) -> bool:
        """Return whether the task is hidden."""
        raise NotImplementedError


def get_task(raw_data: str) -> Task:
    """Return an instance of a Task.

    Args:
        task_id (str): The unique identifier for the task.
        raw_data (str): The raw data used to construct the task.

    Returns:
        Task: An instance conforming to the Task contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
