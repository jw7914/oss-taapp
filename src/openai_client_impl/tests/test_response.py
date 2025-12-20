"""Tests for the response and conversation helpers."""

from __future__ import annotations

from openai_client_impl.response import Conversation, Response, get_conversation, get_response

CONTENT_HELLO = "hello"
TOKENS_FORTY_TWO = 42
CONVERSATION_ID_ONE = "conv-1"
CONVERSATION_CREATED_AT = "2025-01-01T00:00:00Z"


def test_response_properties() -> None:
    """Response instances should expose the provided attributes."""
    resp = Response(CONTENT_HELLO, TOKENS_FORTY_TWO, CONVERSATION_ID_ONE)
    assert resp.content == CONTENT_HELLO
    assert resp.tokens_used == TOKENS_FORTY_TWO
    assert resp.conversation_id == CONVERSATION_ID_ONE


def test_get_response_factory() -> None:
    """get_response should produce Response objects with matching values."""
    resp = get_response("ok", 10, None)
    assert isinstance(resp, Response)
    assert resp.conversation_id is None


def test_conversation_properties() -> None:
    """Conversation dataclass should expose id/messages/timestamp."""
    convo = Conversation(
        "c-1",
        [("user", "hi"), ("assistant", "hey")],
        CONVERSATION_CREATED_AT,
    )
    assert convo.id == "c-1"
    assert convo.messages[0] == ("user", "hi")
    assert convo.created_at == CONVERSATION_CREATED_AT


def test_get_conversation_factory() -> None:
    """get_conversation should construct Conversation instances."""
    convo = get_conversation("c-2", [("user", "hi")], CONVERSATION_CREATED_AT)
    assert isinstance(convo, Conversation)
    assert convo.messages[-1][1] == "hi"
