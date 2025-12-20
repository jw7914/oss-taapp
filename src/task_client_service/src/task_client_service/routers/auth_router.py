"""Router for authentication operations."""

import json
import logging
import os
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


SCOPES = ["https://www.googleapis.com/auth/tasks"]
CREDENTIALS_PATH = "credentials.json"


def get_base_url() -> str:
    """Get the base URL for the service.

    Detects the deployment environment and returns the appropriate base URL:
    - On Render: Uses RENDER_EXTERNAL_URL environment variable
    - Otherwise: Uses OAUTH_REDIRECT_URI or falls back to localhost
    """
    # Check if explicitly set via environment variable
    if os.environ.get("OAUTH_REDIRECT_URI"):
        redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", "")
        # Extract base URL from redirect URI (remove /auth/callback if present)
        if redirect_uri.endswith("/auth/callback"):
            return redirect_uri[:-14]  # Remove "/auth/callback"
        return redirect_uri

    # Check if running on Render
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_external_url:
        # RENDER_EXTERNAL_URL is the full public URL (e.g., https://your-service.onrender.com)
        return render_external_url.rstrip("/")

    # Default to localhost for local development
    return "http://127.0.0.1:8001"


def get_redirect_uri() -> str:
    """Get the OAuth redirect URI for the current environment."""
    base_url = get_base_url()
    return f"{base_url}/auth/callback"


# Default to port 8001 to match the service port
REDIRECT_URI = get_redirect_uri()
logger.info("OAuth redirect URI configured: %s", REDIRECT_URI)


def get_credentials_path() -> Path:
    """Safely retrieve credentials  path."""
    creds_path = Path(CREDENTIALS_PATH)

    if not creds_path.exists():
        msg = f"'{CREDENTIALS_PATH}' not found. Cannot run OAuth flow."
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)
    return creds_path


def credentials_to_dict(creds: Credentials) -> dict[str, Any]:
    """Convert a Credentials object to a JSON-serializable dictionary."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }


def _exchange_code_for_tokens(request: Request) -> dict[str, str]:
    """Exchange authorization code for access and refresh tokens.

    This function handles the server-to-server token exchange step of the OAuth 2.0 flow.
    It receives the authorization code from the callback, validates the state parameter,
    and exchanges the code for access and refresh tokens via Google's token endpoint.
    """
    creds_path = get_credentials_path()

    code = request.query_params.get("code")

    if not code:
        msg = "No authorization code provided. OAuth flow must be initiated via /auth/login"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)

    state: str | None = request.query_params.get("state")
    stored_state: str | None = request.session.pop("oauth_state", None)

    if not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        flow: Flow = Flow.from_client_secrets_file(
            str(creds_path),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        # Exchange authorization code for tokens (server-to-server request to Google)
        flow.fetch_token(code=code, state=state)
        creds: Credentials = flow.credentials

        session_data = credentials_to_dict(creds)

        # Store in session for browser-based requests
        request.session["credentials"] = json.dumps(session_data)  # type: ignore[attr-defined]
        logger.info(
            "Stored credentials in session. Session keys: %s",
            list(request.session.keys()) if hasattr(request.session, "keys") else "N/A",
        )
        # Also store in app.state for programmatic access (e.g., polling from gtask_impl)
        # Store as both 'credentials' and 'current_session_creds' for compatibility
        request.app.state.credentials = session_data  # type: ignore[attr-defined]
        request.app.state.current_session_creds = session_data  # type: ignore[attr-defined]
        logger.info("Stored credentials in app.state")

    except Exception as e:
        logger.exception("Failed to exchange authorization code for tokens")
        raise HTTPException(status_code=500, detail=f"OAuth flow failed: {e!s}") from e
    else:
        logger.info("Successfully obtained credentials from Google OAuth flow")
        return session_data


@router.get("/health-check")
async def get_health_check() -> JSONResponse:
    """Return health check."""
    return JSONResponse(content={"status": "Ok"})


@router.get("/callback")
async def oauth_callback(request: Request) -> Response:
    """Handle OAuth callback from Google."""
    try:
        logger.info("OAuth callback received")
        _exchange_code_for_tokens(request)
        # Verify credentials are in session
        creds_in_session = request.session.get("credentials")
        logger.info(
            "OAuth callback: Credentials in session after storage: %s",
            creds_in_session is not None,
        )
        logger.info(
            "OAuth callback: Session keys after storage: %s",
            list(request.session.keys()) if hasattr(request.session, "keys") else "N/A",
        )
        response = Response(
            content="Authentication successful! You can close this window.",
            status_code=200,
        )
        # Ensure session is saved by accessing it one more time
        # This helps ensure the session middleware saves it
        _ = request.session.get("credentials")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OAuth callback failed")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {e!s}") from e
    else:
        return response


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate OAuth 2.0 login flow.

    This endpoint redirects the user to Google's authorization page.
    """
    creds_path = Path(CREDENTIALS_PATH)
    if not creds_path.exists():
        msg = f"'{CREDENTIALS_PATH}' not found. Cannot run OAuth flow."
        logger.error(msg)
        raise HTTPException(
            status_code=500,
            detail=msg,
        )

    try:
        logger.info("Initiating OAuth flow with redirect URI: %s", REDIRECT_URI)
        flow: Flow = Flow.from_client_secrets_file(
            str(creds_path),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",  # Force consent screen to ensure refresh token
        )
        # Ensure proper typing
        authorization_url = str(authorization_url)
        state = str(state)

        logger.info("Redirecting to Google authorization URL")
        request.session["oauth_state"] = state

    except FileNotFoundError as e:
        msg = f"Credentials file not found: {e}"
        logger.exception(msg)
        raise HTTPException(status_code=500, detail=msg) from e
    except ValueError as e:
        msg = f"Invalid credentials file format: {e}"
        logger.exception(msg)
        raise HTTPException(status_code=500, detail=msg) from e
    except Exception as e:
        logger.exception("Failed to initiate OAuth flow")
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth flow: {e!s}") from e
    else:
        return RedirectResponse(url=authorization_url, status_code=302)


