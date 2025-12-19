from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.delete_tasklist_tasklists_tasklist_id_delete_response_delete_tasklist_tasklists_tasklist_id_delete import (
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    tasklist_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/tasklists/{tasklist_id}",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError | None
):
    if response.status_code == 200:
        response_200 = DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete.from_dict(
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
) -> Response[
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError
]:
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
) -> Response[
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError
]:
    """Delete Tasklist

     Delete a tasklist.

    Args:
        tasklist_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        tasklist_id=tasklist_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> (
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError | None
):
    """Delete Tasklist

     Delete a tasklist.

    Args:
        tasklist_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError
    """

    return sync_detailed(
        tasklist_id=tasklist_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError
]:
    """Delete Tasklist

     Delete a tasklist.

    Args:
        tasklist_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        tasklist_id=tasklist_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tasklist_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> (
    DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError | None
):
    """Delete Tasklist

     Delete a tasklist.

    Args:
        tasklist_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeleteTasklistTasklistsTasklistIdDeleteResponseDeleteTasklistTasklistsTasklistIdDelete | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            tasklist_id=tasklist_id,
            client=client,
        )
    ).parsed
