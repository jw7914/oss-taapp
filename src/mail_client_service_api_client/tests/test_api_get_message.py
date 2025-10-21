import asyncio
from http import HTTPStatus

import httpx
import pytest

from mail_client_service_api_client.api.messages import get_message
from mail_client_service_api_client import errors
from mail_client_service_api_client.models.http_validation_error import HTTPValidationError


class DummySyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False):
        self._response = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_httpx_client(self):
        return self

    def request(self, **kwargs):
        return self._response


class DummyAsyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False):
        self._response = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_async_httpx_client(self):
        return self

    async def request(self, **kwargs):
        return self._response


def test_get_message_get_kwargs_and_sync_parsed():
    kw = get_message._get_kwargs("abc")
    assert kw["method"] == "get"
    assert kw["url"].endswith("/messages/abc")

    resp = httpx.Response(200, json={"id": "abc", "subject": "hi"})
    client = DummySyncClient(resp)
    parsed = get_message.sync("abc", client=client)
    assert parsed == {"id": "abc", "subject": "hi"}


def test_get_message_sync_parse_422_returns_validation_error():
    resp = httpx.Response(422, json={"detail": []})
    client = DummySyncClient(resp)
    parsed = get_message.sync("abc", client=client)
    assert isinstance(parsed, HTTPValidationError)


def test_get_message_unexpected_status_raises_and_returns_none():
    # raises when flag True
    resp_err = httpx.Response(500, content=b"err")
    client_raise = DummySyncClient(resp_err, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        get_message.sync_detailed("abc", client=client_raise)

    # returns None when flag False
    resp_other = httpx.Response(503, content=b"svc", headers={"X-H": "v"})
    client_no_raise = DummySyncClient(resp_other, raise_on_unexpected_status=False)
    detailed = get_message.sync_detailed("abc", client=client_no_raise)
    assert detailed.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert detailed.parsed is None
    assert detailed.content == resp_other.content
    assert detailed.headers == resp_other.headers


def test_get_message_async_paths():
    resp = httpx.Response(200, json={"id": "z", "subject": "async"})
    client = DummyAsyncClient(resp)
    detailed = asyncio.run(get_message.asyncio_detailed("z", client=client))
    assert detailed.status_code == HTTPStatus.OK
    assert detailed.parsed == {"id": "z", "subject": "async"}

    parsed = asyncio.run(get_message.asyncio("z", client=client))
    assert parsed == {"id": "z", "subject": "async"}


def test_get_message_request_kwargs_forwarded_to_client():
    resp = httpx.Response(200, json={"ok": True})

    class ArgCheckingClient(DummySyncClient):
        def request(self, **kwargs):
            assert kwargs["url"].endswith("/messages/abc")
            assert kwargs["method"] == "get"
            return self._response

    client = ArgCheckingClient(resp)
    parsed = get_message.sync("abc", client=client)
    assert parsed == {"ok": True}