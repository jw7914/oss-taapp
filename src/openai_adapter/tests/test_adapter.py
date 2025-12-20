"""Unit tests for the OpenAI service adapter.

These tests use small dummy objects to simulate HTTP responses and verify
adapter behavior without requiring the FastAPI service or OpenAI credentials.
"""

from __future__ import annotations

import sys
import types

import httpx
import pytest

from openai_adapter import AdapterAPIError, OpenAIServiceAdapter  # type: ignore[attr-defined]


class DummyResp:
    """A minimal fake response object used by DummyHTTP."""

    def __init__(self, status_code: int = 200, json_data: dict[str, object] | None = None, content: bytes | str = b"") -> None:
        """Initialize the fake response with status, json payload and content."""
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content

    def json(self) -> dict[str, object]:
        """Return the stored JSON payload."""
        return self._json


class DummyHTTP:
    """A minimal fake http client with ``post``, ``get``, and ``delete`` methods."""

    def __init__(self, resp: DummyResp) -> None:
        """Create a dummy HTTP client that always returns ``resp``."""
        self._resp = resp

    def post(self, _path: str, **_kwargs: object) -> DummyResp:
        """Return the configured response for POST requests."""
        return self._resp

    def get(self, _path: str, **_kwargs: object) -> DummyResp:
        """Return the configured response for GET requests."""
        return self._resp

    def delete(self, _path: str, **_kwargs: object) -> DummyResp:
        """Return the configured response for DELETE requests."""
        return self._resp


class ErroringHTTP:
    """HTTP stub that raises httpx.HTTPError for all methods."""

    def __init__(self) -> None:
        """Initialize."""

    def post(self, _path: str, **_kwargs: object) -> DummyResp:
        """Raise HTTPError for POST requests."""
        msg = "boom"
        raise httpx.HTTPError(msg)

    def get(self, _path: str, **_kwargs: object) -> DummyResp:
        """Raise HTTPError for GET requests."""
        msg = "boom"
        raise httpx.HTTPError(msg)

    def delete(self, _path: str, **_kwargs: object) -> DummyResp:
        """Raise HTTPError for DELETE requests."""
        msg = "boom"
        raise httpx.HTTPError(msg)


def test_create_conversation_success() -> None:
    """create_conversation returns conversation_id on 200."""
    resp = DummyResp(status_code=200, json_data={"conversation_id": "abc"})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    assert adapter.create_conversation() == "abc"


def test_generate_response_api_error_unauthorized() -> None:
    """generate_response raises AdapterAPIError on 401 without API key."""
    resp = DummyResp(status_code=401, content=b"Missing API key")
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError):
        adapter.generate_response(["hello"])  # no API key -> expect 401


def test_get_conversation_success() -> None:
    """get_conversation returns dict when 200."""
    conv: dict[str, object] = {"id": "abc", "messages": [["user", "hi"]]}
    resp = DummyResp(status_code=200, json_data=conv)
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    data = adapter.get_conversation("abc")
    assert data["id"] == "abc"


def test_delete_conversation_success() -> None:
    """delete_conversation returns True on ok."""
    resp = DummyResp(status_code=200, json_data={"ok": True})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    assert adapter.delete_conversation("abc") is True


def test_delete_conversation_default_true_when_no_body() -> None:
    """delete_conversation returns True when body is empty (default ok)."""
    resp = DummyResp(status_code=200, json_data={}, content=b"")
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    assert adapter.delete_conversation("abc") is True


def test_create_conversation_api_error() -> None:
    """create_conversation raises AdapterAPIError on non-2xx."""
    resp = DummyResp(status_code=500, json_data={})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError):
        adapter.create_conversation()


def test_get_conversation_api_error() -> None:
    """get_conversation raises AdapterAPIError on non-2xx."""
    resp = DummyResp(status_code=404, json_data={})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError):
        adapter.get_conversation("abc")


def test_delete_conversation_api_error() -> None:
    """delete_conversation raises AdapterAPIError on non-2xx."""
    resp = DummyResp(status_code=400, json_data={})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError):
        adapter.delete_conversation("abc")


def test_health_check_true_on_ok_status() -> None:
    """health_check returns True when status is ok."""
    resp = DummyResp(status_code=200, json_data={"status": "ok"})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    assert adapter.health_check() is True


