"""Core AI service contract definitions."""

from abc import ABC, abstractmethod

from openai_service_api.src.openai_service_api.response import (
    Conversation,
    Response,
)


class AIClient(ABC):
    """Abstract base class for AI service operations."""

    @abstractmethod
    def generate_response(
        self,
        messages: list[str],
        *,
        conversation_id: str | None = None,
    ) -> Response:
        """Generate a model response given messages and optional conversation ID.

        Args:
            messages (list[str]): A list of message strings in the conversation.
            conversation_id (str, optional): Optional conversation ID to continue existing
                conversation. If None, creates a new conversation. Defaults to None.

        Returns:
            Response: An AI-generated response.

        Raises:
            ValueError: If messages list is empty.
            RuntimeError: If the AI service fails to process the request.

        """
        raise NotImplementedError

    @abstractmethod
    def create_conversation(self) -> str:
        """Create a new conversation and return its ID.

        Returns:
            str: The conversation ID of the newly created conversation.

        Raises:
            RuntimeError: If the conversation could not be created.

        """
        raise NotImplementedError

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Conversation:
        """Retrieve a conversation by its ID.

        Args:
            conversation_id (str): The unique identifier of the conversation.

        Returns:
            Conversation: The conversation object.

        Raises:
            ValueError: If conversation_id is invalid or not found.

        """
        raise NotImplementedError

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages.

        Args:
            conversation_id (str): The unique identifier of the conversation.

        Returns:
            bool: True if successfully deleted, False otherwise.

        Raises:
            ValueError: If conversation_id is invalid or not found.

        """
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> AIClient:
    """Return an instance of an AI Client.

    Args:
        interactive (bool, optional): Whether to prompt for user input if needed.
            Defaults to False.

    Returns:
        AIClient: An instance of the AI client implementation.

    Raises:
        NotImplementedError: If no implementation has been registered.

    """
    raise NotImplementedError
