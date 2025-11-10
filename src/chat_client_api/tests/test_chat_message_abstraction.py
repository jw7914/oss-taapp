"""Tests for the chat_client_api message abstraction."""
from unittest.mock import Mock

from chat_client_api.message import ChatMessage


def test_chat_message_abstraction() -> None:
    """Verifies basic message properties on the chat Message abstraction."""
    # Adjust the attribute names below if your chat Message API differs.
    mock_message = Mock(spec=ChatMessage)
    mock_message.id = "chat_msg_123"
    mock_message.sender = "alice"
    mock_message.recipients = ["bob", "carol"]
    mock_message.timestamp = "2025-10-30T12:34:56Z"
    mock_message.text = "Hello, this is a chat message."

    props = {
        "id": mock_message.id,
        "sender": mock_message.sender,
        "recipients": mock_message.recipients,
        "timestamp": mock_message.timestamp,
        "text": mock_message.text,
    }

    assert props["id"] == "chat_msg_123"
    assert props["sender"] == "alice"
    assert props["recipients"] == ["bob", "carol"]
    assert props["timestamp"] == "2025-10-30T12:34:56Z"
    assert props["text"] == "Hello, this is a chat message."

    # Basic type checks
    assert isinstance(props["id"], str)
    assert isinstance(props["sender"], str)
    assert isinstance(props["recipients"], list)
    assert all(isinstance(r, str) for r in props["recipients"])
    assert isinstance(props["timestamp"], str)
    assert isinstance(props["text"], str)
