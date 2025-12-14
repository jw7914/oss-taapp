"""Tests for the `openai_client_impl.ai_client` module."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime as real_datetime
from types import SimpleNamespace
from typing import Any

import pytest

from openai_client_impl.ai_client import AIClientImpl, MissingOpenAIKeyError

DEFAULT_SUBJECT = "user"
DEFAULT_API_KEY = "sk-test"
DEFAULT_TOTAL_TOKENS = 11
DEFAULT_ASSISTANT_RESPONSE = "ok-response"
DEFAULT_CONVERSATION_ID = "conv-123"
DEFAULT_CREATED_AT = "2025-01-01T00:00:00Z"
EXPECTED_SAVE_CALLS = 2


@dataclass
class FakeResponse:
    """Lightweight response data container used by the stubs."""

    content: str
    tokens_used: int
    conversation_id: str | None


class DummyCompletions:
    """Collects completion calls made by the client under test."""

    def __init__(self) -> None:
        """Initialise storage for recorded completion payloads."""
        self.calls: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> Any:
        """Record payload and return a fake OpenAI completion."""
        self.calls.append(payload)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=DEFAULT_ASSISTANT_RESPONSE))],
            usage=SimpleNamespace(total_tokens=DEFAULT_TOTAL_TOKENS),
        )


def _patch_openai_sdk(
    monkeypatch: pytest.MonkeyPatch,
    captured: dict[str, Any],
    *,
    subject: str,
    api_key: str,
) -> DummyCompletions:
    """Patch OpenAI SDK interactions to use deterministic fakes."""

    def fake_get_openai_key(requested_subject: str) -> str:
        return api_key if requested_subject == subject else ""

    monkeypatch.setattr("openai_client_impl.ai_client.get_openai_key", fake_get_openai_key)

    dummy_completions = DummyCompletions()

    class DummyOpenAI:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.chat = SimpleNamespace(completions=dummy_completions)

    monkeypatch.setattr("openai_client_impl.ai_client.OpenAI", DummyOpenAI)
    captured["completions"] = dummy_completions
    return dummy_completions


def _patch_storage(monkeypatch: pytest.MonkeyPatch, captured: dict[str, Any]) -> None:
    """Patch storage helper functions to capture inputs."""

    def fake_save_conversation(**kwargs: Any) -> None:
        captured["saved"].append(kwargs)

    def fake_delete_conversation(conv_id: str) -> bool:
        captured.setdefault("deleted", set()).add(conv_id)
        return True

    def fake_get_conversation_data(conv_id: str) -> tuple[str, str, str] | None:
        captured["conversation_queries"].append(conv_id)
        return captured.get("conversation_lookup", {}).get(conv_id)

    def fake_get_response(content: str, tokens_used: int, conversation_id: str | None) -> FakeResponse:
        resp = FakeResponse(content=content, tokens_used=tokens_used, conversation_id=conversation_id)
        captured["responses"].append(resp)
        return resp

    def fake_get_conversation(
        conv_id: str,
        messages: list[tuple[str, str]],
        created_at: str,
    ) -> tuple[str, list[tuple[str, str]], str]:
        result = (conv_id, messages, created_at)
        captured["built_conversation"] = result
        return result

    monkeypatch.setattr("openai_client_impl.ai_client.save_conversation", fake_save_conversation)
    monkeypatch.setattr("openai_client_impl.ai_client.delete_conversation", fake_delete_conversation)
    monkeypatch.setattr("openai_client_impl.ai_client.get_conversation_data", fake_get_conversation_data)
    monkeypatch.setattr("openai_client_impl.ai_client.get_response", fake_get_response)
    monkeypatch.setattr("openai_client_impl.ai_client.get_conversation", fake_get_conversation)


def _patch_time_and_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure datetime/uuid helpers return deterministic data."""

    class DummyDateTimeModule:
        UTC = UTC

        @staticmethod
        def now(tz: UTC) -> real_datetime:
            return real_datetime(2025, 1, 1, tzinfo=tz)

    monkeypatch.setattr("openai_client_impl.ai_client.datetime", DummyDateTimeModule)
    monkeypatch.setattr("openai_client_impl.ai_client.uuid", SimpleNamespace(uuid4=lambda: DEFAULT_CONVERSATION_ID))


def _install_common_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    subject: str = DEFAULT_SUBJECT,
    api_key: str = DEFAULT_API_KEY,
) -> dict[str, Any]:
    """Install baseline stubs for storage and OpenAI SDK interactions."""
    captured: dict[str, Any] = {"saved": [], "responses": [], "conversation_queries": []}
    _patch_openai_sdk(monkeypatch, captured, subject=subject, api_key=api_key)
    _patch_storage(monkeypatch, captured)
    _patch_time_and_uuid(monkeypatch)
    return captured


