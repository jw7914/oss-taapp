"""Unit tests for dependency helpers in `openai_client_service.dependencies`."""

from __future__ import annotations

import pytest
from starlette import status

from openai_client_service.src.openai_client_service import dependencies

HTTP_UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED
SESSION_ID = "sid"


@pytest.mark.asyncio
async def test_get_subject_success() -> None:
    """get_subject should return the header value when present."""
    assert await dependencies.get_subject("alice") == "alice"


@pytest.mark.asyncio
async def test_get_subject_missing_header() -> None:
    """Missing subject headers should raise HTTP 401."""
    with pytest.raises(dependencies.HTTPException) as exc:
        await dependencies.get_subject(None)
    assert exc.value.status_code == HTTP_UNAUTHORIZED


@pytest.mark.asyncio
async def test_session_lifecycle() -> None:
    """create/destroy helpers should manage authenticated sessions."""
    dependencies.create_session_for_testing(SESSION_ID, "bob")
    assert await dependencies.get_authenticated_subject(session_id=SESSION_ID) == "bob"
    dependencies.destroy_session_for_testing(SESSION_ID)
    with pytest.raises(dependencies.HTTPException):
        await dependencies.get_authenticated_subject(session_id=SESSION_ID)


@pytest.mark.asyncio
async def test_get_ai_client_uses_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_ai_client should instantiate AIClientImpl with authenticated subject."""

    class DummyClient:
        """Simple stand-in for the AI client implementation."""

        def __init__(self, subject: str) -> None:
            self.subject = subject

    monkeypatch.setattr(dependencies, "AIClientImpl", DummyClient)
    dependencies.create_session_for_testing(SESSION_ID, "carol")
    subject = await dependencies.get_authenticated_subject(SESSION_ID)
    client = dependencies.get_ai_client(subject=subject)
    assert isinstance(client, DummyClient)
    assert client.subject == "carol"
