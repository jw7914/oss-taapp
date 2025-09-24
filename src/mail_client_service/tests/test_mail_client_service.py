
from unittest.mock import Mock

from message import Message

from mail_client_api import Client


def test_client_get_messages() -> None:
    """Verifies and demonstrates the contract for the `get_messages` method.

    This test ensures that any implementation of the `Client` protocol
    must have a `get_messages` method that returns an iterator of `Message` objects.
    """
    # ARRANGE: Create mocks that conform to our protocols.
    mock_message = Mock(spec=Message)
    mock_message.id = "msg_1"
    mock_message.subject = "Test Subject"

    mock_client = Mock(spec=Client)
    mock_client.get_messages.return_value = iter([mock_message])

    # ACT: Use the client as a consumer would.
    messages = mock_client.get_messages()
    first_message = next(messages, None)

    # ASSERT: Verify the interaction and the result.
    mock_client.get_messages.assert_called_once_with()
    assert first_message is not None
    assert first_message.id == "msg_1"
    assert first_message.subject == "Test Subject"


def test_client_get_message() -> None:
    """Verifies and demonstrates the contract for the `get_message` method."""
    # ARRANGE   
    mock_message = Mock(spec=Message)
    mock_message.id = "specific_msg_id"

    mock_client = Mock(spec=Client)
    mock_client.get_message.return_value = mock_message

    # ACT
    retrieved_message = mock_client.get_message(message_id="specific_msg_id")

    # ASSERT
    mock_client.get_message.assert_called_once_with(message_id="specific_msg_id")
    assert retrieved_message.id == "specific_msg_id"
