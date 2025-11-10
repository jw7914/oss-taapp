# Discord Client Service

FastAPI-based Discord client service. This README explains how to run the service locally in development.

Quick start (development)

1. From the repository root, activate your virtualenv if you have one:

# Discord Client Service

A small FastAPI service that exposes the concrete `DiscordClient` implementation over HTTP. This mirrors the `mail_client_service` pattern in the repo and provides basic OAuth2 flow plus a few chat endpoints for listing channels, reading messages, sending messages, and (where permitted) deleting messages.

Contents

- `src/discord_service/src/discord_service/main.py` — FastAPI application and endpoints
- `pyproject.toml` — package metadata for editable installs

Highlights

- OAuth2 endpoints: start authorization and handle callback
- Channel and message endpoints: list channels, list messages, send message, fetch message by id (scoped to channel), delete message
- Uses `discord_client_impl.DiscordClient` and `chat_client_api` contracts

Quick start (development)

1. Install Dependencies:

```bash
uv sync --all-packages --extra dev
```

2. Activate the virtual envoirnment:

```bash
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. Run the Service

```bash
# Run the service
uvicorn discord_service.main:app --reload --host 127.0.0.1 --port 8000
```

Environment variables

Set these for the OAuth flow (or add to a `.env` file):

- `DISCORD_CLIENT_ID` — Discord application client id
- `DISCORD_CLIENT_SECRET` — Discord application client secret
- `DISCORD_REDIRECT_URI` — Optional Discord redirect URI (used for prod)

API endpoints (summary)

- GET `/` — Welcome message
- GET `/health` — Health check (returns {"status": "ok"})
- GET `/login` — Return OAuth2 authorization URL (redirect users to Discord to authorize)
- GET `/auth/callback?code=...` — OAuth2 callback: exchange code for an access token, store a lightweight authenticated client in memory and set an HttpOnly cookie, then redirect to `/user`
- GET `/logout` — Clear the in-memory client and delete the `discord_access_token` cookie
- GET `/user` — Get the current authenticated user's data
- GET `/channels/{channel_id}` — Retrieve channel information
- GET `/channels/{channel_id}/messages?limit=50` — List recent messages in a channel (limit 1-100)
- POST `/message/{recipient_id}?content=...` — Send a message to a recipient/channel (note: path is `/message/{recipient_id}` in the service)
- GET `/channels/{channel_id}/messages/{message_id}` — Get a single message by id (this implementation scans recent messages in the channel)
- DELETE `/channels/{channel_id}/messages/{message_id}` — Delete a message (may require proper scopes/permissions)
- GET `/serverusers/{guild_id}` — List users in a guild (server)

Notes about behavior and limitations

- The service stores the authenticated client on the FastAPI `app.state` for the running process. This is fine for local testing but not production-ready for multi-worker deployments.
- Discord's API and token types govern what you can do: deleting messages or reading certain channels may require the correct OAuth scopes or bot permissions.
- `GET /messages/{id}` requires `channel_id` because this implementation does not provide a single-message GET; it scans recent messages in the specified channel.

Notes about routing differences and behavior

- The send-message endpoint in the running service is exposed as `POST /message/{recipient_id}` (not `/channels/{channel_id}/messages`) — the README previously referenced a different path. The service accepts `content` as a query parameter.
- The service stores an authenticated client on `app.state` and sets an HttpOnly cookie named `discord_access_token` for browser flows. This is suitable for local testing but not for production/multi-worker deployments.
- Some operations (deleting messages, reading specific channels) depend on OAuth scopes and token type; permissions may limit what the service can do.

Example flows

- Get authorization URL:

```bash
curl "http://127.0.0.1:8000/login"
```

- After authorizing, Discord will redirect to your `DISCORD_REDIRECT_URI` (which should map to `/auth/callback` in this service). The callback exchanges the code and the service returns the access token in the response body and sets a secure-ish cookie for subsequent requests.

- List channels (after auth):

```bash
curl http://127.0.0.1:8000/channels
```
