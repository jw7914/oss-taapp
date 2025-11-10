import asyncio
from http import HTTPStatus
from typing import Any, cast

import httpx
import pytest

from mail_client_service_api_client import errors
from mail_client_service_api_client.api.messages import delete_message
from mail_client_service_api_client.client import Client as ApiClient
from mail_client_service_api_client.models.http_validation_error import HTTPValidationError


class DummySyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False) -> None:
        self._response = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_httpx_client(self) -> "DummySyncClient":
        return self

    def request(self, **kwargs: Any) -> httpx.Response:
        return self._response


class DummyAsyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False) -> None:
        self._response = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_async_httpx_client(self) -> "DummyAsyncClient":
        return self

    async def request(self, **kwargs: Any) -> httpx.Response:
        return self._response


def test_delete_message_get_kwargs_and_sync_parsed() -> None:
    kw = delete_message._get_kwargs("del-id")
    assert kw["method"] == "delete"
    assert kw["url"].endswith("/messages/del-id")

    resp = httpx.Response(200, json={"deleted": True})
    client = DummySyncClient(resp)
    parsed = delete_message.sync("del-id", client=cast(ApiClient, client))
    assert parsed == {"deleted": True}


def test_delete_message_sync_parse_422_returns_validation_error() -> None:
    resp = httpx.Response(422, json={"detail": []})
    client = DummySyncClient(resp)
    parsed = delete_message.sync("x", client=cast(ApiClient, client))
    assert isinstance(parsed, HTTPValidationError)


def test_delete_message_unexpected_status_raises_and_returns_none() -> None:
    resp_err = httpx.Response(501, content=b"nope")
    client_raise = DummySyncClient(resp_err, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        delete_message.sync_detailed("x", client=cast(ApiClient, client_raise))

    resp_other = httpx.Response(502, content=b"bad", headers={"X-H": "v"})
    client_no_raise = DummySyncClient(resp_other, raise_on_unexpected_status=False)
    detailed = delete_message.sync_detailed("x", client=cast(ApiClient, client_no_raise))
    assert detailed.status_code == HTTPStatus.BAD_GATEWAY
    assert detailed.parsed is None
    assert detailed.content == resp_other.content
    assert detailed.headers == resp_other.headers


def test_delete_message_async_paths_and_request_forwarding() -> None:
    resp = httpx.Response(200, json={"deleted": "async"})
    client = DummyAsyncClient(resp)
    detailed = asyncio.run(delete_message.asyncio_detailed("async-id", client=cast(ApiClient, client)))
    assert detailed.status_code == HTTPStatus.OK
    assert detailed.parsed == {"deleted": "async"}

    class ArgCheckingClient(DummySyncClient):
        def request(self, **kwargs: Any) -> httpx.Response:
            assert kwargs["url"].endswith("/messages/async-id")
            assert kwargs["method"] == "delete"
            return self._response

    sync_client: ApiClient = cast(ApiClient, ArgCheckingClient(resp))
    parsed = delete_message.sync("async-id", client=sync_client)
    assert parsed == {"deleted": "async"}
