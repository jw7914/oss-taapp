"""Core chat client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from chat_client_api.message import ChatChannel, ChatMessage

__all__ = ["ChatClient", "get_client"]


class ChatClient(ABC):
    """Abstract base class representing a chat client for chat operations."""

    @abstractmethod
    def get_channels(self) -> Iterator[ChatChannel]:
        """Return an iterator over all channels visible to the client."""
        raise NotImplementedError

    @abstractmethod
    def get_channel(self, channel_id: str) -> ChatChannel:
        """Retrieve a specific channel by its unique identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_message(self, channel_id: str, message_id: str) -> ChatMessage:
        """Return a message by its ID."""
        raise NotImplementedError

    @abstractmethod
    def send_message(self, channel_id: str, content: str) -> ChatMessage:
        """Send new message with the given content to a channel, return created message object."""
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, channel_id: str, max_results: int = 10) -> Iterator[ChatMessage]:
        """Return an iterator of messages from the inbox."""
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> ChatClient:
    """Return an instance of a Mail Client."""
    raise NotImplementedError
