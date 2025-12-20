from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.insert_task_tasks_tasklist_id_post_response_insert_task_tasks_tasklist_id_post import (
    InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost,
)
from ...models.insert_task_tasks_tasklist_id_post_task_input import InsertTaskTasksTasklistIdPostTaskInput
from ...types import Response


def _get_kwargs(
    tasklist_id: str,
    *,
    body: InsertTaskTasksTasklistIdPostTaskInput,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/tasks/{tasklist_id}",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost | None:
    if response.status_code == 200:
        response_200 = InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost.from_dict(response.json())

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
) -> Response[HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: InsertTaskTasksTasklistIdPostTaskInput,
) -> Response[HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost]:
    """Insert Task

     Insert a new task into a tasklist.

    Args:
        tasklist_id (str):
        body (InsertTaskTasksTasklistIdPostTaskInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost]
    """

    kwargs = _get_kwargs(
        tasklist_id=tasklist_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: InsertTaskTasksTasklistIdPostTaskInput,
) -> HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost | None:
    """Insert Task

     Insert a new task into a tasklist.

    Args:
        tasklist_id (str):
        body (InsertTaskTasksTasklistIdPostTaskInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost
    """

    return sync_detailed(
        tasklist_id=tasklist_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: InsertTaskTasksTasklistIdPostTaskInput,
) -> Response[HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost]:
    """Insert Task

     Insert a new task into a tasklist.

    Args:
        tasklist_id (str):
        body (InsertTaskTasksTasklistIdPostTaskInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost]
    """

    kwargs = _get_kwargs(
        tasklist_id=tasklist_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: InsertTaskTasksTasklistIdPostTaskInput,
) -> HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost | None:
    """Insert Task

     Insert a new task into a tasklist.

    Args:
        tasklist_id (str):
        body (InsertTaskTasksTasklistIdPostTaskInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | InsertTaskTasksTasklistIdPostResponseInsertTaskTasksTasklistIdPost
    """

    return (
        await asyncio_detailed(
            tasklist_id=tasklist_id,
            client=client,
            body=body,
        )
    ).parsed
