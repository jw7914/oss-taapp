import asyncio
from http import HTTPStatus
from typing import Any, cast

import httpx
import pytest

from mail_client_service_api_client import errors
from mail_client_service_api_client.api.authentication import logout
from mail_client_service_api_client.client import Client as ApiClient


class DummySyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False) -> None:
        self._response = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_httpx_client(self) -> "DummySyncClient":
        return self

    def request(self, **kwargs:Any) -> httpx.Response:
        return self._response


class DummyAsyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False)-> None:
        self._response = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_async_httpx_client(self) -> "DummyAsyncClient":
        return self

    async def request(self, **kwargs: Any) -> httpx.Response:
        return self._response


def test_get_kwargs_structure() -> None:
    kw = logout._get_kwargs()
    assert kw["method"] == "get"
    assert kw["url"] == "/logout"


def test_parse_response_200_returns_none() -> None:
    resp = httpx.Response(200)
    client = DummySyncClient(resp)
    parsed = logout._parse_response(client=cast(ApiClient, client), response=resp)
    assert parsed is None


def test_parse_response_unexpected_status_raises_when_flag_true() -> None:
    resp = httpx.Response(500, content=b"server")
    client = DummySyncClient(resp, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        logout._parse_response(client=cast(ApiClient, client), response=resp)


def test_parse_response_unexpected_status_returns_none_when_flag_false() -> None:
    resp = httpx.Response(503, content=b"svc")
    client = DummySyncClient(resp, raise_on_unexpected_status=False)
    parsed = logout._parse_response(client=cast(ApiClient, client), response=resp)
    assert parsed is None


def test_sync_detailed_builds_response() -> None:
    resp = httpx.Response(200, content=b"ok", headers={"X-H": "v"})
    client = DummySyncClient(resp)
    built = logout.sync_detailed(client=cast(ApiClient, client))
    assert built.status_code == HTTPStatus.OK
    assert built.parsed is None
    assert built.content == resp.content
    assert built.headers == resp.headers


def test_asyncio_detailed_builds_response() -> None:
    resp = httpx.Response(200, content=b"async-ok")
    client = DummyAsyncClient(resp)
    built = asyncio.run(logout.asyncio_detailed(client=cast(ApiClient, client)))
    assert built.status_code == HTTPStatus.OK
    assert built.parsed is None
    assert built.content == resp.content