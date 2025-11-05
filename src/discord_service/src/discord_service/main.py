"""FastAPI Discord client service.

Endpoints provided:
- "/" : Welcome message
- "/login" : Start OAuth2 flow (returns authorization URL)
- "/auth/callback" : OAuth2 callback to exchange code for token and create client
- "/logout" : Clear stored client
- "/user" : Get current authenticated user info
- "/channels" : List channels (DMs/group DMs)
- "/channels/{channel_id}/messages" : List messages in a channel
- POST "/channels/{channel_id}/messages" : Send a message to channel
- GET "/messages/{message_id}" : Fetch a message by id (requires channel_id query)
- DELETE "/channels/{channel_id}/messages/{message_id}" : Delete a message (if supported)

This mirrors patterns used in `mail_client_service` and uses `discord_client_impl.DiscordClient`.

Environment variables expected (or set in DiscordClient constructor):
- DISCORD_CLIENT_ID
- DISCORD_CLIENT_SECRET
- DISCORD_REDIRECT_URI

Run with: uvicorn discord_service.main:app --reload
"""

from typing import Callable, Awaitable, Any

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response, RedirectResponse

import discord_client_impl  # noqa: F401
from discord_client_impl.discord_impl import DiscordClient
from discord_client_impl.message_impl import DiscordMessage, DiscordChannel

