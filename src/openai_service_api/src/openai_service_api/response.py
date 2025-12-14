# mypy: ignore-errors
"""Response and Conversation contracts for AI service."""

from abc import ABC, abstractmethod


class Response(ABC):
    """Abstract base class representing an AI-generated response."""

    @property
    @abstractmethod
    def content(self) -> str:
        """Return the text content of the AI response."""
        raise NotImplementedError

    @property
    @abstractmethod
    def tokens_used(self) -> int:
        """Return the number of tokens consumed."""
        raise NotImplementedError

    @property
    @abstractmethod
    def conversation_id(self) -> str | None:
        """Return the conversation ID this response belongs to."""
        raise NotImplementedError


class Conversation(ABC):
    """Abstract base class representing a conversation.

    Messages are stored as tuples of (role, content) where role is typically
    'user' or 'assistant' (or 'system' for system prompts).
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique conversation identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def messages(self) -> list[tuple[str, str]]:
        """Return all messages in the conversation in chronological order.

        Returns:
            list[tuple[str, str]]: List of (role, content) tuples.

        Example:
            [("user", "Hello"), ("assistant", "Hi there!")]

        """
        raise NotImplementedError

    @property
    @abstractmethod
    def created_at(self) -> str:
        """Return when the conversation was created."""
        raise NotImplementedError


def get_response(content: str, tokens_used: int, conversation_id: str | None) -> Response:
    """Return an instance of Response.

    Args:
        content (str): The text content of the AI response.
        tokens_used (int): The number of tokens consumed.
        conversation_id (str, optional): The conversation ID this response belongs to.

    Returns:
        Response: An instance conforming to the Response contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError


def get_conversation(
    conv_id: str,
    messages: list[tuple[str, str]],
    created_at: str,
) -> Conversation:
    """Return an instance of Conversation.

    Args:
        conv_id (str): The unique conversation identifier.
        messages (list[tuple[str, str]]): All messages as (role, content) tuples.
        created_at (str): When the conversation was created.

    Returns:
        Conversation: An instance conforming to the Conversation contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
