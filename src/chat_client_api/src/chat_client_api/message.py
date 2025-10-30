"""Message contract - Core message representation."""

from abc import ABC, abstractmethod


class DiscordMessage(ABC):
    """Abstract base class representing an email message."""

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
        """Return the unique identifier of the message."""
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


def get_message(msg_id: str, raw_data: str) -> DiscordMessage:
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