app = FastAPI(
    title="Discord Client Service API",
    description="FastAPI service that exposes a Discord client implementation",
    version="1.0.0",
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Middleware enforcing authentication for protected routes.

    Public routes: root, /login, /auth/callback, /logout, and docs/OpenAPI.
    Protected routes require `app.state.client` to be set.
    """
    public_paths = {"/", "/login", "/auth/callback", "/logout", "/openapi.json", "/docs", "/redoc"}

    if request.url.path in public_paths or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
        return await call_next(request)

    # For channel / message related endpoints, ensure client exists
    if (
        request.url.path.startswith("/channels")
        or request.url.path.startswith("/messages")
        or request.url.path.startswith("/user")
    ):
        # If we don't have an in-memory client, try to rehydrate from a cookie
        if not hasattr(app.state, "client") or app.state.client is None:
            token = request.cookies.get("discord_access_token")
            if token:
                try:
                    # Recreate a lightweight client for this request using the access token
                    app.state.client = DiscordClient(access_token=token)
                except Exception:
                    # If rehydration fails, clear any partially-set client and return 401
                    app.state.client = None
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "error": "Not authenticated",
                            "message": "User is not authenticated. Please log in first via /login and complete /auth/callback.",
                            "status": "error",
                        },
                    )
            else:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Not authenticated",
                        "message": "User is not authenticated. Please log in first via /login and complete /auth/callback.",
                        "status": "error",
                    },
                )

    return await call_next(request)


@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    return {"message": "Welcome to Discord Client Service!"}


@app.get("/login", tags=["Authentication"], summary="Get OAuth2 Authorization URL")
def login(scopes: str | None = Query(None, description="Optional space-separated scopes override")) -> Response:
    """Return the authorization URL the user should visit to authorize the application.

    The DiscordClient reads client_id/secret from environment by default. We instantiate
    a temporary client to build the authorization URL.
    """
    # Prevent duplicate login attempts
    if getattr(app.state, "auth_in_progress", False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Authentication in progress",
                "message": "Authentication is already in progress.",
                "status": "error",
            },
        )

    try:
        app.state.auth_in_progress = True
        temp_client = DiscordClient()
        if scopes:
            # client.get_authorization_url expects list of scopes; discord expects space separated, but method handles joining
            scope_list = scopes.split()
            url = temp_client.get_authorization_url(scopes=scope_list)
        else:
            url = temp_client.get_authorization_url()
        # Redirect the user's browser to the authorization URL
        return Response(status_code=status.HTTP_302_FOUND, headers={"Location": url})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to build authorization URL", "message": str(e), "status": "error"},
        )
    finally:
        app.state.auth_in_progress = False


@app.get("/auth/callback", tags=["Authentication"], summary="OAuth2 callback to exchange code for token")
def auth_callback(code: str | None = Query(None, description="Authorization code from provider")) -> RedirectResponse:
    """Exchange the authorization code for an access token and store an authenticated client in app state."""
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Missing code", "message": "Missing 'code' query parameter.", "status": "error"},
        )

    if hasattr(app.state, "client") and app.state.client is not None:
        return RedirectResponse(url="/user", status_code=status.HTTP_302_FOUND)

    try:
        app.state.auth_in_progress = True
        client = DiscordClient()
        token = client.fetch_access_token(code)
        # client now has token set via _set_token inside fetch_access_token
        app.state.client = client
        # Set a secure-ish HttpOnly cookie so subsequent browser requests carry the
        # access token and the middleware can rehydrate the client. In production
        # you should use a server-side session store and avoid storing raw tokens
        # in cookies.
        resp = RedirectResponse(url="/user", status_code=status.HTTP_302_FOUND)
        resp.set_cookie("discord_access_token", token, httponly=True, samesite="lax")
        return resp
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Authentication failed", "message": str(e), "status": "error"},
        )
    finally:
        app.state.auth_in_progress = False


@app.get("/logout", tags=["Authentication"], summary="Logout and clear client")
def logout() -> JSONResponse:
    if hasattr(app.state, "client") and app.state.client is not None:
        app.state.client = None
        resp = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Logged out successfully", "status": "success"})
        resp.delete_cookie("discord_access_token")
        return resp
    resp = JSONResponse(status_code=status.HTTP_200_OK, content={"message": "No active session to logout", "status": "success"})
    resp.delete_cookie("discord_access_token")
    return resp


def serialize_message(msg: DiscordMessage) -> dict[str,str]:
    # ChatMessage implementations provide properties defined by chat_client_api.message
    return {
        "id": getattr(msg, "message_id", getattr(msg, "id", "")),
        "channel_id": getattr(msg, "channel_id", ""),
        "author": getattr(msg, "author", ""),
        "author_username": getattr(msg, "author_username", ""),
        "content": getattr(msg, "content", ""),
        "timestamp": getattr(msg, "timestamp", ""),
    }

def serialize_channel(ch: DiscordChannel) -> dict[str,Any]:
    return {
        "id": getattr(ch, "channel_id", getattr(ch, "id", "")),
        "name": getattr(ch, "channel_name", getattr(ch, "name", "")),
        "type": getattr(ch, "channel_type", None),
        "position": getattr(ch, "channel_position", None),
    }

def serialize_users(user: dict[str,str]) -> dict[str,str]:
    return {
        "id": user.get("id", ""),
        "username": user.get("username", ""),
    }

@app.get("/user", tags=["User"], summary="Get current user info")
def get_current_user() -> JSONResponse:
    try:
        user = app.state.client.get_current_user()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"user": user, "status": "success"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get user", "message": str(e), "status": "error"},
        )


@app.get("/channels/{channel_id}/messages", tags=["Messages"], summary="List messages in a channel")
def list_channel_messages(channel_id: str, limit: int = Query(50, ge=1, le=100),) -> JSONResponse:
    try:    
        messages = list(app.state.client.get_messages(channel_id=channel_id ,limit=limit))
        serialized = [serialize_message(m) for m in messages]   
        return JSONResponse(status_code=status.HTTP_200_OK, content={"messages": serialized, "status": "success"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to list messages", "message": str(e), "status": "error"},
        )


@app.post("/message/{recipient_id}", tags=["Messages"], summary="Send a message to a channel")
def send_message(recipient_id: str, content: str = Query(..., description="Message content")) -> JSONResponse:
    try:
        new_msg = app.state.client.send_message(recipient_id=recipient_id, content=content)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED, content={"message": serialize_message(new_msg), "status": "success"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to send message", "message": str(e), "status": "error"},
        )


@app.get(
    "/channels/{channel_id}/messages/{message_id}",
    tags=["Messages"],
    summary="Get message by id",
    description="Requires `channel_id` query parameter to scope the search",
)
def get_message(
    message_id: str, channel_id: str 
) -> JSONResponse:
    if channel_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Missing channel_id",
                "message": "channel_id query parameter is required to locate a message in Discord.",
                "status": "error",
            },
        )

    try:
        # Discord doesn't provide a single GET-by-id in this implementation, so list recent messages and find match
        for m in app.state.client.get_messages(channel_id=channel_id, limit=100):
            if getattr(m, "message_id", getattr(m, "id", None)) == message_id:
                return JSONResponse(
                    status_code=status.HTTP_200_OK, content={"message": serialize_message(m), "status": "success"}
                )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Message not found",
                "message": f"Message {message_id} not found in channel {channel_id}",
                "status": "error",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to fetch message", "message": str(e), "status": "error"},
        )


@app.delete("/channels/{channel_id}/messages/{message_id}", tags=["Messages"], summary="Delete a message")
def delete_message(channel_id: str, message_id: str) -> JSONResponse:
    """Attempt to delete a message using the client's HTTP interface. May fail depending on permissions and token type."""
    try:
        # Use underlying http client directly (DiscordClient keeps an httpx.Client as _http_client)
        http_client = getattr(app.state.client, "_http_client", None)
        if http_client is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={
                    "error": "Not supported",
                    "message": "Delete not supported by this client implementation.",
                    "status": "error",
                },
            )

        resp = http_client.delete(f"/channels/{channel_id}/messages/{message_id}")
        # 204 No Content indicates success
        if resp.status_code in (200, 204):
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"message": f"Message {message_id} deleted.", "status": "success"}
            )
        if resp.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Forbidden", "message": "Insufficient permissions to delete the message.", "status": "error"},
            )
        if resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found", "message": "Message or channel not found.", "status": "error"},
            )
        # Other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to delete", "message": f"HTTP {resp.status_code}: {resp.text}", "status": "error"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to delete message", "message": str(e), "status": "error"},
        )

@app.get("/serverusers/{guild_id}", tags=["User"], summary="Retrieves channel info")
def get_users(guild_id: str) -> JSONResponse:
    try:    
        users = app.state.client.get_users(guild_id = guild_id)
        user_list = [serialize_users(u['user']) for u in users]
        return JSONResponse(status_code=status.HTTP_200_OK, content={"users": user_list , "status": "success"})
    except Exception as e:
        raise HTTPException( 
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get channel", "message": str(e), "status": "error"})

@app.get("/channels/{channel_id}", tags=["Channel"], summary="Retrieves channel info")
def get_channel(channel_id: str) -> JSONResponse:
    try:    
        channel = app.state.client.get_channel(channel_id=channel_id)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"channel_info": serialize_channel(channel) , "status": "success"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get channel", "message": str(e), "status": "error"})