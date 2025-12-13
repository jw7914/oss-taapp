"""FastAPI Discord client service."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Awaitable

import asyncio
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response, RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator

import discord_client_impl  # noqa: F401
from discord_client_impl.discord_impl import DiscordClient, DiscordGateway
from discord_client_impl.message_impl import DiscordMessage, DiscordChannel

from prometheus_fastapi_instrumentator import Instrumentator
import os


async def listen_for_messages() -> None:
    """Listen for new messages in real-time via Discord Gateway.
    Only starts if app.state.client is available (user is logged in).
    """
    try:
        # Wait for client to be available (user logs in)
        while not hasattr(app.state, "client") or app.state.client is None:
            await asyncio.sleep(1)

        gateway = DiscordGateway(token=app.state.client.bot_token)

        def on_message_create(data: dict[str, Any]) -> None:
            print(f"Message from {data['author']['username']}: {data['content']}")

            for mention in data['mentions']:
                if app.state.client.client_id in mention['id']:
                    process_message(data)
            
        gateway.subscribe("MESSAGE_CREATE", on_message_create)
        await gateway.start()
    except asyncio.CancelledError:
        print("Gateway listener cancelled")
    except Exception as e:
        print(f"Gateway error: {e}")

def process_message(data: dict[str, Any]) -> None:
     """If the discord bot is pinged the message will be processed
    """
     app.state.client.send_message(recipient_id=data["author"]["id"], content=data["content"])



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: startup and shutdown."""
    print("Starting Discord service...")
    task = asyncio.create_task(listen_for_messages())
    app.state.gateway_task = task
    
    yield  # Application runs here
    
    print("Shutting down Discord service...")
    if hasattr(app.state, "gateway_task"):
        app.state.gateway_task.cancel()
        try:
            await app.state.gateway_task
        except asyncio.CancelledError:
            pass


# Create app with lifespan (only once)
app = FastAPI(
    title="Discord Client Service API",
    description="FastAPI service that exposes a Discord client implementation",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    # ...existing middleware code...
    public_paths = {"/", "/login", "/auth/callback", "/logout", "/openapi.json", "/docs", "/redoc", "/health", "/metrics"}

    if request.url.path in public_paths or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
        return await call_next(request)

    if (
        request.url.path.startswith("/channels")
        or request.url.path.startswith("/messages")
        or request.url.path.startswith("/user")
    ):
        if not hasattr(app.state, "client") or app.state.client is None:
            token = request.cookies.get("discord_access_token")
            if token:
                try:
                    app.state.client = DiscordClient(access_token=token)
                except Exception:
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


# Expose Prometheus metrics and show the endpoint in the OpenAPI docs under the General tag.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=True, tags=["General"])

@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    return {"message": "Welcome to Discord Client Service!"}


@app.get("/health", tags=["General"], summary="Health check")
def health() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})


@app.get("/login", tags=["Authentication"], summary="Get OAuth2 Authorization URL")
def login(scopes: str | None = Query(None, description="Optional space-separated scopes override")) -> Response:
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

        temp_client = DiscordClient(
            client_id=os.environ.get("DISCORD_CLIENT_ID"),
            client_secret=os.environ.get("DISCORD_CLIENT_SECRET"),
        )
        if scopes:
            scope_list = scopes.split()
            url = temp_client.get_authorization_url(scopes=scope_list)
        else:
            url = temp_client.get_authorization_url()
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
        app.state.client = client
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


def serialize_message(msg: DiscordMessage) -> dict[str, str]:
    return {
        "id": getattr(msg, "message_id", getattr(msg, "id", "")),
        "channel_id": getattr(msg, "channel_id", ""),
        "author": getattr(msg, "author", ""),
        "author_username": getattr(msg, "author_username", ""),
        "content": getattr(msg, "content", ""),
        "timestamp": getattr(msg, "timestamp", ""),
    }


def serialize_channel(ch: DiscordChannel) -> dict[str, Any]:
    return {
        "id": getattr(ch, "channel_id", getattr(ch, "id", "")),
        "name": getattr(ch, "channel_name", getattr(ch, "name", "")),
        "type": getattr(ch, "channel_type", None),
        "position": getattr(ch, "channel_position", None),
    }


def serialize_users(user: dict[str, str]) -> dict[str, str]:
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
def list_channel_messages(
    channel_id: str,
    limit: int = Query(50, ge=1, le=100),
) -> JSONResponse:
    try:
        messages = list(app.state.client.get_messages(channel_id=channel_id, limit=limit))
        serialized = [serialize_message(m) for m in messages]
        return JSONResponse(status_code=status.HTTP_200_OK, content={"messages": serialized, "status": "success"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to list messages", "message": str(e), "status": "error"},
        )


@app.post("/message/{recipient_id}", tags=["Messages"], summary="Send a message to a user")
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
)
def get_message(message_id: str, channel_id: str) -> JSONResponse:
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
    try:
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
        users = app.state.client.get_users(guild_id=guild_id)
        user_list = [serialize_users(u["user"]) for u in users]
        return JSONResponse(status_code=status.HTTP_200_OK, content={"users": user_list, "status": "success"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get channel", "message": str(e), "status": "error"},
        )


@app.get("/channels/{channel_id}", tags=["Channel"], summary="Retrieves channel info")
def get_channel(channel_id: str) -> JSONResponse:
    try:
        channel = app.state.client.get_channel(channel_id=channel_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"channel_info": serialize_channel(channel), "status": "success"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get channel", "message": str(e), "status": "error"},
        )


@app.get("/channels", tags=["Channel"], summary="Retrieves all channels")
def get_channels() -> JSONResponse:
    try:
        channels = app.state.client.get_channels()
        serialized = [serialize_channel(ch) for ch in channels]
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"channels": serialized, "status": "success"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get channels", "message": str(e), "status": "error"},
        )