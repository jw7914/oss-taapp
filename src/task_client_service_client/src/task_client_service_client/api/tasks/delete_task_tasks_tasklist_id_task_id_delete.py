from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.delete_task_tasks_tasklist_id_task_id_delete_response_delete_task_tasks_tasklist_id_task_id_delete import (
    DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    tasklist_id: str,
    task_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/tasks/{tasklist_id}/{task_id}",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tasklist_id: str,
    task_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError]:
    """Delete Task

     Mark a task as deleted.

    Args:
        tasklist_id (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        tasklist_id=tasklist_id,
        task_id=task_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tasklist_id: str,
    task_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError | None:
    """Delete Task

     Mark a task as deleted.

    Args:
        tasklist_id (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError
    """

    return sync_detailed(
        tasklist_id=tasklist_id,
        task_id=task_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    tasklist_id: str,
    task_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError]:
    """Delete Task

     Mark a task as deleted.

    Args:
        tasklist_id (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        tasklist_id=tasklist_id,
        task_id=task_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tasklist_id: str,
    task_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError | None:
    """Delete Task

     Mark a task as deleted.

    Args:
        tasklist_id (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteTaskTasksTasklistIdTaskIdDeleteResponseDeleteTaskTasksTasklistIdTaskIdDelete | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            tasklist_id=tasklist_id,
            task_id=task_id,
            client=client,
        )
    ).parsed