def test_generate_response_creates_conversation_and_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    """New conversations should be created and persisted."""
    captured = _install_common_stubs(monkeypatch)

    client = AIClientImpl(subject="user")
    resp = client.generate_response(["hello there"])

    assert isinstance(resp, FakeResponse)
    assert resp.content == "ok-response"
    assert resp.tokens_used == DEFAULT_TOTAL_TOKENS
    assert resp.conversation_id == DEFAULT_CONVERSATION_ID

    # create_conversation + final save -> two calls
    save_calls = captured["saved"]
    assert len(save_calls) == EXPECTED_SAVE_CALLS
    first_call, second_call = captured["saved"]
    assert first_call["conv_id"] == DEFAULT_CONVERSATION_ID
    assert json.loads(second_call["messages_json"])[-1]["content"] == DEFAULT_ASSISTANT_RESPONSE
    assert captured["completions"].calls[0]["model"] == "gpt-4o-mini"


def test_generate_response_appends_existing_conversation(monkeypatch: pytest.MonkeyPatch) -> None:
    """When conversation history exists, messages should be appended and saved once."""
    captured = _install_common_stubs(monkeypatch)
    existing_messages = json.dumps([{"role": "user", "content": "prior"}])
    captured["conversation_lookup"] = {"conv-999": ("conv-999", "2024-01-01T00:00:00Z", existing_messages)}

    client = AIClientImpl(subject="user")
    resp = client.generate_response(["again"], conversation_id="conv-999")

    assert resp.conversation_id == "conv-999"
    # Only update save (no create)
    assert len(captured["saved"]) == 1
    saved_payload = captured["saved"][0]
    saved_messages = json.loads(saved_payload["messages_json"])
    assert saved_messages[0]["content"] == "prior"
    assert saved_messages[-1]["role"] == "assistant"
    assert captured["conversation_queries"] == ["conv-999", "conv-999"]


def test_generate_response_requires_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty message list should raise ValueError before contacting the API."""
    _install_common_stubs(monkeypatch)
    client = AIClientImpl(subject="user")

    with pytest.raises(ValueError, match="Messages list cannot be empty"):
        client.generate_response([])


def test_generate_response_propagates_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exceptions from the OpenAI SDK should be wrapped in RuntimeError."""
    captured = _install_common_stubs(monkeypatch)

    def boom(**_: Any) -> None:
        error_message = "network boom"
        raise RuntimeError(error_message)

    captured["completions"].create = boom  # type: ignore[assignment]

    client = AIClientImpl(subject="user")

    with pytest.raises(RuntimeError, match="network boom"):
        client.generate_response(["hi"])


def test_create_conversation_handles_storage_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Storage errors should surface as RuntimeError."""
    _install_common_stubs(monkeypatch)

    def fail_save(**_: Any) -> None:
        error_message = "disk-full"
        raise OSError(error_message)

    monkeypatch.setattr("openai_client_impl.ai_client.save_conversation", fail_save)

    client = AIClientImpl(subject="user")

    with pytest.raises(RuntimeError, match="disk-full"):
        client.create_conversation()


def test_get_conversation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid stored data should round-trip through get_conversation."""
    captured = _install_common_stubs(monkeypatch)
    messages_json = json.dumps(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
    )
    captured["conversation_lookup"] = {"conv-42": ("conv-42", DEFAULT_CREATED_AT, messages_json)}

    client = AIClientImpl(subject="user")
    conv = client.get_conversation("conv-42")

    assert conv[0] == "conv-42"
    assert conv[1][0] == ("user", "hello")
    assert conv[2] == "2025-01-01T00:00:00Z"


def test_get_conversation_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing conversations should raise ValueError."""
    _install_common_stubs(monkeypatch)
    client = AIClientImpl(subject="user")

    with pytest.raises(ValueError, match="Conversation not found"):
        client.get_conversation("missing")


def test_get_conversation_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid JSON payloads should raise ValueError."""
    captured = _install_common_stubs(monkeypatch)
    captured["conversation_lookup"] = {"conv-bad": ("conv-bad", DEFAULT_CREATED_AT, "not-json")}
    client = AIClientImpl(subject="user")

    with pytest.raises(ValueError, match="Invalid conversation data"):
        client.get_conversation("conv-bad")


def test_delete_conversation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_conversation should return True when deletion succeeds."""
    captured = _install_common_stubs(monkeypatch)

    client = AIClientImpl(subject="user")
    assert client.delete_conversation("conv-1") is True
    assert "conv-1" in captured["deleted"]


def test_delete_conversation_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed deletions should raise ValueError."""
    _install_common_stubs(monkeypatch)

    def fake_delete(conv_id: str) -> bool:
        return False

    monkeypatch.setattr("openai_client_impl.ai_client.delete_conversation", fake_delete)

    client = AIClientImpl(subject="user")
    with pytest.raises(ValueError, match="Conversation not found"):
        client.delete_conversation("conv-x")


def test_missing_openai_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Users without an API key should receive MissingOpenAIKeyError."""
    monkeypatch.setattr("openai_client_impl.ai_client.get_openai_key", lambda _: "")
    with pytest.raises(MissingOpenAIKeyError):
        AIClientImpl(subject="user")

