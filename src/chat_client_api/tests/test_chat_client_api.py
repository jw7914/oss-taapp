"""Tests for the chat client API abstract base classes.

This module contains unit tests that verify the contracts and behavior
of the chat_client_api.ChatClient and chat_client_api.ChatMessage abstractions.
These tests use mocks to demonstrate how implementations should behave
and serve as documentation for the expected API contracts.
"""

from unittest.mock import Mock

from chat_client_api.client import ChatClient
from chat_client_api.message import ChatMessage


def test_client_get_messages() -> None:
    """Verifies and demonstrates the contract for the `get_messages` method.

    This test ensures that any implementation of the `ChatClient` abstraction
    must have a `get_messages` method that returns an iterator of `ChatMessage` objects.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_message = Mock(spec=ChatMessage)
    mock_message.message_id = "msg_1"
    mock_message.channel_id = "channel_123"
    mock_message.content = "Test message content"
    mock_message.author = "Test Author"
    mock_message.author_username = "testauthor"
    mock_message.timestamp = "2024-01-01T12:00:00Z"

    mock_client = Mock(spec=ChatClient)
    mock_client.get_messages.return_value = iter([mock_message])

    # ACT: Use the client as a consumer would.
    messages = mock_client.get_messages(channel_id="channel_123", max_results=10)
    first_message = next(messages, None)

    # ASSERT: Verify the interaction and the result.
    mock_client.get_messages.assert_called_once_with(channel_id="channel_123", max_results=10)
    assert first_message is not None
    assert first_message.message_id == "msg_1"
    assert first_message.channel_id == "channel_123"
    assert first_message.content == "Test message content"
    assert first_message.author == "Test Author"
    assert first_message.author_username == "testauthor"
    assert first_message.timestamp == "2024-01-01T12:00:00Z"


def test_client_get_message() -> None:
    """Verifies and demonstrates the contract for the `get_message` method."""
    # ARRANGE
    mock_message = Mock(spec=ChatMessage)
    mock_message.message_id = "specific_msg_id"
    mock_message.channel_id = "channel_456"
    mock_message.content = "Specific message content"
    mock_message.author = "Message Author"
    mock_message.author_username = "msgauthor"
    mock_message.timestamp = "2024-01-02T15:30:00Z"

    mock_client = Mock(spec=ChatClient)
    mock_client.get_message.return_value = mock_message

    # ACT
    retrieved_message = mock_client.get_message(
        channel_id="channel_456", message_id="specific_msg_id",
    )

    # ASSERT
    mock_client.get_message.assert_called_once_with(
        channel_id="channel_456", message_id="specific_msg_id",
    )
    assert retrieved_message.message_id == "specific_msg_id"
    assert retrieved_message.channel_id == "channel_456"
    assert retrieved_message.content == "Specific message content"
    assert retrieved_message.author == "Message Author"
    assert retrieved_message.author_username == "msgauthor"
    assert retrieved_message.timestamp == "2024-01-02T15:30:00Z"


def test_client_delete_message() -> None:
    """Verifies and demonstrates the contract for the `delete_message` method."""
    # ARRANGE
    mock_client = Mock(spec=ChatClient)
    mock_client.delete_message.return_value = True

    # ACT
    success = mock_client.delete_message(channel_id="channel_789", message_id="msg_to_delete")

    # ASSERT
    mock_client.delete_message.assert_called_once_with(
        channel_id="channel_789", message_id="msg_to_delete",
    )
    assert success is True
