"""Adapter that calls the discord service via the generated API client.

This adapter implements the `chat_client_api.ChatClient` interface so it can be
swapped in for the local `discord_client_impl.DiscordClient`.
"""

import contextlib
import json
import webbrowser
from collections.abc import Iterator
from http import HTTPStatus
from typing import Any

from chat_client_api.client import ChatClient
from chat_client_api.message import ChatChannel, ChatMessage
from discord_client_impl.message_impl import DiscordChannel, DiscordMessage
from discord_client_service_api_client.api.authentication import auth_callback, login
from discord_client_service_api_client.api.channel import get_channel
from discord_client_service_api_client.api.messages import (
    delete_message,
    get_message,
    get_messages,
    send_message,
)
from discord_client_service_api_client.api.user import get_current_user, get_users
from discord_client_service_api_client.client import AuthenticatedClient, Client
from discord_client_service_api_client.models.http_validation_error import HTTPValidationError

# HTTP status range for redirects (inclusive lower, exclusive upper)
REDIRECT_STATUS_MIN = 300
REDIRECT_STATUS_MAX = 400


class DiscordAdapter(ChatClient):
    """Adapter that implements ChatClient by delegating to the discord service API.

    It stores an optional AuthenticatedClient created from an access token. If no token
    is present, calls that require authentication will raise ValueError.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", token: str | None = None) -> None:
        """Initialize the adapter.

        base_url: Base URL of the discord service API.
        token: Optional access token to create an authenticated client immediately.
        """
        self.base_url = base_url
        self.Client = Client(base_url=base_url)
        self.auth_client: AuthenticatedClient | None = None
        if token:
            self.set_token(token)

    # Convenience: call the service /login endpoint which returns an authorization URL
    def login(self, scopes: str | None = None, *, follow: bool = False) -> str | HTTPStatus:
        """Call the service /login endpoint and return an authorization URL or HTTP status.

        If the service responds with a redirect (3xx) the `Location` header
        value is returned. If the service returns a JSON object containing a
        URL (e.g. `url`, `authorization_url`) that string will be returned.

        If `follow=True` and an authorization URL is discovered the adapter
        will attempt to open the user's default browser to that URL. The URL
        is still returned to the caller so they can take further action.

        If no URL can be located the method falls back to returning the raw
        HTTP status code to preserve backwards compatibility.
        """
        resp = login.sync_detailed(client=self.Client, scopes=scopes)

        # If the service returned a redirect, the Location header contains the URL
        if REDIRECT_STATUS_MIN <= resp.status_code < REDIRECT_STATUS_MAX:
            location = resp.headers.get("Location")
            if location:
                if follow:
                    with contextlib.suppress(Exception):
                        webbrowser.open(location)
                return location

        # Some implementations may return the authorization URL in the JSON body
        parsed = resp.parsed
        if isinstance(parsed, dict):
            for key in ("url", "authorization_url", "auth_url", "authorizationUrl", "location"):
                val = parsed.get(key)
                if isinstance(val, str) and val:
                    if follow:
                        with contextlib.suppress(Exception):
                            webbrowser.open(val)
                    return val

        # Fall back to status code for compatibility
        return resp.status_code

    def set_token(self, token: str) -> None:
        """Create an AuthenticatedClient using the provided token."""
        self.auth_client = AuthenticatedClient(base_url=self.base_url, token=token)

    def _require_auth(self) -> AuthenticatedClient:
        if self.auth_client is None:
            msg = "Adapter not authenticated. Call set_token(token) first."
            raise ValueError(msg)
        return self.auth_client

    def get_messages(self, channel_id: str, max_results: int = 10) -> Iterator[ChatMessage]:
        """Yield up to `max_results` messages from `channel_id`.

        This returns an iterator of ChatMessage instances.
        """
        client = self._require_auth()
        res = get_messages.sync_detailed(channel_id=channel_id, client=client, limit=max_results)
        content = res.parsed
        if isinstance(content, HTTPValidationError) or content is None:
            msg = "Validation error from service"
            raise ValueError(msg)

        # Server may return either a list or a dict with a 'messages' key
        messages_data = None
        if isinstance(content, list):
            messages_data = content
        elif isinstance(content, dict) and "messages" in content:
            messages_data = content["messages"]
        else:
            msg = "Unexpected response format from list messages"
            raise ValueError(msg)

        for message in messages_data:
            yield DiscordMessage(message)

    def get_message(self, channel_id: str, message_id: str) -> ChatMessage:
        """Fetch a single message by `message_id` in `channel_id` and return it."""
        client = self._require_auth()
        res = get_message.sync_detailed(channel_id=channel_id, message_id=message_id, client=client)
        content = res.parsed
        if isinstance(content, HTTPValidationError) or content is None:
            msg = "Validation error from service"
            raise ValueError(msg)

        if isinstance(content, dict) and "message" in content:
            return DiscordMessage(content["message"])

        # If service returned the raw message dict directly
        if isinstance(content, dict):
            return DiscordMessage(content)

        msg = "Unexpected response format for get_message"
        raise ValueError(msg)

    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message and return True if the service reports deletion."""
        client = self._require_auth()
        res = delete_message.sync_detailed(channel_id=channel_id, message_id=message_id, client=client)
        deleted = res.parsed
        if isinstance(deleted, HTTPValidationError) or deleted is None:
            msg = "Validation error from service"
            raise ValueError(msg)
        return isinstance(deleted, dict) and ("message" in deleted or "status" in deleted)

    def send_message(self, recipient_id: str, content: str) -> ChatMessage:
        """Send a message to the given recipient and return the created message."""
        client = self._require_auth()
        res = send_message.sync_detailed(recipient_id=recipient_id, client=client, content=content)
        parsed = res.parsed
        if isinstance(parsed, HTTPValidationError) or parsed is None:
            msg = "Validation error from service"
            raise ValueError(msg)

        # Service returns dict with 'message' or the message object directly
        if isinstance(parsed, dict) and "message" in parsed:
            return DiscordMessage(parsed["message"])  # type: ignore[arg-type]
        if isinstance(parsed, dict):
            return DiscordMessage(parsed)
        msg = "Unexpected send_message response"
        raise ValueError(msg)

    def get_current_user(self) -> dict[str, Any]:
        """Return the current authenticated user as a mapping.

        If parsing the response fails, an empty dict is returned.
        """
        client = self._require_auth()
        res = get_current_user.sync_detailed(client=client)
        content = res.parsed
        if content is None:
            # Some generated endpoints return None in `.parsed` even when the
            # response contains JSON body. Try to decode the raw content as JSON
            # and return that to the caller so they receive the expected user dict.
            raw = res.content
            try:
                if isinstance(raw, (bytes, bytearray)):
                    return json.loads(raw.decode("utf-8"))
                if isinstance(raw, str):
                    return json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to empty dict if parsing fails
                return {}
        return content

    def _extract_token_from_mapping(self, mapping: object) -> str | None:
        """Return the first token-like value found in a mapping, or None."""
        if not isinstance(mapping, dict):
            return None
        for key in ("token", "access_token", "accessToken", "auth_token"):
            val = mapping.get(key)
            if isinstance(val, str) and val:
                return val
        return None

    def _parse_response_json(self, res: object) -> dict | None:
        """Try to parse response content as JSON and return a dict or None.

        This avoids broad exception handling in the main method.
        """
        raw = res.content
        try:
            if isinstance(raw, (bytes, bytearray)):
                return json.loads(raw.decode("utf-8"))
            if isinstance(raw, str):
                return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            return None
        return None

    def auth_callback_and_set_token(self, code: str) -> str | None:
        """Call the auth callback endpoint, extract and set an access token.

        Returns the token string if one was found and set, otherwise None.
        """
        # Call the generated endpoint for auth callback
        res = auth_callback.sync_detailed(client=self.Client, code=code)
        content = res.parsed
        token: str | None = None

        # If parsed content is a dict, look for common token keys
        token = self._extract_token_from_mapping(content)

        # If parsed is None or didn't include a token, try raw JSON body
        if token is None:
            parsed_raw = self._parse_response_json(res)
            token = self._extract_token_from_mapping(parsed_raw)

        if token:
            self.set_token(token)
        return token

    def get_users(self, guild_id: str) -> list[dict[str, Any]]:
        """Return a list of users for the given guild id."""
        client = self._require_auth()
        res = get_users.sync_detailed(guild_id=guild_id, client=client)
        content = res.parsed
        if isinstance(content, HTTPValidationError) or content is None:
            msg = "Validation error from service"
            raise ValueError(msg)
        # Expect a list or dict with 'users'
        if isinstance(content, list):
            return content
        if isinstance(content, dict) and "users" in content:
            return content["users"]
        return []

    def get_channel(self, channel_id: str) -> ChatChannel:
        """Return channel information for `channel_id` as a ChatChannel.

        If the service response cannot be parsed, an empty channel mapping is
        returned wrapped in a DiscordChannel.
        """
        client = self._require_auth()
        res = get_channel.sync_detailed(channel_id=channel_id, client=client)
        content = res.parsed
        if isinstance(content, HTTPValidationError) or content is None:
            msg = "Validation error from service"
            raise ValueError(msg)
        if isinstance(content, dict) and "channel_info" in content:
            return DiscordChannel(content["channel_info"])  # type: ignore[arg-type]
        if isinstance(content, dict):
            return DiscordChannel(content)
        return DiscordChannel({})
