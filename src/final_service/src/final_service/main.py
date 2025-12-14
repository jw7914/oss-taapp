"""Discord and AI implementation."""

# UPDATE DEPENDENCIES
import asyncio
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from discord_client_impl.discord_impl import DiscordClient, DiscordGateway
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response
from openai_client_impl.ai_client import AIClientImpl
from openai_client_impl import set_openai_key
from openai_client_impl import init_db
from prometheus_fastapi_instrumentator import Instrumentator

import discord_client_impl  # noqa: F401


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

            for mention in data["mentions"]:
                if app.state.client.client_id in mention["id"]:
                    process_message(data)

        gateway.subscribe("MESSAGE_CREATE", on_message_create)
        await gateway.start()
    except asyncio.CancelledError:
        print("Gateway listener cancelled")
    except Exception as e:
        print(f"Gateway error: {e}")


def process_message(data: dict[str, Any]) -> None:
    """If the discord bot is pinged the message will be processed."""

    KEY = os.getenv("OPENAPI_KEY")
    set_openai_key("user", KEY)
    ai_client = AIClientImpl("user")
    response = ai_client.generate_response(data["content"])
    result = response.content

    app.state.client.send_message(recipient_id=data["author"]["id"], content=result)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: startup and shutdown."""
    print("Starting Discord service...")
    # Ensure database directory and tables exist before background tasks run
    init_db()
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
    title="Discord AI Chat Service API",
    description="FastAPI service that exposes a Discord login implementation for AI integration",
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
    return {"message": "Welcome to Discord-AI Client Service!"}


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


@app.get("/health", tags=["General"], summary="Health check")
def health() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
