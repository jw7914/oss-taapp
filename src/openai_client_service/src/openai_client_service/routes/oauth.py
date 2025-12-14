"""Authentication routes for OpenAI Client Service."""

import base64
import os
import secrets
import time
import urllib.parse
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from openai_client_impl import set_openai_key  # type: ignore[attr-defined]
from openai_client_service.src.openai_client_service.dependencies import (
    _create_session,
    _destroy_session,
    get_authenticated_subject,
)

router = APIRouter()

HTTP_BAD_REQUEST = 400

_PENDING_STATE: dict[str, dict[str, int]] = {}


def _oauth_config() -> dict[str, str]:
    client_id = os.environ.get("OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "")
    auth_url = os.environ.get("OAUTH_AUTH_URL", "")
    token_url = os.environ.get("OAUTH_TOKEN_URL", "")
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", "")
    scope = os.environ.get("OAUTH_SCOPE", "openid profile email")
    userinfo_url = os.environ.get("OAUTH_USERINFO_URL", "")
    if not all([client_id, auth_url, token_url, redirect_uri]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OAuth configuration missing")
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_url": auth_url,
        "token_url": token_url,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "userinfo_url": userinfo_url,
    }


@router.get("/login")  # type: ignore[misc]
def oauth_login() -> Response:
    """Start OAuth2 Authorization Code flow by redirecting to provider."""
    cfg = _oauth_config()
    state = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode().rstrip("=")
    _PENDING_STATE[state] = {"created_at": int(time.time())}

    query = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": cfg["scope"],
        "state": state,
    }
    location = f"{cfg['auth_url']}?{urllib.parse.urlencode(query)}"
    response = RedirectResponse(url=location, status_code=status.HTTP_302_FOUND)
    response.set_cookie("oauth_state", state, httponly=True, secure=True, samesite="lax")
    return response


@router.get("/callback")  # type: ignore[misc]
def oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    oauth_state: str | None = None,
) -> Response:
    """Handle OAuth2 callback, exchange code for tokens, and create a session."""
    cfg = _oauth_config()
    cookie_state = request.cookies.get("oauth_state") if oauth_state is None else oauth_state
    if not code or not state or not cookie_state or state != cookie_state or state not in _PENDING_STATE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state or code")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg["redirect_uri"],
        "client_id": cfg["client_id"],
    }

    with httpx.Client(timeout=10.0) as client:
        data_with_secret = {**data, "client_secret": cfg["client_secret"]} if cfg["client_secret"] else data
        token_resp = client.post(
            cfg["token_url"],
            data=data_with_secret,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if token_resp.status_code >= HTTP_BAD_REQUEST:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Token exchange failed: {token_resp.text}")

    token_json = token_resp.json()

    subject = _extract_subject(token_json, cfg)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to determine subject from tokens")

    session_id = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode().rstrip("=")
    _create_session(session_id, subject)

    _PENDING_STATE.pop(state, None)

    response = RedirectResponse(url="/docs", status_code=status.HTTP_302_FOUND)
    response.set_cookie("session_id", session_id, httponly=True, secure=True, samesite="lax")
    response.delete_cookie("oauth_state")
    return response


def _extract_subject(token_json: dict[str, object], cfg: dict[str, str]) -> str | None:
    """Extract subject from OAuth token response.

    Uses the userinfo endpoint with the access token to securely retrieve
    the user's subject. The access token is validated by the OAuth provider.

    Returns:
        Subject string if found, None otherwise

    Raises:
        None - returns None on any error to allow caller to handle gracefully

    """
    access_token = token_json.get("access_token")
    if not isinstance(access_token, str) or not cfg.get("userinfo_url"):
        return None

    try:
        with httpx.Client(timeout=10.0) as client:
            ui = client.get(cfg["userinfo_url"], headers={"Authorization": f"Bearer {access_token}"})
        if ui.status_code < HTTP_BAD_REQUEST:
            data = ui.json()
            sub = data.get("sub") or data.get("id")
            if isinstance(sub, str) and sub:
                return sub
    except (httpx.HTTPError, ValueError, KeyError):
        pass

    return None


class SetKeyRequest(BaseModel):  # type: ignore[misc]
    """Request model for setting OpenAI API key."""

    api_key: str


@router.post("/set-openai-key")  # type: ignore[misc]
def set_openai_key_endpoint(
    request: SetKeyRequest,
    subject: Annotated[str, Depends(get_authenticated_subject)],
) -> dict[str, str | bool]:
    """Store/replace the per-user OpenAI API key securely.

    The implementation handles encryption of the API key before storage.
    This endpoint requires authentication - users can only set their own API key.
    The subject is derived from the authenticated session.

    Args:
        request: Contains OpenAI API key
        subject: Authenticated user subject from session (injected via dependency)

    Returns:
        Success confirmation with subject

    Raises:
        HTTPException: If API key storage fails or user is not authenticated

    """
    try:
        set_openai_key(subject, request.api_key)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store API key: {e!s}",
        ) from e
    else:
        return {
            "ok": True,
            "subject": subject,
            "message": "OpenAI API key stored securely",
        }


@router.post("/logout")  # type: ignore[misc]
def logout(request: Request) -> Response:
    """Clear session cookie and remove server-side session."""
    sid = request.cookies.get("session_id")
    if sid:
        _destroy_session(sid)
    response = RedirectResponse(url="/docs", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_id")
    return response


@router.get("/whoami")  # type: ignore[misc]
def whoami(subject: Annotated[str, Depends(get_authenticated_subject)]) -> dict[str, str]:
    """Return the authenticated subject derived from the OAuth session."""
    return {"subject": subject}
