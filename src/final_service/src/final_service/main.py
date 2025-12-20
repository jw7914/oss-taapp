"""Discord, AI, and Tickets implementation."""

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
from tickets_client_impl.tickets_impl import TicketsClient
from tickets_api import TicketStatus
from prometheus_fastapi_instrumentator import Instrumentator
from gtask_client_impl.gtask_impl import GTaskClient

import discord_client_impl  # noqa: F401
import tickets_client_impl  # noqa: F401


async def listen_for_messages() -> None:
    """Listen for new messages in real-time via Discord Gateway.
    Only starts if app.state.client is available (user is logged in).

    """
    try:
        # Wait for client to be available (user logs in)
        while not hasattr(app.state, "client") or app.state.client is None:
            await asyncio.sleep(1)

        gateway = DiscordGateway(token=app.state.client.bot_token)
        loop = asyncio.get_running_loop()

        def on_message_create(data: dict[str, Any]) -> None:
            print(f"Message from {data['author']['username']}: {data['content']}")

            for mention in data["mentions"]:
                if app.state.client.client_id in mention["id"]:
                    # Schedule the async task on the event loop
                    asyncio.run_coroutine_threadsafe(process_message_async(data), loop)

        gateway.subscribe("MESSAGE_CREATE", on_message_create)
        await gateway.start()
    except asyncio.CancelledError:
        print("Gateway listener cancelled")
    except Exception as e:
        print(f"Gateway error: {e}")


