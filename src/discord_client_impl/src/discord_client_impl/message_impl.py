"""Discord Message and Channel Implementation.

This module provides concrete implementations of the ChatMessage and ChatChannel
abstract base classes from the chat_client_api.
"""

from typing import Any

from chat_client_api.message import ChatChannel, ChatMessage

import chat_client_api
from chat_client_api import message


class DiscordMessage(ChatMessage):
    """Concrete implementation of ChatMessage for a Discord message."""

    def __init__(self, raw_data: dict[str, Any]) -> None:
        """Initialize a Discord message from raw API data.

        Args:
            raw_data: Raw message data from Discord API.

        """
        self._raw_data = raw_data

    @property
    def id(self) -> str:
        """Return the unique identifier of the message."""
        return str(self._raw_data.get("id", ""))

    @property
    def message_id(self) -> str:
        """Compatibility property required by ChatMessage API."""
        return self.id

    @property
    def channel_id(self) -> str:
        """Return the ID of the channel where the message was sent."""
        return str(self._raw_data.get("channel_id", ""))

    @property
    def author_id(self) -> str:
        """Return the ID of the message author."""
        author = self._raw_data.get("author", {})
        return str(author.get("id", "")) if isinstance(author, dict) else ""

    @property
    def author(self) -> str:
        """Compatibility property required by ChatMessage API (author id)."""
        return self.author_id

    @property
    def author_name(self) -> str:
        """Return the display name of the message author."""
        author = self._raw_data.get("author", {})
        if isinstance(author, dict):
            # Prefer global_name, fallback to username
            return str(author.get("global_name") or author.get("username", "Unknown"))
        return "Unknown"

    @property
    def author_username(self) -> str:
        """Compatibility property required by ChatMessage API (author username)."""
        return self.author_name

    @property
    def content(self) -> str:
        """Return the text content of the message."""
        return str(self._raw_data.get("content", ""))

    @property
    def timestamp(self) -> str:
        """Return the timestamp when the message was created (ISO 8601 format)."""
        return str(self._raw_data.get("timestamp", ""))

    @property
    def edited_timestamp(self) -> str | None:
        """Return the timestamp when the message was last edited, or None if never edited."""
        edited = self._raw_data.get("edited_timestamp")
        return str(edited) if edited else None


class DiscordChannel(ChatChannel):
    """Discord implementation of Channel."""

    def __init__(self, raw_data: dict[str, Any]) -> None:
        """Initialize a Discord channel from raw API data.

        Args:
            raw_data: Raw channel data from Discord API.

        """
        self._raw_data = raw_data

    @property
    def id(self) -> str:
        """Return the unique identifier of the channel."""
        return str(self._raw_data.get("id", ""))

    @property
    def channel_id(self) -> str:
        """Compatibility property required by ChatChannel API."""
        return self.id

    @property
    def name(self) -> str:
        """Return the name of the channel."""
        # DM channels may not have a name
        name = self._raw_data.get("name")
        if name:
            return str(name)
        # For DM channels, construct a name from recipients
        recipients = self._raw_data.get("recipients")
        if isinstance(recipients, list):
            if recipients:  # Non-empty recipient list
                usernames = [
                    r.get("username", "Unknown") for r in recipients if isinstance(r, dict)
                ]
                return f"DM: {', '.join(usernames)}" if usernames else "Direct Message"
            # Empty recipient list for DM
            return "Direct Message"
        return "Unknown Channel"

    @property
    def channel_name(self) -> str:
        """Compatibility property required by ChatChannel API."""
        return self.name

    @property
    def channel_type(self) -> int:
        """Return the integer type code of the channel.

        The ChatChannel API expects an int code. Discord returns an integer
        in the `type` field; we coerce to int and return 0 on error.
        """
        try:
            return int(self._raw_data.get("type", 0))
        except (TypeError, ValueError):
            return 0

    @property
    def channel_position(self) -> int:
        """Return the position of the channel in the guild (or 0 for DMs)."""
        try:
            return int(self._raw_data.get("position", 0))
        except (TypeError, ValueError):
            return 0


def get_chat_message_impl(msg_id: str, raw_data: str) -> message.ChatMessage:
    """Return an instance of the concrete DiscordMessage implementation."""
    return DiscordMessage(msg_id=msg_id, raw_data=raw_data)


def register() -> None:
    """Register the Discord message implementation with the message abstraction."""
    message.get_message = get_chat_message_impl
    chat_client_api.get_message = get_chat_message_impl
