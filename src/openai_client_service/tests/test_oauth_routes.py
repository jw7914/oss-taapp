"""Tests for the OAuth routes of the OpenAI client service."""

from __future__ import annotations

import json
import urllib.parse
from importlib import import_module
from typing import TYPE_CHECKING, Any, Self

import pytest
from fastapi.testclient import TestClient
from starlette import status

from openai_client_service.main import app
from openai_client_service.routes import oauth

if TYPE_CHECKING:
    from types import TracebackType
else:
    TracebackType = object  # type: ignore[assignment]


@pytest.fixture
def oauth_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Return a TestClient with database initialisation disabled."""
    app.dependency_overrides.clear()
    main_module = import_module("openai_client_service.main")
    monkeypatch.setattr(main_module, "init_db", lambda: None, raising=False)
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def _mock_oauth_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Install a synthetic OAuth configuration for tests."""
    cfg = {
        "client_id": "cid",
        "client_secret": "secret",
        "auth_url": "https://auth.example/authorize",
        "token_url": "https://auth.example/token",
        "redirect_uri": "https://app.example/callback",
        "scope": "openid",
        "userinfo_url": "https://auth.example/me",
    }
    monkeypatch.setattr(oauth, "_oauth_config", lambda: cfg)
    return cfg


class DummyHTTPClient:
    """Tiny httpx replacement returning canned responses."""

    def __init__(self, responses: dict[str, Any]) -> None:
        """Persist the canned response mapping."""
        self._responses = responses

    def __enter__(self) -> Self:
        """Support use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        """Clean up the context manager (no-op for fake client)."""

    def post(self, _url: str, *_args: Any, **_kwargs: Any) -> Any:
        """Return the stubbed POST response."""
        return self._responses["post"]

    def get(self, _url: str, *_args: Any, **_kwargs: Any) -> Any:
        """Return the stubbed GET response."""
        return self._responses["get"]


class DummyResponse:
    """Minimal httpx.Response surrogate."""

    def __init__(self, status_code: int, payload: Any) -> None:
        """Store status code and payload for later inspection."""
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> Any:
        """Return the JSON payload."""
        return self._payload


@pytest.mark.unit
def test_oauth_login_sets_cookie_and_redirect(oauth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The login endpoint should redirect and set an OAuth state cookie."""
    _mock_oauth_config(monkeypatch)
    resp = oauth_client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == status.HTTP_302_FOUND
    assert resp.headers["location"].startswith("https://auth.example/authorize")
    assert "oauth_state" in resp.cookies

    parsed = urllib.parse.urlparse(resp.headers["location"])
    params = urllib.parse.parse_qs(parsed.query)
    assert params["client_id"] == ["cid"]
    assert params["state"][0] == resp.cookies["oauth_state"]


@pytest.mark.unit
def test_oauth_callback_creates_session(oauth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Callback should exchange the token and establish a session."""
    _mock_oauth_config(monkeypatch)
    login_resp = oauth_client.get("/auth/login", follow_redirects=False)
    state = login_resp.cookies["oauth_state"]

    token_payload = {"access_token": "token-123"}
    userinfo_payload = {"sub": "subject-1"}

    responses = {
        "post": DummyResponse(200, token_payload),
        "get": DummyResponse(200, userinfo_payload),
    }
    monkeypatch.setattr(oauth.httpx, "Client", lambda *_args, **_kwargs: DummyHTTPClient(responses))

    resp = oauth_client.get(
        "/auth/callback",
        params={"code": "abc", "state": state},
        cookies={"oauth_state": state},
        follow_redirects=False,
    )
    assert resp.status_code == status.HTTP_302_FOUND
    assert "session_id" in resp.cookies
    assert resp.headers["location"] == "/docs"


@pytest.mark.unit
def test_set_openai_key_endpoint(oauth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting a new API key should succeed when subject is authenticated."""
    monkeypatch.setattr(oauth, "set_openai_key", lambda _subject, _key: None)
    app.dependency_overrides[oauth.get_authenticated_subject] = lambda: "subject-2"  # type: ignore[misc]

    resp = oauth_client.post("/auth/set-openai-key", json={"api_key": "sk-live"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["subject"] == "subject-2"


@pytest.mark.unit
def test_logout_clears_session(oauth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Logout endpoint should remove the session cookie."""
    destroyed: list[str] = []
    monkeypatch.setattr(oauth, "_destroy_session", lambda sid: destroyed.append(sid))
    oauth_client.cookies.set("session_id", "sid-1")
    resp = oauth_client.post("/auth/logout", follow_redirects=False)
    assert resp.status_code == status.HTTP_302_FOUND
    assert destroyed == ["sid-1"]
    assert "session_id=" in resp.headers.get("set-cookie", "")


@pytest.mark.unit
def test_whoami_returns_subject(oauth_client: TestClient) -> None:
    """Whoami endpoint should return the authenticated subject."""
    app.dependency_overrides[oauth.get_authenticated_subject] = lambda: "subject-3"  # type: ignore[misc]
    resp = oauth_client.get("/auth/whoami")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"subject": "subject-3"}
