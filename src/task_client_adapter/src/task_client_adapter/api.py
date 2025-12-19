"""API functions for mail service."""

from enum import IntEnum
from typing import Any, cast

from task_client_service_client import Client


class HTTPStatus(IntEnum):
    """HTTP status codes used in the API."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


"""   TASKLIST OPERATIONS   """


def list_tasklists_sync(
    *,
    client: Client,
) -> list[dict[str, str]] | None:
    """List Tasklists.

    Get a list of tasklists from the task client.

    Args:
        client: The client to use for the request

    Returns:
        List of tasklist dictionaries

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/tasklists",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("list[dict[str, str]]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def insert_tasklist_sync(
    *,
    client: Client,
    body: dict[str, str],
) -> dict[str, str] | None:
    """Insert Tasklist.

    Create a new tasklist by delegating to the task client implementation.

    Args:
        client: The client to use for the request
        body: The tasklist data to create

    Returns:
        Tasklist dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/tasklists",
        "json": body,
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, str]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def delete_tasklist_sync(
    tasklist_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    """Delete Tasklist.

    Delete a tasklist by ID by delegating to the task client implementation.

    Args:
        tasklist_id: The ID of the tasklist to delete
        client: The client to use for the request

    Returns:
        Response dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/tasklists/{tasklist_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, Any]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


"""   TASK OPERATIONS   """


def list_tasks_sync(
    tasklist_id: str,
    *,
    client: Client,
) -> list[dict[str, str | None | bool]] | None:
    """List Tasks.

    Get a list of tasks from a tasklist.

    Args:
        tasklist_id: The ID of the tasklist
        client: The client to use for the request

    Returns:
        List of task dictionaries

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/tasks/{tasklist_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("list[dict[str, str | None | bool]]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def get_task_sync(
    tasklist_id: str,
    task_id: str,
    *,
    client: Client,
) -> dict[str, str | None | bool] | None:
    """Get Task.

    Get a specific task by ID from a tasklist.

    Args:
        tasklist_id: The ID of the tasklist
        task_id: The ID of the task to retrieve
        client: The client to use for the request

    Returns:
        Task dictionary or None if not found

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/tasks/{tasklist_id}/{task_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, str | None | bool]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def insert_task_sync(
    tasklist_id: str,
    *,
    client: Client,
    body: dict[str, str | None | bool],
) -> dict[str, str | None | bool] | None:
    """Insert Task.

    Create a new task in a tasklist by delegating to the task client implementation.

    Args:
        tasklist_id: The ID of the tasklist
        client: The client to use for the request
        body: The task data to create

    Returns:
        Task dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/tasks/{tasklist_id}",
        "json": body,
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, str | None | bool]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def delete_task_sync(
    tasklist_id: str,
    task_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    """Delete Task.

    Delete a task by ID from a tasklist by delegating to the task client implementation.

    Args:
        tasklist_id: The ID of the tasklist
        task_id: The ID of the task to delete
        client: The client to use for the request

    Returns:
        Response dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/tasks/{tasklist_id}/{task_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, Any]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def list_messages_sync(
    *,
    client: Client,
) -> list[dict[str, str]] | None:
    """List Messages.

     Get a list of messages from the mail client.

    Args:
        client: The client to use for the request

    Returns:
        List of message dictionaries

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/messages",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("list[dict[str, str]]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def get_message_sync(
    message_id: str,
    *,
    client: Client,
) -> dict[str, str] | None:
    """Get Message.

     Get a specific message by ID.

    Args:
        message_id: The ID of the message to retrieve
        client: The client to use for the request

    Returns:
        Message dictionary or None if not found

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/messages/{message_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, str]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def delete_message_sync(
    message_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    """Delete Message.

     Delete a message by ID by delegating to the mail client implementation.

    Args:
        message_id: The ID of the message to delete
        client: The client to use for the request

    Returns:
        Response dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/messages/{message_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, Any]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def mark_as_read_sync(
    message_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    """Mark As Read.

     Mark a message as read by delegating to the mail client implementation.

    Args:
        message_id: The ID of the message to mark as read
        client: The client to use for the request

    Returns:
        Response dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/messages/{message_id}/mark-as-read",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, Any]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None
