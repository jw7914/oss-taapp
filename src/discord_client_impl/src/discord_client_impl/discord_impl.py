"""Discord Client Implementation.

This module provides a concrete implementation of the chat client API using the Discord API.
It handles OAuth2 authentication and provides methods to interact with Discord.

"""

import asyncio
import json
import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

from collections.abc import Iterator, Callable
from typing import Any, Optional

import aiohttp
import httpx
import websockets
from authlib.integrations.httpx_client import OAuth2Client  # type: ignore[import-untyped]
from chat_client_api.client import ChatClient
from chat_client_api.message import ChatChannel, ChatMessage

import chat_client_api
from discord_client_impl.message_impl import DiscordChannel, DiscordMessage

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # If python-dotenv is not available, check if .env file exists
    # and manually load it
    env_path = Path(".env")
    if env_path.exists():
        with env_path.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


class DiscordGateway:
    DISCORD_GATEWAY_URL = "https://discord.com/api/v10/gateway/bot"

    def __init__(self, token: str | None = None) -> None:
        self.token: str = token or os.environ.get("DISCORD_BOT_TOKEN")
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.sequence: Optional[int] = None
        self.session_id: Optional[str] = None
        self.subscribers: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}
        self.heartbeat_interval: Optional[int] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self.running: bool = False

    def subscribe(self, event_name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        if event_name in self.subscribers:
            self.subscribers[event_name].remove(callback)

    async def _emit(self, event_name: str, data: dict[str, Any]) -> None:
        """Call subscriber callbacks."""
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        # run sync callbacks without blocking
                        await asyncio.get_running_loop().run_in_executor(None, callback, data)
                except Exception as e:
                    print(f"Error in {event_name} callback: {e}")

    async def _heartbeat(self) -> None:
        try:
            while self.running:
                await asyncio.sleep(self.heartbeat_interval / 1000)
                if self.ws and not self.ws.closed:
                    heartbeat = {"op": 1, "d": self.sequence}
                    await self.ws.send(json.dumps(heartbeat))
        except asyncio.CancelledError:
            return


    async def _identify(self) -> None:
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "intents": 513,  # GUILDS + GUILD_MESSAGES
                "properties": {"os": "linux", "browser": "custom_bot", "device": "custom_bot"},
            },
        }
        await self.ws.send(json.dumps(payload))


    async def _handle_message(self, message: str) -> None:
        data: dict[str, Any] = json.loads(message)
        op: int = data["op"]

        if data.get("s"):
            self.sequence = data["s"]

        if op == 10:  # Hello response
            self.heartbeat_interval = data["d"]["heartbeat_interval"]
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
            await self._identify()

        elif op == 11:  # Heartbeat
            pass

        elif op == 0:  # Dispatch
            event_name = data["t"]
            event_data = data["d"]

            if event_name == "READY":
                self.session_id = event_data["session_id"]
                print(f"Connected as {event_data['user']['username']}#{event_data['user']['discriminator']}")

            await self._emit(event_name, event_data)

        elif op == 9:  # Invalid session
            print("Invalid session, re-identifying in 5s...")
            await asyncio.sleep(5)
            await self._identify()

    async def _connect_and_listen(self) -> None:
        # Query the gateway URL
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.DISCORD_GATEWAY_URL,
                headers={"Authorization": f"Bot {self.token}"},
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to get gateway: {resp.status}")
                gateway_data = await resp.json()
                url = gateway_data["url"]

        # Connect to WebSocket
        async with websockets.connect(f"{url}?v=10&encoding=json", max_size=None) as ws:
            self.ws = ws
            print(f"Connected to Discord Gateway: {url}")

            async for message in ws:
                await self._handle_message(message)

   
    async def start(self) -> None:
        """Start the gateway."""
        self.running = True

        while self.running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                print(f"Connection error: {e}")

            if not self.running:
                break
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

    async def stop(self) -> None:
        """Clean async shutdown."""
        self.running = False

        if self.ws:
            await self.ws.close()

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

