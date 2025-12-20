"""Tests for the OpenAI client service AI routes."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette import status

from openai_client_service.main import app
from openai_client_service.src.openai_client_service.dependencies import (
    get_ai_client,
    get_authenticated_subject,
)

try:
    from openai_client_impl import MissingOpenAIKeyError
except ImportError:  # pragma: no cover

    class MissingOpenAIKeyError(Exception):
        """Fallback error used when openai_client_impl is unavailable."""


TOKENS_USED = 7
DEFAULT_CONVERSATION_ID = "conv-new"
CREATED_CONVERSATION_ID = "conv-created"
CONVERSATION_LOOKUP_ID = "conv-1"
CONVERSATION_CREATED_AT = "2025-01-01T00:00:00Z"
HTTP_OK = status.HTTP_200_OK
HTTP_UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED
HTTP_BAD_REQUEST = status.HTTP_400_BAD_REQUEST


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Configure TestClient with dependency overrides and a fake AI client."""
    fake_client = FakeAIClient()
    app.dependency_overrides[get_ai_client] = lambda: fake_client  # type: ignore[return-value]
    app.dependency_overrides[get_authenticated_subject] = lambda: "user-1"  # type: ignore[return-value]

    main_module = import_module("openai_client_service.main")
    monkeypatch.setattr(main_module, "init_db", lambda: None, raising=False)

    test_client = TestClient(app)
    test_client.app.state.fake_ai_client = fake_client  # type: ignore[attr-defined]
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


class FakeAIClient:
    """Test double implementing the AI client surface."""

    def __init__(self) -> None:
        """Initialise the fake client flags and captured call storage."""
        self.saved_args: list[tuple[str, dict[str, Any]]] = []
        self.raise_missing = False
        self.raise_value = False
        self.raise_runtime = False

    def generate_response(self, messages: list[str], *, conversation_id: str | None = None) -> FakeResponse:
        """Simulate generating a response."""
        if self.raise_missing:
            error_message = "missing key"
            raise MissingOpenAIKeyError(error_message)
        if self.raise_value:
            error_message = "bad request"
            raise ValueError(error_message)
        if self.raise_runtime:
            error_message = "server down"
            raise RuntimeError(error_message)
        self.saved_args.append(("generate", {"messages": messages, "conversation_id": conversation_id}))
        return FakeResponse(content="hi", tokens_used=TOKENS_USED, conversation_id=conversation_id or DEFAULT_CONVERSATION_ID)

    def create_conversation(self) -> str:
        """Simulate creating a conversation."""
        if self.raise_missing:
            error_message = "missing key"
            raise MissingOpenAIKeyError(error_message)
        if self.raise_runtime:
            error_message = "cannot create"
            raise RuntimeError(error_message)
        self.saved_args.append(("create", {}))
        return CREATED_CONVERSATION_ID

    def get_conversation(self, conversation_id: str) -> FakeConversation:
        """Simulate retrieving a conversation."""
        if self.raise_missing:
            error_message = "missing key"
            raise MissingOpenAIKeyError(error_message)
        if self.raise_value:
            error_message = "not found"
            raise ValueError(error_message)
        self.saved_args.append(("get", {"conversation_id": conversation_id}))
        return FakeConversation(conversation_id, [("user", "hello"), ("assistant", "hi")], CONVERSATION_CREATED_AT)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Simulate deleting a conversation."""
        if self.raise_missing:
            error_message = "missing key"
            raise MissingOpenAIKeyError(error_message)
        if self.raise_value:
            error_message = "not found"
            raise ValueError(error_message)
        self.saved_args.append(("delete", {"conversation_id": conversation_id}))
        return True


class FakeResponse:
    """Simple value object that mirrors the real Response dataclass."""

    def __init__(self, content: str, tokens_used: int, conversation_id: str | None) -> None:
        """Store response data for downstream assertions."""
        self.content = content
        self.tokens_used = tokens_used
        self.conversation_id = conversation_id


class FakeConversation:
    """Simple value object for conversation payloads."""

    def __init__(self, conv_id: str, messages: list[tuple[str, str]], created_at: str) -> None:
        """Store conversation metadata for downstream assertions."""
        self.id = conv_id
        self.messages = messages
        self.created_at = created_at


@pytest.mark.unit
def test_generate_response_success(client: TestClient) -> None:
    """POST /ai/generate-response should succeed with valid payload."""
    payload = {"messages": ["hello"], "conversation_id": None}
    resp = client.post("/ai/generate-response", json=payload)
    assert resp.status_code == HTTP_OK
    data = resp.json()
    assert data["content"] == "hi"
    assert data["tokens_used"] == TOKENS_USED
    assert data["conversation_id"] == DEFAULT_CONVERSATION_ID


@pytest.mark.unit
def test_generate_response_handles_missing_key(client: TestClient) -> None:
    """Missing API keys should return HTTP 401."""
    fake_client: FakeAIClient = client.app.state.fake_ai_client  # type: ignore[attr-defined]
    fake_client.raise_missing = True

    resp = client.post("/ai/generate-response", json={"messages": ["hi"]})
    assert resp.status_code == HTTP_UNAUTHORIZED
    detail = resp.json()["detail"]
    assert "hint" in detail


@pytest.mark.unit
def test_generate_response_handles_value_error(client: TestClient) -> None:
    """Backend value errors should surface as HTTP 400."""
    fake_client: FakeAIClient = client.app.state.fake_ai_client  # type: ignore[attr-defined]
    fake_client.raise_value = True

    resp = client.post("/ai/generate-response", json={"messages": ["hi"]})
    assert resp.status_code == HTTP_BAD_REQUEST
    assert "bad request" in resp.text.lower()


@pytest.mark.unit
def test_create_conversation_success(client: TestClient) -> None:
    """POST /ai/conversations should create a new conversation."""
    resp = client.post("/ai/conversations")
    assert resp.status_code == HTTP_OK
    assert resp.json() == {"conversation_id": CREATED_CONVERSATION_ID}


@pytest.mark.unit
def test_get_conversation_success(client: TestClient) -> None:
    """GET /ai/conversations/{id} should return conversation details."""
    resp = client.get(f"/ai/conversations/{CONVERSATION_LOOKUP_ID}")
    assert resp.status_code == HTTP_OK
    data = resp.json()
    assert data["id"] == CONVERSATION_LOOKUP_ID
    assert data["messages"][0] == ["user", "hello"]


@pytest.mark.unit
def test_delete_conversation_success(client: TestClient) -> None:
    """DELETE /ai/conversations/{id} should return success flag."""
    resp = client.delete(f"/ai/conversations/{CONVERSATION_LOOKUP_ID}")
    assert resp.status_code == HTTP_OK
    assert resp.json()["ok"] is True