def test_health_check_http_error_returns_false() -> None:
    """health_check returns False when httpx raises."""
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = ErroringHTTP()  # type: ignore[attr-defined,assignment]
    assert adapter.health_check() is False


def test_health_check_non_2xx_returns_false() -> None:
    """health_check returns False on non-2xx status."""
    resp = DummyResp(status_code=500, json_data={})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    assert adapter.health_check() is False


def test_health_check_invalid_json_fallback() -> None:
    """health_check falls back to status when JSON parsing fails."""

    class BadJSONResp(DummyResp):
        def json(self) -> dict[str, object]:
            """Raise ValueError to simulate invalid JSON."""
            msg = "bad json"
            raise ValueError(msg)

    resp = BadJSONResp(status_code=200, json_data={})
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    assert adapter.health_check() is True


def test_constructor_allows_testserver_without_fastapi() -> None:
    """Constructing with testserver base_url should not error even without fastapi."""
    OpenAIServiceAdapter(base_url="http://testserver", session_id="test-session-1")


def test_init_raises_on_empty_base_url() -> None:
    """Constructor should raise ValueError when base_url is empty."""
    with pytest.raises(ValueError, match="base_url is required"):
        OpenAIServiceAdapter(base_url="", session_id="test-session-1")


def test_init_raises_on_empty_session_id() -> None:
    """Constructor should raise ValueError when session_id is empty."""
    with pytest.raises(ValueError, match="session_id is required"):
        OpenAIServiceAdapter(base_url="http://example.com", session_id="")


def test_constructor_uses_asgi_transport_when_testserver(monkeypatch: pytest.MonkeyPatch) -> None:
    """When base_url is testserver and module is present, ASGITransport is used.

    We inject a fake openai_client_service.main with an `app` symbol and stub
    httpx.ASGITransport to ensure the import path is executed.
    """
    fake_pkg = types.ModuleType("openai_client_service")
    fake_main = types.ModuleType("openai_client_service.main")
    fake_main.app = object()  # type: ignore[attr-defined]
    sys.modules["openai_client_service"] = fake_pkg
    sys.modules["openai_client_service.main"] = fake_main

    called = {"count": 0}

    class DummyTransport:
        """Stub transport that records initialisation."""

        def __init__(self, *_: object, **__: object) -> None:
            called["count"] += 1

    monkeypatch.setattr(httpx, "ASGITransport", DummyTransport)
    import openai_adapter.src.openai_adapter._adapter as adapter_module

    monkeypatch.setattr(adapter_module, "_load_test_client", lambda: (None, fake_main.app))

    OpenAIServiceAdapter(base_url="http://testserver", session_id="test-session-1")
    assert called["count"] == 1


def test_generate_response_network_error_raises() -> None:
    """generate_response raises AdapterNetworkError when httpx errors."""
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = ErroringHTTP()  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError.__mro__[1]):  # AdapterNetworkError subclass of AdapterError
        adapter.generate_response(["hi"])  # type: ignore[arg-type]


def test_generate_response_success() -> None:
    """generate_response returns content/tokens/conversation_id on 200."""
    expected_tokens = 10
    payload = {"content": "ok", "tokens_used": expected_tokens, "conversation_id": "c1"}
    resp = DummyResp(status_code=200, json_data=payload)
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = DummyHTTP(resp)  # type: ignore[attr-defined,assignment]
    out = adapter.generate_response(["hi"])  # type: ignore[arg-type]
    assert out["content"] == "ok"
    assert out["tokens_used"] == expected_tokens
    assert out["conversation_id"] == "c1"


def test_create_conversation_network_error_raises() -> None:
    """create_conversation raises AdapterNetworkError when httpx errors."""
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = ErroringHTTP()  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError.__mro__[1]):
        adapter.create_conversation()


def test_get_conversation_network_error_raises() -> None:
    """get_conversation raises AdapterNetworkError when httpx errors."""
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = ErroringHTTP()  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError.__mro__[1]):
        adapter.get_conversation("abc")


def test_delete_conversation_network_error_raises() -> None:
    """delete_conversation raises AdapterNetworkError when httpx errors."""
    adapter = OpenAIServiceAdapter(base_url="http://example.com", session_id="test-session-1")
    adapter._http = ErroringHTTP()  # type: ignore[attr-defined,assignment]
    with pytest.raises(AdapterAPIError.__mro__[1]):
        adapter.delete_conversation("abc")