class DiscordClient(ChatClient):
    """Concrete implementation of the Client abstraction using Discord API."""

    DISCORD_API_BASE: ClassVar[str] = "https://discord.com/api/v10"
    # Use the documented API endpoints which return JSON responses.
    OAUTH2_AUTHORIZE_URL: ClassVar[str] = "https://discord.com/api/oauth2/authorize"
    OAUTH2_TOKEN_URL: ClassVar[str] = "https://discord.com/api/oauth2/token"  # noqa: S105
    DEFAULT_SCOPES: ClassVar[list[str]] = [
        "identify",  # For /users/@me
        "bot",
        "messages.read",  # For GET /channels/{id}/messages
        # "dm_channels.read",  # For GET /users/@me/channels
    ]
    # Common HTTP status codes used by the implementation
    NOT_FOUND_STATUS: ClassVar[int] = 404

    def __init__(
        self,
        access_token: str | None = None,
        bot_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
    ) -> None:
        """Initialize Discord client with OAuth2 credentials.

        Args:
            access_token: Discord OAuth2 access token (if already authenticated).
            client_id: Discord application client ID (for OAuth flow).
            bot_token: Discord bot token (for user interaction)
            client_secret: Discord application client secret (for OAuth flow).
            redirect_uri: OAuth2 redirect URI (for OAuth flow).

        """
        self.client_id = client_id or os.environ.get("DISCORD_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("DISCORD_CLIENT_SECRET")
        self.bot_token = bot_token or os.environ.get("DISCORD_BOT_TOKEN")
        self.redirect_uri = redirect_uri or os.environ.get(
            "DISCORD_REDIRECT_URI",
            "http://127.0.0.1:8000/auth/callback",
        )
        self.access_token = access_token

        # This client is for making API calls (requires Bearer token)
        self._http_client: httpx.Client = httpx.Client(
            base_url=self.DISCORD_API_BASE,
            timeout=30.0,
        )

        # This client is for performing the OAuth flow (uses client_id/secret)
        # Keep as Any to avoid static issues if OAuth2Client is unresolved.
        self._oauth_client: Any = OAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )
        if self.access_token:
            self._set_token(self.access_token)

    def _set_token(self, token: str) -> None:
        """Set the access token for the API client."""
        self.access_token = token
        self._http_client.headers.update(
            {
                "Authorization": f"Bot {self.bot_token}",
            },
        )

    def get_authorization_url(
        self,
        scopes: list[str] | None = None,
        **kwargs: object,
    ) -> str:
        """Get the OAuth2 authorization URL to redirect the user to.

        Args:
            scopes: A list of OAuth scopes to r equest. Defaults to DEFAULT_SCOPES.
            **kwargs: Additional parameters to pass to create_authorization_url.

        Returns:
            The full authorization URL.

        """
        if scopes is None:
            scopes = self.DEFAULT_SCOPES

        # Discord requires scopes as a space-separated string
        auth_url, _ = self._oauth_client.create_authorization_url(
            self.OAUTH2_AUTHORIZE_URL,
            scope=" ".join(scopes),
            **kwargs,
        )
        return str(auth_url)

    def fetch_access_token(self, authorization_code: str) -> str:
        """Exchange an authorization code for an access token.

        This method also sets the token on the client for future requests.

        Args:
            authorization_code: The 'code' query parameter from the OAuth callback.

        Returns:
            The new access token.

        """
        token_data = self._oauth_client.fetch_token(
            self.OAUTH2_TOKEN_URL,
            grant_type="authorization_code",
            code=authorization_code,
            redirect_uri=self.redirect_uri,
        )

        access_token = str(token_data["access_token"])
        self._set_token(access_token)
        return access_token

    def get_current_user(self) -> dict[str, Any]:
        """Get information about the currently authenticated user.

        Requires the 'identify' scope.

        Returns:
            A dictionary of the user's data from the Discord API.

        Raises:
            TypeError: If the API response is not in the expected dict format.

        """
        response = self._http_client.get(
            "/users/@me",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        response.raise_for_status()  # Raise HTTPError for bad responses

        json_data = response.json()

        if not isinstance(json_data, dict):
            err_str = f"API response for /users/@me was not a dict, got {type(json_data)}"
            raise TypeError(
                err_str,
            )

        # Mypy will be satisfied that json_data is a dict.
        # Since the abstract method returns dict[str, Any], this is compliant.
        return json_data

    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> Iterator[ChatMessage]:
        """Get recent messages from a specific channel.

        Requires the 'messages.read' scope.

        Args:
            channel_id: The ID of the channel to fetch messages from.
            token: Access token of the user.
            limit: The number of messages to retrieve (max 100).
            token: The OAuth2 access token to use for authorization.

        Yields:
            DiscordMessage: A message object.

        """
        params = {"limit": min(limit, 100)}  # Enforce Discord's max limit
        response = self._http_client.get(
            f"/channels/{channel_id}/messages",
            params=params,
        )
        response.raise_for_status()

        message_data_list = response.json()
        logger.debug(f"get_messages raw response ({len(message_data_list)} messages): {message_data_list}")
        
        if not isinstance(message_data_list, list):
            logger.warning(
                "Expected a list from /channels/.../messages, got %s",
                type(message_data_list),
            )
            return  # Stop iteration

        # Messages are returned newest-first by default
        for message_data in message_data_list:
            yield DiscordMessage(message_data)

    def send_message(self, recipient_id: str, content: str) -> ChatMessage:
        """Send a message to a specific channel.

        Requires the 'send_messages' scope.

        Args:
            recipient_id: The ID of the user to send the message to.
            content: The text content of the message.

        Returns:
            DiscordMessage: The newly created message object returned by the API.

        """
        channel_response = self._http_client.post(
            "/users/@me/channels",
            json={"recipient_id": recipient_id},
        )
        channel_response.raise_for_status()
        channel_id = channel_response.json()["id"]
        payload = {"content": content}
        response = self._http_client.post(
            f"/channels/{channel_id}/messages",
            json=payload,
        )
        response.raise_for_status()

        # The API returns the newly created message object
        new_message_data = response.json()
        return DiscordMessage(new_message_data)

    # Implement abstract ChatClient methods to satisfy the contract
    def get_message(self, channel_id: str, message_id: str) -> ChatMessage:
        """Locate a message by id by scanning the user's channels.

        This is a best-effort implementation because Discord's REST API
        requires a channel id to fetch messages. We scan recent messages
        in each channel until a match is found.
        """
        try:
            for msg in self.get_messages(channel_id=channel_id, limit=100):
                if msg.message_id == message_id:
                    logger.debug(f"Found message! Content: {repr(msg.content)}")
                    return msg
        except httpx.HTTPError as exc:
            # Log per-channel failures so we can diagnose network/API issues
            logger.debug(
                "Failed to scan channel %s for message %s: %s",
                channel_id,
                message_id,
                exc,
            )

        msg_text = f"Message with id {message_id} not found"
        raise RuntimeError(msg_text)

    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Attempt to delete a message by searching channels and calling DELETE.

        Returns True on success, False otherwise.
        """
        try:
            url = f"/channels/{channel_id}/messages/{message_id}"
            resp = self._http_client.delete(url)
            # If 404, continue searching other channels
            # For other status codes, treat as failure for this channel and continue
        except httpx.HTTPError as exc:
            logger.debug(
                "Failed to delete message %s in channel %s: %s",
                message_id,
                channel_id,
                exc,
            )
            return False
        else:
            return resp.status_code in (200, 204)

    def get_users(self, guild_id: str) -> list[str]:
        """Get users from a server.

        Returns a list of users"
        """
        try:
            response = self._http_client.get(f"/guilds/{guild_id}/members?limit=1000")
            response.raise_for_status()
            user_list = response.json()
            if not isinstance(user_list, list):
                logger.warning(
                    "Expected a list, got %s",
                    type(user_list),
                )
                return []
        except httpx.HTTPError as exc:
            logger.debug(
                "Failed to get users in %s: %s",
                guild_id,
                exc,
            )
            return []
        else:
            return user_list

    def get_channel(self, channel_id: str) -> ChatChannel:
        """Get channel info from channel_id.

        Returns a DiscordChannel object.
        """
        try:
            response = self._http_client.get(f"/channels/{channel_id}")
            response.raise_for_status()
            channel_data = response.json()
            return DiscordChannel(channel_data)
        except httpx.HTTPError as exc:
            logger.debug(
                "Failed to get channel %s: %s",
                channel_id,
                exc,
            )
            return DiscordChannel({})
    def get_channels(self) -> Iterator[ChatChannel]:
        """Get channels from all channels visible to client.

        Returns a Iterative DiscordChannel object.
        """
        try:
            response = self._http_client.get("/users/@me/channels")
            response.raise_for_status()
            channels = response.json()

            for channel_data in channels:
                yield DiscordChannel(channel_data)
        except httpx.HTTPError as exc:
            logger.debug(
                "Failed to get channels: %s",
                exc,
            )


def get_chat_client_impl(*, access_token: str) -> chat_client_api.ChatClient:
    """Return a configured :class:`DiscordClient` instance."""
    return DiscordClient(access_token = access_token)


def register() -> None:
    """Register the Gmail client implementation with the chat client API."""
    chat_client_api.get_client = get_chat_client_impl
