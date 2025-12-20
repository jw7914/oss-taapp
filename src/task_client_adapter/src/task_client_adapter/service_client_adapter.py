"""Service client adapter implementation."""

import json
import logging
from typing import cast

from dotenv import load_dotenv

import task_client_api
from task_client_api import task, tasklist
from task_client_service_client import Client as ServiceClient

from .api import (
    delete_task_sync,
    delete_tasklist_sync,
    get_task_sync,
    insert_task_sync,
    insert_tasklist_sync,
    list_tasklists_sync,
    list_tasks_sync,
)
from .service_task import ServiceTask
from .service_tasklist import ServiceTaskList

load_dotenv()


class ServiceClientAdapter(task_client_api.Client):
    """Adapter that wraps the auto-generated service client to implement the Client protocol."""

    def __init__(self, service_client: ServiceClient) -> None:
        """Initialize the adapter with a service client.

        Args:
            service_client: The authenticated service client to wrap

        """
        self._service_client = service_client
        self.logger = logging.getLogger(__name__)

    def _raise_tasklist_not_found_error(self, tasklist_id: str) -> None:
        """Raise an error when a tasklist is not found."""
        msg = f"Tasklist with ID {tasklist_id} not found"
        raise RuntimeError(msg)

    def _raise_task_not_found_error(self, task_id: str) -> None:
        """Raise an error when a task is not found."""
        msg = f"Task with ID {task_id} not found"
        raise RuntimeError(msg)

    def _raise_insert_tasklist_none_response_error(self) -> None:
        """Raise an error when insert tasklist receives None response."""
        msg = "Failed to insert tasklist: received None response"
        raise RuntimeError(msg)

    def _raise_insert_task_none_response_error(self) -> None:
        """Raise an error when insert task receives None response."""
        msg = "Failed to insert task: received None response"
        raise RuntimeError(msg)

    def _tasklist_to_dict(self, tasklist: tasklist.TaskList) -> dict[str, str]:
        """Convert a TaskList object to a dictionary."""
        return {
            "id": tasklist.id,
            "title": tasklist.title,
            "etag": tasklist.etag,
            "updated": tasklist.updated,
            "self_link": tasklist.self_link,
        }

    def _task_to_dict(self, task: task.Task) -> dict[str, str | bool | None]:
        """Convert a Task object to a dictionary."""
        return {
            "id": task.id,
            "title": task.title,
            "notes": task.notes,
            "status": task.status,
            "due": task.due,
            "completed": task.completed,
            "deleted": task.deleted,
            "hidden": task.hidden,
        }

    """   TASKLIST OPERATIONS   """

    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist by its ID.

        Args:
            tasklist_id: The unique identifier of the tasklist to delete

        Returns:
            bool: True if the tasklist was successfully deleted, False otherwise

        Raises:
            RuntimeError: If the tasklist cannot be deleted

        """
        try:
            self.logger.info("Attempting to delete tasklist %s", tasklist_id)
            response = delete_tasklist_sync(
                tasklist_id=tasklist_id,
                client=self._service_client,
            )

            if response is None:
                self.logger.warning(
                    "Received None response when deleting tasklist %s",
                    tasklist_id,
                )
                return False

            # Check if the response indicates success
            success = response.get("success", True)  # Assume success if we got a response
            if not success:
                self.logger.warning(
                    "Delete operation reported failure for tasklist %s",
                    tasklist_id,
                )
                return False

        except Exception as e:
            self.logger.exception("Failed to delete tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return False

        else:
            self.logger.info("Successfully deleted tasklist %s", tasklist_id)
            return True

    def insert_tasklist(self, tasklist: tasklist.TaskList) -> tasklist.TaskList:
        """Insert a tasklist.

        Args:
            tasklist: The tasklist to insert

        Returns:
            TaskList: The inserted tasklist

        Raises:
            RuntimeError: If the tasklist cannot be inserted

        """
        try:
            self.logger.info("Attempting to insert tasklist with title: '%s'", tasklist.title)
            tasklist_dict = self._tasklist_to_dict(tasklist)
            response = insert_tasklist_sync(
                body=tasklist_dict,
                client=self._service_client,
            )

            if response is None:
                self._raise_insert_tasklist_none_response_error()

            # Convert dict to JSON string to match the contract
            raw_data = json.dumps(cast("dict[str, str]", response))
            return ServiceTaskList(raw_data)

        except Exception as e:
            msg = f"Failed to insert tasklist: {e!s}"
            raise RuntimeError(msg) from e

    def list_tasklists(self) -> list[tasklist.TaskList]:
        """List all tasklists.

        Returns:
            list[TaskList]: A list of all tasklists

        Raises:
            RuntimeError: If the tasklists cannot be retrieved

        """
        try:
            self.logger.info("Fetching tasklists")
            response = list_tasklists_sync(client=self._service_client)

            if response is None:
                self.logger.warning("Received None response from list_tasklists_sync")
                return []

            if not isinstance(response, list):
                self.logger.error(
                    "Expected list response but got %s",
                    type(response).__name__,
                )
                return []

            self.logger.info("Processing %d tasklists", len(response))
            return [ServiceTaskList(json.dumps(tasklist_dict)) for tasklist_dict in response]

        except Exception as e:
            self.logger.exception("Failed to fetch tasklists")
            self.logger.debug("Error details: %s", e)
            return []

    """   TASK OPERATIONS   """

    def list_tasks(self, tasklist_id: str) -> list[task.Task]:
        """List all tasks in a tasklist.

        Args:
            tasklist_id: The ID of the tasklist

        Returns:
            list[Task]: A list of tasks in the tasklist

        Raises:
            RuntimeError: If the tasks cannot be retrieved

        """
        try:
            self.logger.info("Fetching tasks for tasklist %s", tasklist_id)
            response = list_tasks_sync(
                tasklist_id=tasklist_id,
                client=self._service_client,
            )

            if response is None:
                self.logger.warning("Received None response from list_tasks_sync")
                return []

            if not isinstance(response, list):
                self.logger.error(
                    "Expected list response but got %s",
                    type(response).__name__,
                )
                return []

            self.logger.info("Processing %d tasks", len(response))
            return [ServiceTask(json.dumps(task_dict)) for task_dict in response]

        except Exception as e:
            self.logger.exception("Failed to fetch tasks for tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return []

    def insert_task(self, tasklist_id: str, task: task.Task) -> task.Task:
        """Insert a task into a tasklist.

        Args:
            tasklist_id: The ID of the tasklist
            task: The task to insert

        Returns:
            Task: The inserted task

        Raises:
            RuntimeError: If the task cannot be inserted

        """
        try:
            self.logger.info(
                "Attempting to insert task with title: '%s' into tasklist %s",
                task.title,
                tasklist_id,
            )
            task_dict = self._task_to_dict(task)
            response = insert_task_sync(
                tasklist_id=tasklist_id,
                body=task_dict,
                client=self._service_client,
            )

            if response is None:
                self._raise_insert_task_none_response_error()

            # Convert dict to JSON string to match the contract
            raw_data = json.dumps(cast("dict[str, str | bool | None]", response))
            return ServiceTask(raw_data)

        except Exception as e:
            msg = f"Failed to insert task: {e!s}"
            raise RuntimeError(msg) from e

    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """Delete a task by its ID.

        Args:
            tasklist_id: The ID of the tasklist
            task_id: The unique identifier of the task to delete

        Returns:
            bool: True if the task was successfully deleted, False otherwise

        Raises:
            RuntimeError: If the task cannot be deleted

        """
        try:
            self.logger.info(
                "Attempting to delete task %s from tasklist %s",
                task_id,
                tasklist_id,
            )
            response = delete_task_sync(
                tasklist_id=tasklist_id,
                task_id=task_id,
                client=self._service_client,
            )

            if response is None:
                self.logger.warning(
                    "Received None response when deleting task %s",
                    task_id,
                )
                return False

            success = response.get("success", True)
            if not success:
                self.logger.warning(
                    "Delete operation reported failure for task %s",
                    task_id,
                )
                return False

        except Exception as e:
            self.logger.exception("Failed to delete task %s", task_id)
            self.logger.debug("Error details: %s", e)
            return False
        else:
            self.logger.info("Successfully deleted task %s", task_id)
            return True

    def get_task(self, tasklist_id: str, task_id: str) -> task.Task:
        """Get a task by its ID.

        Args:
            tasklist_id: The ID of the tasklist
            task_id: The unique identifier of the task

        Returns:
            Task: The requested task

        Raises:
            RuntimeError: If the task cannot be retrieved

        """
        try:
            response = get_task_sync(
                tasklist_id=tasklist_id,
                task_id=task_id,
                client=self._service_client,
            )

            if response is None:
                # Raise a runtime error if the task is not found
                self._raise_task_not_found_error(task_id)

            # Convert dict to JSON string to match the contract
            raw_data = json.dumps(cast("dict[str, str | bool | None]", response))
            return ServiceTask(raw_data)

        except Exception as e:
            msg = f"Failed to get task {task_id}: {e!s}"
            raise RuntimeError(msg) from e


def get_service_client_impl(
    *,
    interactive: bool = False,  # noqa: ARG001
    base_url: str = "http://127.0.0.1:8001/",
) -> task_client_api.Client:
    """Return a configured :class:`ServiceClientAdapter` instance."""
    service_client = ServiceClient(base_url)
    return ServiceClientAdapter(service_client)


def register() -> None:
    """Register the Google Tasks client implementation with the task client API."""
    task_client_api.get_client = get_service_client_impl
