import asyncio
from http import HTTPStatus
from typing import Any, cast

import httpx
import pytest

from mail_client_service_api_client import errors
from mail_client_service_api_client.api.authentication import login
from mail_client_service_api_client.client import Client as ApiClient
from mail_client_service_api_client.models.http_validation_error import HTTPValidationError
from mail_client_service_api_client.types import UNSET


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

    async def request(self, **kwargs: Any)-> httpx.Response:
        return self._response


def test_get_kwargs_includes_and_excludes_interactive() -> None:
    # default should include interactive=False
    kw = login._get_kwargs()
    assert kw["url"] == "/login"
    assert "params" in kw
    assert kw["params"]["interactive"] is False

    # UNSET should remove the param
    kw2 = login._get_kwargs(interactive=UNSET)
    assert "params" in kw2
    assert kw2["params"] == {}


def test_sync_detailed_and_sync_parse_200() -> None:
    resp = httpx.Response(200, json={"ok": True})
    client = DummySyncClient(resp)
    detailed = login.sync_detailed(client=cast(ApiClient, client))
    assert detailed.status_code == HTTPStatus.OK
    assert detailed.parsed == {"ok": True}

    parsed = login.sync(client=cast(ApiClient, client))
    assert parsed == {"ok": True}


def test_sync_parse_422_returns_validation_error() -> None:
    resp = httpx.Response(422, json={"detail": []})
    client = DummySyncClient(resp)
    parsed = login.sync(client=cast(ApiClient, client))
    assert isinstance(parsed, HTTPValidationError)


def test_sync_detailed_unexpected_status_raises() -> None:
    resp = httpx.Response(500, content=b"server error")
    client = DummySyncClient(resp, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        login.sync_detailed(client=cast(ApiClient, client))


def test_asyncio_detailed_and_async_parse_200() -> None:
    resp = httpx.Response(200, json={"ok": "async"})
    client = DummyAsyncClient(resp)
    detailed = asyncio.run(login.asyncio_detailed(client=cast(ApiClient, client)))
    assert detailed.status_code == HTTPStatus.OK
    assert detailed.parsed == {"ok": "async"}

    parsed = asyncio.run(login.asyncio(client=cast(ApiClient, client)))
    assert parsed == {"ok": "async"}

def test_get_kwargs_interactive_true() -> None:
    kw = login._get_kwargs(interactive=True)
    assert "params" in kw
    assert kw["params"]["interactive"] is True

def test_get_kwargs_interactive_none_removes_param() -> None:
    kw = login._get_kwargs(interactive=UNSET)
    assert "params" in kw
    assert kw["params"] == {}

def test_sync_detailed_unexpected_status_returns_none_when_flag_false() -> None:
    resp = httpx.Response(500, content=b"server error", headers={"X-Test": "1"})
    client = DummySyncClient(resp, raise_on_unexpected_status=False)
    detailed = login.sync_detailed(client=cast(ApiClient, client))
    assert detailed.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert detailed.parsed is None
    assert detailed.content == resp.content
    assert detailed.headers == resp.headers

def test_asyncio_detailed_unexpected_status_raises() -> None:
    resp = httpx.Response(503, content=b"unavailable")
    client = DummyAsyncClient(resp, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        asyncio.run(login.asyncio_detailed(client=cast(ApiClient, client)))

def test_request_kwargs_forwarded_to_client() -> None:
    resp = httpx.Response(200, json={"ok": True})

    class ArgCheckingClient(DummySyncClient):
        def request(self, **kwargs: Any) -> httpx.Response:
            assert kwargs["url"].endswith("/login")
            assert "params" in kwargs
            # the interactive param should be forwarded and True
            assert kwargs["params"]["interactive"] is True
            return self._response

    client = ArgCheckingClient(resp)
    # call sync which should forward params to the client's request
    parsed = login.sync(client=cast(ApiClient, client), interactive=True)
    assert parsed == {"ok": True}
# ...existing code...