from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response


def _get_kwargs(
    recipient_id: str,
    *,
    content: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["content"] = content

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/message/{recipient_id}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = response.json()
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
) -> Response[Any | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    recipient_id: str,
    *,
    client: AuthenticatedClient | Client,
    content: str,
) -> Response[Any | HTTPValidationError]:
    """Send a message to a channel

    Args:
        recipient_id (str):
        content (str): Message content

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        recipient_id=recipient_id,
        content=content,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    recipient_id: str,
    *,
    client: AuthenticatedClient | Client,
    content: str,
) -> Any | HTTPValidationError | None:
    """Send a message to a channel

    Args:
        recipient_id (str):
        content (str): Message content

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return sync_detailed(
        recipient_id=recipient_id,
        client=client,
        content=content,
    ).parsed


async def asyncio_detailed(
    recipient_id: str,
    *,
    client: AuthenticatedClient | Client,
    content: str,
) -> Response[Any | HTTPValidationError]:
    """Send a message to a channel

    Args:
        recipient_id (str):
        content (str): Message content

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        recipient_id=recipient_id,
        content=content,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    recipient_id: str,
    *,
    client: AuthenticatedClient | Client,
    content: str,
) -> Any | HTTPValidationError | None:
    """Send a message to a channel

    Args:
        recipient_id (str):
        content (str): Message content

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            recipient_id=recipient_id,
            client=client,
            content=content,
        )
    ).parsed
