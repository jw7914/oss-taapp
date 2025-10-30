"""Message contract - Core message representation."""

from abc import ABC, abstractmethod


class ChatMessage(ABC):
    """Abstract base class representing an chat message."""

    @property
    @abstractmethod
    def message_id(self) -> str:
        """Return the unique identifier of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def author(self) -> str:
        """Return the sender's info ."""
        raise NotImplementedError

    @property
    @abstractmethod
    def author_username(self) -> str:
        """Return the sender's info ."""
        raise NotImplementedError

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """Return the unique identifier of the channel."""
        raise NotImplementedError

    @property
    @abstractmethod
    def timestamp(self) -> str:
        """Return the date the message was sent."""
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self) -> str:
        """Return the plain text content of the message."""
        raise NotImplementedError


class ChatChannel(ABC):
    """Abstract base class representing an chat channel."""

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """Return the unique identifier of the channel."""
        raise NotImplementedError

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the unique identifier of the channel."""
        raise NotImplementedError

    @property
    @abstractmethod
    def channel_type(self) -> int:
        """Return the type of the channel."""
        raise NotImplementedError

    @property
    @abstractmethod
    def channel_position(self) -> int:
        """Return the type of the channel."""
        raise NotImplementedError


def get_message(msg_id: str, raw_data: str) -> ChatMessage:
    """Return an instance of a Message.

    Args:
        msg_id (str): The unique identifier for the message.
        raw_data (str): The raw data used to construct the message.

    Returns:
    Message: An instance conforming to the Message contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError

def get_channel(channel_id: str, raw_data: dict[str, str]) -> ChatChannel:
    """Return an instance of a channel.

    Args:
        channel_id (str): The unique identifier for the message.
        raw_data (dict[str, str]): The raw data used to construct the channel

    Returns:
    Channel: An instance conforming to the Channel contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError

