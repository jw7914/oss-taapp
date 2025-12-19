"""Core task client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod

from task_client_api.task import Task
from task_client_api.tasklist import TaskList

__all__ = ["Client", "get_client"]


class Client(ABC):
    """Abstract base class representing a task client for task operations."""

    """   TASKLIST OPERATIONS   """

    @abstractmethod
    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist by its ID.

        Args:
            tasklist_id: The ID of the tasklist to delete.

        Returns:
            True if the tasklist was successfully deleted, False otherwise.

        """
        raise NotImplementedError

    @abstractmethod
    def insert_tasklist(self, tasklist: TaskList) -> TaskList:
        """Insert a tasklist.

        Args:
            tasklist: TaskList carrying the title to create.

        Returns:
            The created TaskList as returned by the API.

        """
        raise NotImplementedError

    @abstractmethod
    def list_tasklists(self) -> list[TaskList]:
        """List all tasklists.

        Returns:
            A list of TaskList objects.

        """
        raise NotImplementedError

    """   TASK OPERATIONS   """

    @abstractmethod
    def list_tasks(self, tasklist_id: str) -> list[Task]:
        """List all tasks in a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to list tasks from.

        Returns:
            A list of Task objects.

        """
        raise NotImplementedError

    @abstractmethod
    def insert_task(self, tasklist_id: str, task: Task) -> Task:
        """Insert a task into a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to insert the task into.
            task: Task carrying the data to create (e.g., title, notes, status, due).

        Returns:
            The inserted task with updated fields.

        """
        raise NotImplementedError

    @abstractmethod
    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """Delete a task by its ID.

        Args:
            tasklist_id: The ID of the tasklist to delete the task from.
            task_id: The unique identifier of the task to delete.

        Returns:
            True if the task was successfully deleted, False otherwise.

        """
        raise NotImplementedError

    @abstractmethod
    def get_task(self, tasklist_id: str, task_id: str) -> Task:
        """Get a task by its ID.

        Args:
            tasklist_id: The ID of the tasklist to get the task from.
            task_id: The unique identifier of the task to retrieve.

        Returns:
            A Task object containing the task data.

        """
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of a Task Client.

    Args:
        interactive: If True, allows interactive authentication flow.

    Returns:
        A Client instance configured for task operations.

    """
    raise NotImplementedError
