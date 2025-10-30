import asyncio
from http import HTTPStatus
from typing import Any, cast

import httpx
import pytest

from mail_client_service_api_client import errors
from mail_client_service_api_client.api.messages import mark_message_as_read
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


def test_get_kwargs_builds_correct_url_and_method() -> None:
    kw = mark_message_as_read._get_kwargs(message_id="abc")
    assert kw["method"] == "post"
    assert kw["url"] == "/messages/abc/mark-as-read"


def test_parse_200_and_sync_detailed() -> None:
    resp = httpx.Response(200, json={"status": "ok"})
    client = DummySyncClient(resp)
    detailed = mark_message_as_read.sync_detailed(message_id="abc", client=cast(ApiClient, client))
    assert detailed.status_code == HTTPStatus.OK
    assert detailed.parsed == {"status": "ok"}

    parsed = mark_message_as_read.sync(message_id="abc", client=cast(ApiClient, client))
    assert parsed == {"status": "ok"}


def test_parse_422_returns_validation_error() -> None:
    resp = httpx.Response(422, json={"detail": []})
    client = DummySyncClient(resp)
    parsed = mark_message_as_read.sync(message_id="abc", client=cast(ApiClient, client))
    assert isinstance(parsed, HTTPValidationError)


def test_unexpected_status_raises_when_flag_true() -> None:
    resp = httpx.Response(500, content=b"err")
    client = DummySyncClient(resp, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        mark_message_as_read.sync_detailed(message_id="abc", client=cast(ApiClient, client))


def test_unexpected_status_returns_none_when_flag_false() -> None:
    resp = httpx.Response(500, content=b"err")
    client = DummySyncClient(resp, raise_on_unexpected_status=False)
    detailed = mark_message_as_read.sync_detailed(message_id="abc", client=cast(ApiClient, client))
    assert detailed.parsed is None


def test_asyncio_parsing_and_build_response() -> None:
    resp = httpx.Response(200, json={"status": "async-ok"})
    client = DummyAsyncClient(resp)
    detailed = asyncio.run(mark_message_as_read.asyncio_detailed(message_id="abc", client=cast(ApiClient, client)))
    assert detailed.status_code == HTTPStatus.OK
    assert detailed.parsed == {"status": "async-ok"}


def test_request_kwargs_are_forwarded_to_client() -> None:
    resp = httpx.Response(200, json={"status": "ok"})

    class ArgCheckingClient(DummySyncClient):
        def request(self, **kwargs: Any) -> httpx.Response:
            # the wrapper should forward method/url
            assert kwargs["method"] == "post"
            assert kwargs["url"].endswith("/messages/xyz/mark-as-read")
            return self._response

    client = ArgCheckingClient(resp)
    parsed = mark_message_as_read.sync(message_id="xyz", client=cast(ApiClient, client))
    assert parsed == {"status": "ok"}
