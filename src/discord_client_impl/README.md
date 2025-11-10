````markdown
# Discord Client Implementation

## Overview

`discord_client_impl` provides a concrete implementation of the chat client API
backed by the Discord REST API. It implements the `ChatClient` abstraction and
returns `DiscordMessage` and `DiscordChannel` objects from the `message_impl`.

This package is intended for locally-run services or bots that need to read
and send messages via Discord (for example, the `discord_service` component).

## Purpose

- Provide a production-ready adapter between the project's `chat_client_api`
  abstractions and Discord's API.
- Handle OAuth2 and bot-token based authentication.
- Convert raw Discord JSON responses into typed `DiscordMessage` and
  `DiscordChannel` objects that satisfy the `ChatMessage` / `ChatChannel` API.

## Files

- `discord_impl.py` — `DiscordClient` implementation of `chat_client_api.client.ChatClient`.

  - Handles OAuth flows (authorization URL, token exchange) via `authlib`.
  - Exposes methods: `get_authorization_url`, `fetch_access_token`, `get_current_user`,
    `get_messages`, `send_message`, `get_message`, `delete_message`, `get_users`, `get_channel`.
  - Uses `httpx.Client` for HTTP requests.

- `message_impl.py` — `DiscordMessage` and `DiscordChannel` implementations of the
  `ChatMessage` and `ChatChannel` abstract classes. These provide convenient
  typed accessors for common fields (id, content, author, timestamps, name, type).

## Environment / Configuration

`DiscordClient` reads configuration from constructor parameters or environment
variables (priority: explicit constructor args → environment):

- `DISCORD_CLIENT_ID` — OAuth2 client ID
- `DISCORD_CLIENT_SECRET` — OAuth2 client secret
- `DISCORD_REDIRECT_URI` — OAuth2 redirect uri (defaults to `http://127.0.0.1:8000/auth/callback`)
- `DISCORD_BOT_TOKEN` — Bot token used for authenticated API calls

If a `.env` file exists and `python-dotenv` is installed, this library will
attempt to load it automatically.

## Usage Examples

### Basic instantiation (bot-token based)

```python
from discord_client_impl.discord_impl import DiscordClient

# Create the client using environment variables or pass tokens directly
client = DiscordClient(bot_token="YOUR_BOT_TOKEN")

# Fetch a channel and iterate recent messages
channel = client.get_channel("123456789012345678")
for msg in client.get_messages(channel_id=channel.id, limit=10):
    print(msg.timestamp, msg.author_name, msg.content)

# Send a message to a user (creates or finds DM channel)
new_msg = client.send_message(recipient_id="987654321098765432", content="Hello from the bot!")
print("Sent message id:", new_msg.id)
```
````

### OAuth2 interactive flow (web app)

```python
from discord_client_impl.discord_impl import DiscordClient

client = DiscordClient(client_id="...", client_secret="...", redirect_uri="https://your.app/callback")
auth_url = client.get_authorization_url()
print("Open this URL to authorize:", auth_url)

# After the user authorizes and you receive a `code` at your redirect URI:
# token = client.fetch_access_token(authorization_code)
# client is now authorized to make user-scoped requests
```

## API Highlights

- get_authorization_url(scopes: list[str] | None = None, \*\*kwargs) -> str

  - Returns a Discord OAuth2 authorization URL. Scopes are space-separated.

- fetch_access_token(authorization_code: str) -> str

  - Exchanges an authorization code for an access token and sets that token
    on the client.

- get_messages(channel_id: str, limit: int = 50) -> Iterator[ChatMessage]

  - Yields `DiscordMessage` instances wrapping raw API JSON.

- send_message(recipient_id: str, content: str) -> ChatMessage
  - Sends a direct-message (will create DM channel if needed) and returns
    the created `DiscordMessage`.

See the source code for additional methods and detailed behavior (e.g.,
pagination, error handling, HTTP status checks).

## Types and compatibility

`DiscordMessage` and `DiscordChannel` implement the project-level `ChatMessage`
and `ChatChannel` abstractions (see `chat_client_api`) and provide compatibility
properties such as `message_id`, `channel_name`, and `author_username` so they
work with existing code that expects the abstract API.

## Testing

Unit tests live under `src/discord_client_impl/tests/` and use mocks for HTTP
responses—no real Discord calls are made by unit tests. Run them with pytest:

```bash
uv run pytest src/discord_client_impl/tests/ -q
```

## Notes and caveats

- Discord API limits: the client enforces a per-request message `limit` but does
  not implement rate-limit backoff. Consumers should handle `httpx.HTTPError`
  and rate-limit (429) responses if performing high-volume operations.
- Some methods (like `get_message`) implement best-effort scanning because the
  REST API requires a channel id to fetch messages directly.

## Where to look next

- `src/discord_client_impl/src/discord_client_impl/discord_impl.py` — implementation
- `src/discord_client_impl/src/discord_client_impl/message_impl.py` — message/channel types

```

```
