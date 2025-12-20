from http import HTTPStatus
from typing import Any, cast

import httpx
import pytest

from mail_client_service_api_client import errors
from mail_client_service_api_client.api.messages import get_messages
from mail_client_service_api_client.client import Client as ApiClient


class DummySyncClient:
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False) -> None:
        self._resp = response
        self.raise_on_unexpected_status = raise_on_unexpected_status

    def get_httpx_client(self) -> "DummySyncClient":
        return self

    def request(self, **kwargs: Any) -> httpx.Response:
        return self._resp


class DummyAsyncClient(DummySyncClient):
    def __init__(self, response: httpx.Response, raise_on_unexpected_status: bool = False) -> None:
        self._resp = response

    def request(self, **kwargs: Any) -> httpx.Response:
        return self._resp


def test_get_messages_get_kwargs_defaults() -> None:
    kw = get_messages._get_kwargs()
    assert kw["url"] == "/messages"
    assert "params" in kw
    # default max_results should exist and equal 3
    assert kw["params"]["max_results"] == 3


def test_get_messages_parse_200_and_sync_detailed() -> None:
    resp = httpx.Response(200, json=[{"id": "m1"}])
    client = DummySyncClient(resp)
    r = get_messages.sync_detailed(client=cast(ApiClient, client))
    assert r.status_code == HTTPStatus.OK
    assert r.parsed == [{"id": "m1"}]


def test_get_messages_parse_422_returns_validation_error() -> None:
    resp = httpx.Response(422, json={"detail": []})
    client = DummySyncClient(resp)
    parsed = get_messages.sync(client=cast(ApiClient, client))
    # library parses HTTPValidationError; parsed should not be None
    assert parsed is not None


def test_get_messages_unexpected_status_raises_when_flagged() -> None:
    resp = httpx.Response(500, content=b"err")
    client = DummySyncClient(resp, raise_on_unexpected_status=True)
    with pytest.raises(errors.UnexpectedStatus):
        get_messages.sync_detailed(client=cast(ApiClient, client))
