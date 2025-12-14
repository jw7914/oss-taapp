"""Response and Conversation implementations for OpenAI client."""
from openai_service_api.response import (
    Conversation as ConversationABC,
)
from openai_service_api.response import Response as ResponseABC


class Response(ResponseABC):
    """Concrete implementation of AI response."""

    def __init__(self, content: str, tokens_used: int, conversation_id: str | None = None) -> None:
        """Initialize a response.

        Args:
            content: The text content of the AI response.
            tokens_used: The number of tokens consumed.
            conversation_id: Optional conversation ID.

        """
        self._content = content
        self._tokens_used = tokens_used
        self._conversation_id = conversation_id

    @property
    def content(self) -> str:
        """Return the text content of the AI response."""
        return self._content

    @property
    def tokens_used(self) -> int:
        """Return the number of tokens consumed."""
        return self._tokens_used

    @property
    def conversation_id(self) -> str | None:
        """Return the conversation ID this response belongs to."""
        return self._conversation_id


class Conversation(ConversationABC):
    """Concrete implementation of a conversation."""

    def __init__(
        self,
        conv_id: str,
        messages: list[tuple[str, str]],
        created_at: str,
    ) -> None:
        """Initialize a conversation.

        Args:
            conv_id: The unique conversation identifier.
            messages: All messages as (role, content) tuples.
            created_at: When the conversation was created (ISO format string).

        """
        self._id = conv_id
        self._messages = messages
        self._created_at = created_at

    @property
    def id(self) -> str:
        """Return the unique conversation identifier."""
        return self._id

    @property
    def messages(self) -> list[tuple[str, str]]:
        """Return all messages in the conversation in chronological order.

        Returns:
            List of (role, content) tuples.

        Example:
            [("user", "Hello"), ("assistant", "Hi there!")]

        """
        return self._messages

    @property
    def created_at(self) -> str:
        """Return when the conversation was created."""
        return self._created_at


def get_response(content: str, tokens_used: int, conversation_id: str | None) -> Response:
    """Return an instance of Response.

    Args:
        content: The text content of the AI response.
        tokens_used: The number of tokens consumed.
        conversation_id: The conversation ID this response belongs to.

    Returns:
        Response: An instance conforming to the Response contract.

    """
    return Response(content, tokens_used, conversation_id)


def get_conversation(conv_id: str, messages: list[tuple[str, str]], created_at: str) -> Conversation:
    """Return an instance of Conversation.

    Args:
        conv_id: The unique conversation identifier.
        messages: All messages as (role, content) tuples.
        created_at: When the conversation was created.

    Returns:
        Conversation: An instance conforming to the Conversation contract.

    """
    return Conversation(conv_id, messages, created_at)
