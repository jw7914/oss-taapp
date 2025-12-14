"""AI client implementation that implements the AIClient interface."""

import json
import uuid
from datetime import UTC, datetime

from openai import OpenAI

from .errors import MissingOpenAIKeyError
from .response import Conversation, Response, get_conversation, get_response
from .storage import delete_conversation, get_conversation_data, get_openai_key, save_conversation

__all__ = ["AIClientImpl", "MissingOpenAIKeyError"]

DEFAULT_MODEL = "gpt-4o-mini"


class AIClientImpl:
    """Concrete implementation of AIClient using OpenAI API."""

    def __init__(self, subject: str) -> None:
        """Initialize AI client for a specific user/subject.

        Args:
            subject: User identifier for API key lookup and conversation scoping.

        """
        self.subject = subject
        self._sdk = self._get_sdk()

    def _get_sdk(self) -> OpenAI:
        """Get OpenAI SDK client for the user.

        Returns:
            OpenAI client instance.

        Raises:
            MissingOpenAIKeyError: If user hasn't set an API key.

        """
        key = get_openai_key(self.subject)  
        if not key:
            error_msg = "OpenAI API key is not set for this user. Set it via the service."
            raise MissingOpenAIKeyError(error_msg)
        return OpenAI(api_key=key)

    def generate_response(
        self,
        messages: list[str],
        *,
        conversation_id: str | None = None,
    ) -> Response:
        """Generate a model response given messages and optional conversation ID.

        Args:
            messages: A list of message strings in the conversation.
            conversation_id: Optional conversation ID to continue existing
                conversation. If None, creates a new conversation.

        Returns:
            An AI-generated response.

        Raises:
            ValueError: If messages list is empty.
            RuntimeError: If the AI service fails to process the request.

        """
        if not messages:
            error_msg = "Messages list cannot be empty"
            raise ValueError(error_msg)

        openai_messages: list[dict[str, str]] = [{"role": "user", "content": msg} for msg in messages]

        if conversation_id:
            conv_data = get_conversation_data(conversation_id)
            if conv_data:
                _, _, messages_json = conv_data
                existing_messages = json.loads(messages_json)
                openai_messages = existing_messages + openai_messages
        try:
            resp = self._sdk.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=openai_messages,  # type: ignore[arg-type]
            )
        except Exception as e:
            error_msg = f"AI service failed to process request: {e}"
            raise RuntimeError(error_msg) from e

        content = resp.choices[0].message.content or ""
        tokens_used = resp.usage.total_tokens if resp.usage else 0

        if conversation_id:
            conv_data = get_conversation_data(conversation_id)
            if conv_data:
                _, created_at, _ = conv_data
            else:
                created_at = datetime.now(UTC).isoformat()

            updated_messages = [*openai_messages, {"role": "assistant", "content": content}]
            save_conversation(
                conv_id=conversation_id,
                subject=self.subject,
                created_at=created_at,
                messages_json=json.dumps(updated_messages),
            )
        else:
            conversation_id = self.create_conversation()
            created_at = datetime.now(UTC).isoformat()
            updated_messages = [*openai_messages, {"role": "assistant", "content": content}]
            save_conversation(
                conv_id=conversation_id,
                subject=self.subject,
                created_at=created_at,
                messages_json=json.dumps(updated_messages),
            )

        return get_response(content, tokens_used, conversation_id)

    def create_conversation(self) -> str:
        """Create a new conversation and return its ID.

        Returns:
            The conversation ID of the newly created conversation.

        Raises:
            RuntimeError: If the conversation could not be created.

        """
        try:
            conv_id = str(uuid.uuid4())
            created_at = datetime.now(UTC).isoformat()
            save_conversation(
                conv_id=conv_id,
                subject=self.subject,
                created_at=created_at,
                messages_json=json.dumps([]),
            )
        except Exception as e:
            error_msg = f"Could not create conversation: {e}"
            raise RuntimeError(error_msg) from e
        else:
            return conv_id

    def get_conversation(self, conversation_id: str) -> Conversation:
        """Retrieve a conversation by its ID.

        Args:
            conversation_id: The unique identifier of the conversation.

        Returns:
            The conversation object.

        Raises:
            ValueError: If conversation_id is invalid or not found.

        """
        conv_data = get_conversation_data(conversation_id)
        if not conv_data:
            error_msg = f"Conversation not found: {conversation_id}"
            raise ValueError(error_msg)

        _, created_at, messages_json = conv_data
        try:
            messages_list = json.loads(messages_json)
            messages = [(msg["role"], msg["content"]) for msg in messages_list]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            error_msg = f"Invalid conversation data: {e}"
            raise ValueError(error_msg) from e

        return get_conversation(conversation_id, messages, created_at)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages.

        Args:
            conversation_id: The unique identifier of the conversation.

        Returns:
            True if successfully deleted, False otherwise.

        Raises:
            ValueError: If conversation_id is invalid or not found.

        """
        deleted = bool(delete_conversation(conversation_id))
        if not deleted:
            error_msg = f"Conversation not found: {conversation_id}"
            raise ValueError(error_msg)
        return deleted