async def process_message_async(data: dict[str, Any]) -> None:
    """Process Discord message asynchronously.

    Flow:
    1. Generate AI response to understand user intent
    2. Use AI to determine if user wants to create, close, or delete tasks
    3. Perform the appropriate action
    4. Send response back to user

    This runs in a background task to not block the gateway listener.
    """
    author = data["author"]["username"]
    content = data["content"]
    print(f"[ASYNC] Starting message processing for {author}: {content[:50]}...")

    try:
        # Step 1: Generate AI response
        print("[ASYNC] Getting OpenAI key...")
        KEY = os.getenv("OPENAPI_KEY")
        if not KEY:
            print("[ASYNC] ⚠ WARNING: OPENAPI_KEY not set in environment")

        set_openai_key("user", KEY)
        ai_client = AIClientImpl("user")
        print("[ASYNC] Generating AI response...")
        response = ai_client.generate_response(content)
        result = response.content
        print(f"[ASYNC] AI response generated: {result[:60]}...")

        # Step 2: Use AI to determine intent (create, close, delete task)
        print("[ASYNC] Analyzing user intent...")
        intent = await _determine_task_intent_async(content, result)
        print(f"[ASYNC] Detected intent: {intent}")

        # Step 3: Execute appropriate action based on intent
        if intent == "create":
            print("[ASYNC] Intent is to CREATE a task")
            task_created = await _handle_ticket_creation_async(data, result)
            if task_created:
                confirmation_msg = "✓ Task has been created for this issue."
            else:
                confirmation_msg = "⚠ Failed to create task. Please check your Google Tasks."
            app.state.client.send_message(recipient_id=data["author"]["id"], content=confirmation_msg)

        elif intent == "close":
            print("[ASYNC] Intent is to CLOSE/RESOLVE a task")
            task_closed = await _handle_ticket_closure_async(data, content)
            if task_closed:
                confirmation_msg = "✓ Task has been marked as completed."
            else:
                confirmation_msg = "⚠ Could not find or close the task. Please check Google Tasks."
            app.state.client.send_message(recipient_id=data["author"]["id"], content=confirmation_msg)

        elif intent == "delete":
            print("[ASYNC] Intent is to DELETE a task")
            task_deleted = await _handle_task_deletion_async(data, content)
            if task_deleted:
                confirmation_msg = "✓ Task has been deleted."
            else:
                confirmation_msg = "⚠ Could not find or delete the task. Please check Google Tasks."
            app.state.client.send_message(recipient_id=data["author"]["id"], content=confirmation_msg)

        else:
            # Default: just send the AI response
            print("[ASYNC] Intent is NONE - sending AI response")
            app.state.client.send_message(recipient_id=data["author"]["id"], content=result)

        print("[ASYNC] ✓ Message processed successfully")

    except Exception as e:
        print(f"[ASYNC] ✗ Error processing message: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        try:
            app.state.client.send_message(
                recipient_id=data["author"]["id"], content=f"Sorry, I encountered an error: {str(e)[:100]}"
            )
        except Exception as send_error:
            print(f"[ASYNC] ✗ Failed to send error message: {send_error}")


def process_message(data: dict[str, Any]) -> None:
    """If the discord bot is pinged the message will be processed.

    Flow:
    1. Extract message content
    2. Generate AI response
    3. Check if ticket should be created based on message content
    4. Send response back to user
    """

    KEY = os.getenv("OPENAPI_KEY")
    set_openai_key("user", KEY)
    ai_client = AIClientImpl("user")
    response = ai_client.generate_response(data["content"])
    result = response.content

    # Step 1: Send AI response
    app.state.client.send_message(recipient_id=data["author"]["id"], content=result)

    # Step 2: Check if we should create a ticket based on the message
    # You can customize this logic - for example, check if message contains keywords
    # or if AI response suggests creating a ticket
    ticket_created = _handle_ticket_creation(data, result)

    if ticket_created:
        confirmation_msg = "✓ Ticket has been created for this issue."
        app.state.client.send_message(recipient_id=data["author"]["id"], content=confirmation_msg)


async def _determine_task_intent_async(message: str, ai_response: str) -> str:
    """Use AI to determine user intent: create, close, delete, or none.

    Args:
        message: The original user message
        ai_response: The AI-generated response

    Returns:
        One of: "create", "close", "delete", or "none"
    """
    print("[INTENT] Analyzing message for task intent...")
    try:
        message_lower = message.lower()

        # Check for explicit keywords first (more reliable than AI)
        create_keywords = [
            "create",
            "add",
            "new task",
            "new todo",
            "need to",
            "want to",
            "remember",
            "remind",
            "should",
            "have to",
        ]
        close_keywords = ["done", "finish", "complete", "resolved", "fixed", "close", "mark as done"]
        delete_keywords = ["delete", "remove", "forget", "cancel", "discard"]

        # Score the message for each intent
        create_score = sum(1 for kw in create_keywords if kw in message_lower)
        close_score = sum(1 for kw in close_keywords if kw in message_lower)
        delete_score = sum(1 for kw in delete_keywords if kw in message_lower)

        print(f"[INTENT] Keyword scores - create: {create_score}, close: {close_score}, delete: {delete_score}")

        # Determine intent based on scores
        if create_score > close_score and create_score > delete_score and create_score > 0:
            print("[INTENT] ✓ Determined intent: create (from keywords)")
            return "create"
        elif close_score > create_score and close_score > delete_score and close_score > 0:
            print("[INTENT] ✓ Determined intent: close (from keywords)")
            return "close"
        elif delete_score > create_score and delete_score > close_score and delete_score > 0:
            print("[INTENT] ✓ Determined intent: delete (from keywords)")
            return "delete"
        else:
            print("[INTENT] No strong intent detected, defaulting to 'none'")
            return "none"

    except Exception as e:
        print(f"[INTENT] ✗ Error determining intent: {type(e).__name__}: {e}")
        return "none"  # Default to no action on error


async def _handle_task_deletion_async(data: dict[str, Any], message: str) -> bool:
    """Async version: Find and delete a task based on message content.

    Args:
        data: Original Discord message data
        message: The user's message

    Returns:
        True if a task was deleted, False otherwise
    """
    print("[DELETE-TASK] Processing task deletion request...")
    try:
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        print("[DELETE-TASK] Running deletion in executor...")
        result = await loop.run_in_executor(None, _handle_task_deletion, message)
        print(f"[DELETE-TASK] Executor returned: {result}")
        return result
    except Exception as e:
        print(f"[DELETE-TASK] ✗ Task deletion failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def _handle_task_deletion(message: str) -> bool:
    """Find and delete a task based on message content.

    Searches for a task matching keywords from the message,
    then deletes it.

    Args:
        message: The user's message containing deletion request

    Returns:
        True if a task was deleted, False otherwise
    """
    print("[DELETE-TASK-SYNC] Starting task deletion...")
    try:
        # Initialize tickets client
        print("[DELETE-TASK-SYNC] Initializing TicketsClient...")
        tickets_client = TicketsClient(interactive=False)
        print("[DELETE-TASK-SYNC] ✓ TicketsClient initialized")

        # Clean up the message: remove bot mentions and deletion keywords
        import re

        search_query = message.lower()
        # Remove Discord mentions (e.g., <@123456789>)
        search_query = re.sub(r"<@\d+>", "", search_query)
        # Remove deletion keywords
        delete_keywords = ["delete", "remove", "forget", "cancel", "discard", "help me", "task", "bug", "issue", "ticket"]
        for keyword in delete_keywords:
            search_query = search_query.replace(keyword, "")
        search_query = search_query.strip()

        print(f"[DELETE-TASK-SYNC] Cleaned search query: '{search_query}'")

        # Search for matching tasks - if query is too short, get all tasks
        if len(search_query) < 3:
            print("[DELETE-TASK-SYNC] Query too short, searching all tasks")
            matching_tasks = tickets_client.search_tickets(query=None)
        else:
            matching_tasks = tickets_client.search_tickets(query=search_query)

        print(f"[DELETE-TASK-SYNC] Found {len(matching_tasks)} matching tasks")

        if not matching_tasks:
            print("[DELETE-TASK-SYNC] ⚠ No matching task found")
            return False

        # Delete the first matching task
        task_to_delete = matching_tasks[0]
        print(f"[DELETE-TASK-SYNC] Deleting task {task_to_delete.id}: {task_to_delete.title}")

        deleted = tickets_client.delete_ticket(task_to_delete.id)

        if deleted:
            print(f"[DELETE-TASK-SYNC] ✓ Task deleted: {task_to_delete.id}")
        else:
            print("[DELETE-TASK-SYNC] ⚠ Task deletion returned False")

        return deleted

    except Exception as e:
        print(f"[DELETE-TASK-SYNC] ✗ Task deletion failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def _handle_ticket_closure_async(data: dict[str, Any], message: str) -> bool:
    """Async version: Find and close a task based on message content.

    Args:
        data: Original Discord message data
        message: The user's message

    Returns:
        True if a task was closed, False otherwise
    """
    print("[CLOSE-TASK] Processing task closure request...")
    try:
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        print("[CLOSE-TASK] Running closure in executor...")
        result = await loop.run_in_executor(None, _handle_ticket_closure, message)
        print(f"[CLOSE-TASK] Executor returned: {result}")
        return result
    except Exception as e:
        print(f"[CLOSE-TASK] ✗ Task closure failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def _handle_ticket_closure(message: str) -> bool:
    """Find and close a task based on message content.

    Searches for a task matching keywords from the message,
    then marks it as closed.

    Args:
        message: The user's message containing closure request

    Returns:
        True if a task was closed, False otherwise
    """
    print("[CLOSE-TASK-SYNC] Starting task closure...")
    try:
        # Initialize tickets client
        print("[CLOSE-TASK-SYNC] Initializing TicketsClient...")
        tickets_client = TicketsClient(interactive=False)
        print("[CLOSE-TASK-SYNC] ✓ TicketsClient initialized")

        # Clean up the message: remove bot mentions and closure keywords
        import re

        search_query = message.lower()
        # Remove Discord mentions (e.g., <@123456789>)
        search_query = re.sub(r"<@\d+>", "", search_query)
        # Remove closure keywords
        close_keywords = [
            "done",
            "finish",
            "complete",
            "resolved",
            "fixed",
            "close",
            "mark as done",
            "help me",
            "task",
            "bug",
            "issue",
            "ticket",
        ]
        for keyword in close_keywords:
            search_query = search_query.replace(keyword, "")
        search_query = search_query.strip()

        print(f"[CLOSE-TASK-SYNC] Cleaned search query: '{search_query}'")

        # Search for all open/in_progress tasks
        if len(search_query) < 3:
            print("[CLOSE-TASK-SYNC] Query too short, searching all tasks")
            open_tickets = tickets_client.search_tickets(query=None)
        else:
            open_tickets = tickets_client.search_tickets(query=search_query)

        print(f"[CLOSE-TASK-SYNC] Found {len(open_tickets)} matching tasks")

        # Find the first matching task (by description/title)
        matching_ticket = None
        if open_tickets:
            matching_ticket = open_tickets[0]
            print(f"[CLOSE-TASK-SYNC] Found matching task: {matching_ticket.id} - {matching_ticket.title}")

        if not matching_ticket:
            print("[CLOSE-TASK-SYNC] ⚠ No matching task found")
            return False

        # Close the task
        print(f"[CLOSE-TASK-SYNC] Closing task {matching_ticket.id}...")
        closed_ticket = tickets_client.update_ticket(matching_ticket.id, status=TicketStatus.CLOSED)

        print(f"[CLOSE-TASK-SYNC] ✓ Task closed: {closed_ticket.id}")
        return True

    except Exception as e:
        print(f"[CLOSE-TASK-SYNC] ✗ Task closure failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def _handle_ticket_creation_async(data: dict[str, Any], ai_response: str) -> bool:
    """Async version: Create a task based on message content and AI response.

    Args:
        data: Original Discord message data
        ai_response: The AI-generated response

    Returns:
        True if a task was created, False otherwise
    """
    print("[CREATE-TASK] Processing task creation request...")
    try:
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        print("[CREATE-TASK] Running task creation in executor...")
        result = await loop.run_in_executor(None, _handle_ticket_creation, data, ai_response)
        print(f"[CREATE-TASK] Executor returned: {result}")
        return result
    except Exception as e:
        print(f"[CREATE-TASK] ✗ Task creation failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def _handle_ticket_creation(data: dict[str, Any], ai_response: str) -> bool:
    """Create a task based on message content and AI response.

    Args:
        data: Original Discord message data
        ai_response: The AI-generated response

    Returns:
        True if a task was created, False otherwise
    """
    print("[CREATE-TASK-SYNC] Starting task creation...")
    try:
        # Initialize tickets client
        print("[CREATE-TASK-SYNC] Initializing TicketsClient...")
        tickets_client = TicketsClient(interactive=False)
        print("[CREATE-TASK-SYNC] ✓ TicketsClient initialized")

        # Extract author info for task assignee
        author_id = data["author"]["id"]

        # Create task with message content as title and AI response as description
        title = f"Discord Issue: {data['content'][:50]}..."  # First 50 chars
        description = f"**Original Message**: {data['content']}\n\n**AI Analysis**: {ai_response}"

        print(f"[CREATE-TASK-SYNC] Creating task: '{title}'")
        task = tickets_client.create_ticket(title=title, description=description, assignee=author_id)

        print(f"[CREATE-TASK-SYNC] ✓ Task created: {task.id}")
        return True

    except Exception as e:
        print(f"[CREATE-TASK-SYNC] ✗ Task creation failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        # Don't fail the message processing if task creation fails
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: startup and shutdown."""
    print("Starting Discord and Google services...")
    init_db()
    # Start Discord listener
    discord_task = asyncio.create_task(listen_for_messages())
    app.state.gateway_task = discord_task
    # Start Google client
    try:
        app.state.google_client = GTaskClient(interactive=False)
    except Exception:
        import logging

        logging.exception("Failed to instantiate GTaskClient")
        app.state.google_client = None  # Optionally handle as needed

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


@app.get("/login", tags=["Authentication"], summary="Get OAuth2 Discord Authorization URL")
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


@app.get("/tasklists", tags=["Tasks"], summary="List all Google Tasklists")
def list_google_tasklists():
    try:
        tasklists = app.state.google_client.list_tasklists()
        # Convert each tasklist to a dict for JSON serialization
        serialized = [t.to_dict() if hasattr(t, "to_dict") else vars(t) for t in tasklists]
        return JSONResponse(
            status_code=200,
            content={"tasklists": serialized, "status": "success"},
        )
    except Exception as e:
        import logging

        logging.exception("Failed to list tasklists")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to list tasklists", "message": str(e), "status": "error"},
        )


@app.get("/tasks", tags=["Tasks"], summary="List all tasks in a Google Tasklist")
def list_google_tasks(tasklist_id: str = Query(..., description="Google Tasklist ID")):
    try:
        tasks = app.state.google_client.list_tasks(tasklist_id)
        serialized = [t.to_dict() if hasattr(t, "to_dict") else vars(t) for t in tasks]
        return JSONResponse(
            status_code=200,
            content={"tasks": serialized, "status": "success"},
        )
    except Exception as e:
        import logging

        logging.exception("Failed to list tasks")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to list tasks", "message": str(e), "status": "error"},
        )
