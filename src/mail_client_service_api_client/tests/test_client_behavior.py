import asyncio

import httpx
import pytest
from httpx import AsyncClient
from httpx import Client as HttpxClient

from mail_client_service_api_client.client import AuthenticatedClient, Client


def test_get_httpx_client_constructs_and_reuses() -> None:
    c = Client(base_url="http://example")
    httpx_client = c.get_httpx_client()
    assert isinstance(httpx_client, HttpxClient)
    assert str(httpx_client.base_url) == "http://example"
    # second call returns same instance
    assert c.get_httpx_client() is httpx_client
    httpx_client.close()


def test_set_httpx_client_overrides_and_preserves() -> None:
    c = Client(base_url="http://example")
    custom = httpx.Client(base_url="http://custom", headers={"X-C": "1"})
    c.set_httpx_client(custom)
    got = c.get_httpx_client()
    assert got is custom
    assert got.headers["X-C"] == "1"
    got.close()


def test_with_headers_updates_existing_httpx_client_and_returns_new_instance() -> None:
    c = Client(base_url="http://example")
    underlying = c.get_httpx_client()
    new = c.with_headers({"X-Test": "1"})
    assert new is not c
    # underlying httpx client headers updated in-place
    assert underlying.headers.get("X-Test") == "1"
    # new instance stores merged headers
    assert new._headers["X-Test"] == "1"
    underlying.close()


def test_with_cookies_updates_existing_httpx_client_and_returns_new_instance() -> None:
    c = Client(base_url="http://example")
    underlying = c.get_httpx_client()
    new = c.with_cookies({"session": "abc"})
    assert new is not c
    assert underlying.cookies.get("session") == "abc"
    assert new._cookies["session"] == "abc"
    underlying.close()


def test_with_timeout_updates_underlying_client_and_returns_new_instance() -> None:
    c = Client(base_url="http://example")
    underlying = c.get_httpx_client()
    t = httpx.Timeout(5.0)
    new = c.with_timeout(t)
    assert new is not c
    assert underlying.timeout == t
    assert new._timeout == t
    underlying.close()


def test_context_manager_sync_enter_exit_no_error() -> None:
    c = Client(base_url="http://example")
    with c as ctx:
        assert ctx is c
        assert c._client is not None
    # close underlying client explicitly
    c.get_httpx_client().close()


def test_get_async_httpx_client_and_close() -> None:
    c = Client(base_url="http://example")
    async_client = asyncio.run(async_get_async_client(c))
    assert isinstance(async_client, AsyncClient)
    # ensure we can close it cleanly
    asyncio.run(async_client.aclose())


async def async_get_async_client(client: Client) -> AsyncClient:
    return client.get_async_httpx_client()


def test_authenticated_client_injects_bearer_header_default() -> None:
    ac = AuthenticatedClient(base_url="http://example", token="tok-123")
    httpx_client = ac.get_httpx_client()
    assert "Authorization" in httpx_client.headers
    assert httpx_client.headers["Authorization"] == "Bearer tok-123"
    httpx_client.close()


def test_authenticated_client_custom_prefix_and_header_name() -> None:
    ac = AuthenticatedClient(base_url="http://example", token="mytoken", prefix="", auth_header_name="X-Auth")
    httpx_client = ac.get_httpx_client()
    assert "X-Auth" in httpx_client.headers
    assert httpx_client.headers["X-Auth"] == "mytoken"
    assert "Authorization" not in httpx_client.headers
    httpx_client.close()


def test_authenticated_client_async_injects_header_and_closure() -> None:
    ac = AuthenticatedClient(base_url="http://example", token="tok-async")
    async_client = asyncio.run(async_get_async_client_auth(ac))
    assert async_client.headers.get("Authorization") == "Bearer tok-async"
    asyncio.run(async_client.aclose())


async def async_get_async_client_auth(ac: AuthenticatedClient) -> AsyncClient:
    return ac.get_async_httpx_client()


@pytest.mark.parametrize(
    "prefix,header_name,expected",
    [
        ("Bearer", "Authorization", "Bearer t"),
        ("", "Authorization", "t"),
        ("Token", "X-Auth", "Token t"),
    ],
)
def test_authenticated_client_header_variants(prefix: str, header_name: str, expected: str) -> None:
    ac = AuthenticatedClient(base_url="http://example", token="t", prefix=prefix, auth_header_name=header_name)
    client = ac.get_httpx_client()
    assert client.headers[header_name] == expected
    client.close()


def test_with_headers_without_existing_clients_returns_new_instance_and_preserves_headers() -> None:
    c = Client(base_url="http://example")
    # no underlying sync/async clients created yet
    assert c._client is None
    assert c._async_client is None

    new = c.with_headers({"X-New": "1"})
    assert new is not c
    # original client still has no underlying clients
    assert c._client is None
    assert c._async_client is None
    # new instance stores the merged headers
    assert new._headers.get("X-New") == "1"


def test_set_async_httpx_client_and_get_async_returns_provided_client() -> None:
    c = Client(base_url="http://example")
    custom = httpx.AsyncClient(base_url="http://async")
    c.set_async_httpx_client(custom)
    got = c.get_async_httpx_client()
    assert got is custom
    # cleanup
    asyncio.run(got.aclose())


def test_with_headers_updates_existing_async_client_and_returns_new_instance() -> None:
    c = Client(base_url="http://example")
    async_client = asyncio.run(async_get_async_client(c))
    # ensure underlying async client exists
    assert isinstance(async_client, AsyncClient)

    new = c.with_headers({"X-A": "a"})
    assert new is not c
    # underlying async client's headers should be updated in-place
    assert async_client.headers.get("X-A") == "a"
    # cleanup
    asyncio.run(async_client.aclose())


def test_authenticated_client_context_manager_enter_exit_and_set_async_client_behaviour() -> None:
    ac = AuthenticatedClient(base_url="http://example", token="tok-ctx")
    # context manager should create underlying client
    with ac as ctx:
        assert ctx is ac
        assert ac._client is not None
        # underlying client should have auth header
        assert ac._client.headers.get(ac.auth_header_name) is not None
    # now test set_async_httpx_client keeps provided async client
    provided = httpx.AsyncClient(base_url="http://provided")
    ac.set_async_httpx_client(provided)
    got = ac.get_async_httpx_client()
    assert got is provided
    asyncio.run(got.aclose())


def test_with_timeout_updates_existing_async_client_and_returns_new_instance() -> None:
    c = Client(base_url="http://example")
    async_client = asyncio.run(async_get_async_client(c))
    t = httpx.Timeout(7.0)
    new = c.with_timeout(t)
    assert new is not c
    assert async_client.timeout == t
    assert new._timeout == t
    asyncio.run(async_client.aclose())
