"""FastAPI dependencies for OpenAI Client Service."""

from typing import Annotated, cast

from fastapi import Cookie, Depends, Header, HTTPException, status

from openai_client_impl import AIClientImpl  # type: ignore[attr-defined]
from openai_service_api.src.openai_service_api.client import AIClient

_SESSION_STORE: dict[str, dict[str, str]] = {}


async def get_subject(x_subject: str | None = Header(default=None)) -> str:
    """Extract and validate the X-Subject header.

    Args:
        x_subject: The X-Subject header value

    Returns:
        The validated subject string

    Raises:
        HTTPException: If X-Subject header is missing

    """
    if not x_subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Subject header. Please provide a user identifier.",
        )
    return x_subject


async def get_authenticated_subject(
    session_id: str | None = Cookie(default=None, alias="session_id"),
) -> str:
    """Return the authenticated subject from the OAuth session cookie.

    Raises 401 if there is no valid session.
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session = _SESSION_STORE.get(session_id)
    if not session or "subject" not in session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return session["subject"]


def _create_session(session_id: str, subject: str) -> None:
    """Create or replace a session with the given subject."""
    _SESSION_STORE[session_id] = {"subject": subject}


def _destroy_session(session_id: str) -> None:
    """Remove a session if it exists."""
    _SESSION_STORE.pop(session_id, None)


def get_ai_client(subject: Annotated[str, Depends(get_authenticated_subject)]) -> AIClient:
    """Return an AIClient instance for the authenticated subject.

    This dependency injects the AI client implementation into route handlers,
    using the authenticated subject from the session cookie.

    Args:
        subject: Authenticated user subject from session (injected via dependency)

    Returns:
        AIClient instance configured for the authenticated user

    Raises:
        HTTPException: If user is not authenticated

    """
    return cast("AIClient", AIClientImpl(subject=subject))


def create_session_for_testing(session_id: str, subject: str) -> None:
    """Create an authenticated session for tests."""
    _create_session(session_id, subject)


def destroy_session_for_testing(session_id: str) -> None:
    """Remove an authenticated session for tests."""
    _destroy_session(session_id)
