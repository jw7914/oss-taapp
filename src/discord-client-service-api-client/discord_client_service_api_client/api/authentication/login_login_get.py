from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    scopes: None | str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_scopes: None | str | Unset
    if isinstance(scopes, Unset):
        json_scopes = UNSET
    else:
        json_scopes = scopes
    params["scopes"] = json_scopes

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/login",
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
    *,
    client: AuthenticatedClient | Client,
    scopes: None | str | Unset = UNSET,
) -> Response[Any | HTTPValidationError]:
    """Get OAuth2 Authorization URL

     Return the authorization URL the user should visit to authorize the application.

    The DiscordClient reads client_id/secret from environment by default. We instantiate
    a temporary client to build the authorization URL.

    Args:
        scopes (None | str | Unset): Optional space-separated scopes override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        scopes=scopes,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    scopes: None | str | Unset = UNSET,
) -> Any | HTTPValidationError | None:
    """Get OAuth2 Authorization URL

     Return the authorization URL the user should visit to authorize the application.

    The DiscordClient reads client_id/secret from environment by default. We instantiate
    a temporary client to build the authorization URL.

    Args:
        scopes (None | str | Unset): Optional space-separated scopes override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        scopes=scopes,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    scopes: None | str | Unset = UNSET,
) -> Response[Any | HTTPValidationError]:
    """Get OAuth2 Authorization URL

     Return the authorization URL the user should visit to authorize the application.

    The DiscordClient reads client_id/secret from environment by default. We instantiate
    a temporary client to build the authorization URL.

    Args:
        scopes (None | str | Unset): Optional space-separated scopes override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        scopes=scopes,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    scopes: None | str | Unset = UNSET,
) -> Any | HTTPValidationError | None:
    """Get OAuth2 Authorization URL

     Return the authorization URL the user should visit to authorize the application.

    The DiscordClient reads client_id/secret from environment by default. We instantiate
    a temporary client to build the authorization URL.

    Args:
        scopes (None | str | Unset): Optional space-separated scopes override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            scopes=scopes,
        )
    ).parsed
