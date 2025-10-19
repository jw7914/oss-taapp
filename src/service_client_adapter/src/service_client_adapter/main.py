"""Mail client service adapter.

Handles authentication, message retrieval, and related API calls.
"""

from mail_client_api.message import Message
from mail_client_service_api_client.api.authentication import login
from mail_client_service_api_client.api.messages import (
    delete_message,
    get_message,
    get_messages,
    mark_message_as_read,
)
from mail_client_service_api_client.client import Client
from mail_client_service_api_client.models.http_validation_error import HTTPValidationError
from mail_client_service_api_client.models.message_response import MessageContents, MessageResponse


class ServiceClientAdapter(Client):
    """Adapter class for interacting with the mail client API using a fast API client.

    Provides methods to get, delete, and mark messages as read, as well as to retrieve messages from inbox.
    """

    def __init__(self) -> None:
        """Initialize client adapter."""
        self.Client = Client(base_url = "http://127.0.0.1:8000")

    def login(self) -> None:
        """Authenticate the user."""
        login.sync_detailed(
            client = self.Client,
        )

    def get_message(self, message_id: str) -> Message:
        """Return a message by its ID."""
        message = get_message.sync_detailed(
            message_id = message_id,
            client = self.Client,
        ) #response[messageResponse]
        content = message.parsed
        if isinstance(content, HTTPValidationError) or content is None:
            msg = "Validation error"
            raise ValueError(msg)

        return MessageContents(MessageResponse(**content["message"]))

    def delete_message(self, message_id: str) -> bool:
        """Delete a message by its ID."""
        result = delete_message.sync_detailed(
            message_id = message_id,
            client = self.Client,
        )
        deleted = result.parsed
        if isinstance(deleted, HTTPValidationError) or deleted is None:
            msg = "Validation error"
            raise ValueError(msg)
        return "message" in deleted
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read by its ID."""
        result = mark_message_as_read.sync_detailed(
            message_id = message_id,
            client = self.Client,
        )
        read = result.parsed
        if isinstance(read, HTTPValidationError) or read is None:
            msg = "Validation error"
            raise ValueError(msg)
        return "message" in read

    def get_messages(self, max_results: int = 10) -> list[Message]:
        """Return an iterator of messages from the inbox."""
        messages = get_messages.sync_detailed(
            client = self.Client,
            max_results=max_results,
        )
        content = messages.parsed
        if isinstance(content, HTTPValidationError) or content is None:
            msg = "Validation error"
            raise ValueError(msg)
        return [MessageContents(MessageResponse(**message)) for message in content]
