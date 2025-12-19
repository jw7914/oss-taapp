"""Shared dependencies for the FastAPI service."""

import json
import logging
import os
from contextvars import ContextVar
from typing import Annotated

import gtask_client_impl  # Ensure registration happens
from fastapi import Depends, HTTPException, Request
from task_client_api import Client, get_client

gtask_client_impl.register()

logger = logging.getLogger(__name__)

# Store current request in a context variable (thread-safe alternative to global)
# This allows gtask_impl.py to access the request object to get app.state
current_request: ContextVar[Request | None] = ContextVar("current_request", default=None)


def get_task_client(request: Request) -> Client:
    """Get the task client, creating it lazily if needed with session credentials.

    On first access to a task/tasklist route, if credentials aren't available,
    this will attempt to create the client with interactive=True, which will
    trigger the OAuth authentication flow.
    """
    current_request.set(request)

    session_creds = None
    # Log session info for debugging
    logger.info(
        "get_task_client: Session keys: %s",
        list(request.session.keys()) if hasattr(request.session, "keys") else "N/A",
    )
    credentials_json = request.session.get("credentials")
    logger.info(
        "get_task_client: Checking session for credentials. credentials_json is None: %s",
        credentials_json is None,
    )
    if credentials_json:
        try:
            session_creds = json.loads(credentials_json)
            logger.info("get_task_client: Found and parsed credentials in session")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse session credentials: %s", e)
    else:
        logger.info("get_task_client: No credentials found in session")

    request.app.state.current_session_creds = session_creds
    logger.info(
        "get_task_client: Set app.state.current_session_creds to: %s",
        session_creds is not None,
    )

    base_url = f"{request.url.scheme}://{request.url.netloc}"
    os.environ["TASK_SERVICE_BASE_URL"] = base_url

    # First, try to get client with interactive=False (normal flow)
    try:
        client = get_client(interactive=False)
    except RuntimeError as e:
        # If credentials aren't available, try interactive=True to trigger auth flow
        error_msg = str(e)
        if "Failed to obtain credentials" in error_msg or "credentials" in error_msg.lower():
            logger.info(
                "No credentials found. Attempting to initialize client with interactive=True "
                "to trigger authentication flow."
            )
            try:
                # This will trigger the OAuth flow automatically
                client = get_client(interactive=True)
            except RuntimeError as interactive_error:
                logger.warning(
                    "Interactive authentication flow failed: %s. "
                    "Please complete the authentication in your browser.",
                    interactive_error,
                )
                raise HTTPException(
                    status_code=401,
                    detail=(
                        "Authentication required. The OAuth flow should have been initiated. "
                        "Please complete the authentication in your browser, then try again. "
                        "If the browser didn't open, visit /auth/login manually."
                    ),
                ) from interactive_error
            except Exception as interactive_error:
                logger.exception("Unexpected error during interactive authentication")
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Failed to initialize task client with interactive authentication. "
                        "Please try visiting /auth/login manually."
                    ),
                ) from interactive_error
            else:
                logger.info("Task client created successfully after interactive authentication")
                return client
        else:
            # Some other RuntimeError, re-raise it
            logger.warning("Task client initialization failed: %s", e)
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please authenticate via /auth/login first.",
            ) from e
    except Exception as e:
        logger.exception("Failed to initialize task client")
        raise HTTPException(
            status_code=503,
            detail="Task client not available. Please authenticate via /auth/login first.",
        ) from e
    else:
        logger.debug("Task client created for request")
        return client


TaskClientDep = Annotated[Client, Depends(get_task_client)]