@router.get("/_give_session_creds")
async def give_session_creds(request: Request) -> JSONResponse:
    """Retrieve session credentials (internal endpoint, not user-facing)."""
    # First try to get from app.state (for programmatic access)
    creds_data = getattr(request.app.state, "credentials", None)

    # If not in app.state, try session (for browser-based requests)
    if not creds_data and hasattr(request, "session"):
        creds_json = request.session.get("credentials")
        if creds_json:
            try:
                creds_data = json.loads(creds_json)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse session credentials: %s", e)

    if not creds_data:
        logger.info("No credentials found in session or app.state")
        raise HTTPException(
            status_code=401,
            detail="No active session found. Please log in at /auth/login",
        )

    return JSONResponse(creds_data)


@router.post("/refresh")
async def refresh_credentials(request: Request) -> JSONResponse:
    """Refresh the stored credentials using the refresh token.

    This endpoint refreshes the access token using the stored refresh token
    and updates both the session and app.state with the new credentials.
    """
    # Get current credentials from app.state or session
    creds_data = getattr(request.app.state, "credentials", None)

    if not creds_data and hasattr(request, "session"):
        creds_json = request.session.get("credentials")
        if creds_json:
            try:
                creds_data = json.loads(creds_json)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse session credentials: %s", e)

    if not creds_data:
        raise HTTPException(
            status_code=401,
            detail="No credentials found. Please log in at /auth/login",
        )

    if not creds_data.get("refresh_token"):
        raise HTTPException(
            status_code=400,
            detail="No refresh token available. Please re-authenticate at /auth/login",
        )

    try:
        # Create Credentials object from stored data
        credentials_factory = cast("Any", Credentials)
        creds = cast(
            "Credentials",
            credentials_factory(
                token=creds_data.get("token"),
                refresh_token=creds_data.get("refresh_token"),
                token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=creds_data.get("client_id"),
                client_secret=creds_data.get("client_secret"),
                scopes=creds_data.get("scopes", SCOPES),
            ),
        )

        # Refresh the credentials
        request_factory = cast("Any", GoogleRequest)
        request_adapter = request_factory()
        creds.refresh(request_adapter)

        # Convert back to dict
        refreshed_data = credentials_to_dict(creds)

        # Update session and app.state
        if hasattr(request, "session"):
            request.session["credentials"] = json.dumps(refreshed_data)
        request.app.state.credentials = refreshed_data
        request.app.state.current_session_creds = refreshed_data  # type: ignore[attr-defined]

        logger.info("Successfully refreshed credentials")
        return JSONResponse(refreshed_data)

    except (GoogleAuthError, RefreshError) as e:
        logger.exception("Failed to refresh credentials")
        raise HTTPException(
            status_code=401,
            detail=f"Failed to refresh credentials: {e!s}. Please re-authenticate at /auth/login",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error refreshing credentials")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error refreshing credentials: {e!s}",
        ) from e
