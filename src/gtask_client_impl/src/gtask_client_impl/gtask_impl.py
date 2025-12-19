"""Google Tasks Client Implementation.

This module provides a concrete implementation of the task client API using the Google Tasks API.
It handles OAuth2 authentication and provides methods to interact with Google Tasks and TaskLists.

The implementation supports multiple authentication modes:
    - Environment variables (for CI/CD environments)
    - Local token file (for development)
    - Interactive OAuth flow (for initial setup)
"""

import json
import logging

import task_client_api
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from task_client_api import task, tasklist

from gtask_client_impl.auth import OAuthManager


class GTaskClient(task_client_api.Client):
    """Concrete implementation of the Client abstraction using Google Tasks API.

    This class provides a complete implementation of the mail_client_api.Client abstraction
    using Google's Tasks API. It handles OAuth2 authentication automatically and provides
    methods to interact with Google Tasks.

    Attributes:
        SCOPES: List of OAuth2 scopes required for Gmail API access.
        FAILURE_TO_CRED: Error message for authentication failures.
        service: The authenticated Tasks API service object.

    Authentication Flow:
        1. If `interactive=True`, forces interactive OAuth flow
        2. Try environment variables (TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN)
        3. Try local token.json file
        4. Fallback to interactive OAuth flow

    Environment Variables:
        - TASKS_CLIENT_ID: OAuth2 client ID
        - TASKS_CLIENT_SECRET: OAuth2 client secret
        - TASKS_REFRESH_TOKEN: OAuth2 refresh token
        - TASKS_TOKEN_URI: OAuth2 token URI (optional, defaults to Google's endpoint)

    """

    FAILURE_TO_CRED = "Failed to obtain credentials. Please check your setup."

    def __init__(self, service: Resource | None = None, *, interactive: bool = False) -> None:
        """Initialize the GTaskClient, handling authentication."""
        self.logger = logging.getLogger(__name__)
        self.auth_manager = OAuthManager(logger=self.logger)
        if service:
            self.service = service
            return  # Skip auth if service is provided

        creds = self.auth_manager.select_credentials(interactive=interactive)
        if not creds or not creds.valid:
            raise RuntimeError(self.FAILURE_TO_CRED)
        self.service = build("tasks", "v1", credentials=creds)

    def _ensure_service_initialized(self) -> None:
        """Ensure the service is initialized with valid credentials.

        If service is None, try to get credentials and initialize it.
        Raises RuntimeError if credentials are not available.
        """

        def build_service(creds: Credentials) -> Resource:
            return build("tasks", "v1", credentials=creds)

        self.service = self.auth_manager.ensure_service_initialized(self.service, build_service)

    """   TASKLIST OPERATIONS   """

    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist by its ID.

        Args:
            tasklist_id: The ID of the tasklist to delete.

        Returns:
            True if the tasklist was successfully deleted, False otherwise.

        """
        self._ensure_service_initialized()
        try:
            (
                self.service.tasklists()  # type: ignore[attr-defined]
                .delete(tasklist=tasklist_id)
                .execute()
            )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to delete tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return False
        else:
            return True

    def insert_tasklist(self, tasklist: tasklist.TaskList) -> tasklist.TaskList:
        """Insert a tasklist.

        Args:
            tasklist: TaskList carrying the title to create.

        Returns:
            The created TaskList as returned by the API.

        """
        self._ensure_service_initialized()
        try:
            body = {"title": tasklist.title}
            result = (
                self.service.tasklists()  # type: ignore[attr-defined]
                .insert(body=body)
                .execute()
            )
            # Convert result dict to JSON string for raw_data
            raw_data = json.dumps(result)
            return task_client_api.tasklist.get_tasklist(raw_data=raw_data)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to insert tasklist")
            self.logger.debug("Error details: %s", e)
            raise

    def list_tasklists(self) -> list[tasklist.TaskList]:
        """List all tasklists.

        Returns:
            A list of TaskList objects.

        """
        self._ensure_service_initialized()
        try:
            result = (
                self.service.tasklists().list().execute()  # type: ignore[attr-defined]
            )
            tasklists = []
            for item in result.get("items", []):
                raw_data = json.dumps(item)
                tasklists.append(tasklist.get_tasklist(raw_data=raw_data))
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to list tasklists")
            self.logger.debug("Error details: %s", e)
            return []
        else:
            return tasklists

    """   TASK OPERATIONS   """

    def list_tasks(self, tasklist_id: str) -> list[task.Task]:
        """List all tasks in a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to list tasks from.

        Returns:
            A list of Task objects.

        """
        self._ensure_service_initialized()
        try:
            result = (
                self.service.tasks()  # type: ignore[attr-defined]
                .list(tasklist=tasklist_id)
                .execute()
            )
            tasks = []
            for item in result.get("items", []):
                raw_data = json.dumps(item)
                tasks.append(
                    task.get_task(
                        raw_data=raw_data,
                    )
                )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to list tasks for tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return []
        else:
            return tasks

    def insert_task(self, tasklist_id: str, task: task.Task) -> task.Task:
        """Insert a task into a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to insert the task into.
            task: Task carrying the title to create.
                        (e.g., title, notes, status, due, parent, previous).

        Returns:
            The inserted task with updated fields.

        """
        self._ensure_service_initialized()
        try:
            body: dict[str, str | None] = {
                "title": task.title,
            }
            if task.notes:
                body["notes"] = task.notes
            if task.status:
                body["status"] = task.status
            if task.due:
                body["due"] = task.due

            result = (
                self.service.tasks().insert(tasklist=tasklist_id, body=body).execute()  # type: ignore[attr-defined]
            )
            raw_data = json.dumps(result)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to insert task")
            self.logger.debug("Error details: %s", e)
            raise
        else:
            self.logger.info("Successfully created task with ID: %s", result["id"])
            return task_client_api.task.get_task(
                raw_data=raw_data,
            )

    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """Delete a task by its ID.

        Note: The Google Tasks API requires both tasklist ID and task ID.
        This implementation attempts to delete from the default "@default" tasklist.
        For more control, use a task object that contains the tasklist reference.

        Args:
            tasklist_id: The ID of the tasklist to delete the task from.
            task_id: The unique identifier of the task to delete.

        Returns:
            True if the task was successfully deleted, False otherwise.

        """
        self._ensure_service_initialized()
        try:
            # Note: Google Tasks API requires tasklist ID, defaulting to "@default"
            # In a production system, you might want to store tasklist_id with tasks
            (
                self.service.tasks()  # type: ignore[attr-defined]
                .delete(tasklist=tasklist_id, task=task_id)
                .execute()
            )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to delete task %s", task_id)
            self.logger.debug("Error details: %s", e)
            return False
        else:
            return True

    def get_task(self, tasklist_id: str, task_id: str) -> task.Task:
        """Get a task by its ID.

        Note: The Google Tasks API requires both tasklist ID and task ID.
        This implementation attempts to get from the default "@default" tasklist.

        Args:
            tasklist_id: The ID of the tasklist to get the task from.
            task_id: The unique identifier of the task to retrieve.

        Returns:
            A Task object containing the task data.

        Raises:
            ValueError: If the task cannot be retrieved.

        """
        self._ensure_service_initialized()
        try:
            result = (
                self.service.tasks()  # type: ignore[attr-defined]
                .get(tasklist=tasklist_id, task=task_id)
                .execute()
            )
            raw_data = json.dumps(result)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to get task %s", task_id)
            self.logger.debug("Error details: %s", e)
            error_msg = f"Failed to retrieve task {task_id}"
            raise ValueError(error_msg) from e
        else:
            return task.get_task(raw_data=raw_data)


def get_client_impl(*, interactive: bool = False) -> task_client_api.Client:
    """Return a configured :class:`GTaskClient` instance."""
    return GTaskClient(interactive=interactive)


def register() -> None:
    """Register the GTask client implementation with the task client API."""
    task_client_api.get_client = get_client_impl
