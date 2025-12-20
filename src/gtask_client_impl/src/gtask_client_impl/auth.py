"""OAuth2 Authentication Manager for Google Tasks API.

This module handles all OAuth2 authentication flows for the Google Tasks client,
including interactive and non-interactive authentication modes.
"""

import importlib
import importlib.util
import json
import logging
import os
import secrets
import socket
import threading
import time
import webbrowser
from collections.abc import Callable
from enum import IntEnum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, cast
from urllib.parse import parse_qs, urlencode, urlparse

if TYPE_CHECKING:
    from fastapi import Request as FastAPIRequest

import requests
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource
from requests.exceptions import RequestException


class HTTPStatus(IntEnum):
    """HTTP status codes used in the API."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


# Find project root (where .env file is located)
# This file is at: src/gtask_client_impl/src/gtask_client_impl/auth.py
# Project root is 5 levels up
_project_root = Path(__file__).parent.parent.parent.parent.parent
_env_file = _project_root / ".env"

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    if _env_file.exists():
        load_dotenv(_env_file, override=True)
    else:
        logger = logging.getLogger(__name__)
        logger.debug("No .env file found at %s", _env_file)
except ImportError:
    # If python-dotenv is not available, check if .env file exists
    # and manually load it
    if _env_file.exists():
        with _env_file.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    else:
        logger = logging.getLogger(__name__)
        logger.debug("No .env file found at %s", _env_file)


class OAuthManager:
    """Manages OAuth2 authentication for Google Tasks API.

    This class handles all authentication flows including:
    - Environment variable authentication
    - Interactive OAuth flow
    - Session-based authentication via FastAPI service
    """

    CREDENTIALS_PATH: str = "credentials.json"
    OAUTH_TOKEN_URI: str = "https://oauth2.googleapis.com/token"  # noqa: S105
    SCOPES: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/tasks",
    ]
    SERVICE_BASE_URL: str = os.environ.get("TASK_SERVICE_BASE_URL", "http://127.0.0.1:8001")

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the OAuth manager.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.

        """
        self.logger = logger or logging.getLogger(__name__)

    def select_credentials(self, *, interactive: bool) -> Credentials | None:
        """Select credentials based on interactive mode.

        Args:
            interactive: Whether to use interactive authentication flow.

        Returns:
            Credentials object if successful, None otherwise.

        """
        self.logger.info("select_credentials: Called with interactive=%s", interactive)
        creds: Credentials | None = None

        if not interactive:
            self.logger.info("select_credentials: Using non-interactive flow")
            creds = self._get_non_interactive_credentials()
        elif interactive:
            self.logger.info("select_credentials: Using interactive flow")
            creds = self._get_interactive_credentials()

        self.logger.info("select_credentials: Before refresh, creds is: %s", creds is not None)
        result = self._refresh_credentials_if_needed(creds)
        self.logger.info("select_credentials: After refresh, result is: %s", result is not None)
        return result

    def _is_in_fastapi_context(self) -> bool:
        """Check if we're running in a FastAPI service context.

        Returns:
            True if running in FastAPI service context, False otherwise.

        """
        # Check if the dependencies module is available
        try:
            if importlib.util.find_spec("task_client_service.dependencies") is None:
                return False
        except (ModuleNotFoundError, ValueError):
            return False
            # Module doesn't exist or invalid module path


        # Try to import the dependencies module
        try:
            deps_module = importlib.import_module("task_client_service.dependencies")
        except ImportError:
            return False

        # Check if current_request is available
        if not hasattr(deps_module, "current_request"):
            return False

        # Try to get the current request from context
        try:
            request = deps_module.current_request.get()
        except (AttributeError, RuntimeError, KeyError):
            return False
        else:
            return request is not None

    def _get_non_interactive_credentials(self) -> Credentials | None:
        """Get credentials in non-interactive mode.

        Priority order:
        1. Session credentials (from FastAPI request context) - preferred for web requests
        2. Environment variable credentials (from .env file) - only if NOT in FastAPI context

        For multi-user web services, we should ONLY use session credentials and NOT
        fall back to environment variables, as env vars are shared across all users.
        """
        self.logger.info(
            "_get_non_interactive_credentials: Starting non-interactive credential retrieval",
        )

        # Check if we're in FastAPI service context
        in_fastapi_context = self._is_in_fastapi_context()
        self.logger.info(
            "_get_non_interactive_credentials: Running in FastAPI context: %s", in_fastapi_context,
        )

        # First, try to get session credentials (preferred for web requests)
        self.logger.info(
            "_get_non_interactive_credentials: Attempting to get session credentials first",
        )
        try:
            creds = self._get_session_credentials()
            if creds and creds.valid:
                self.logger.info(
                    "_get_non_interactive_credentials: Successfully obtained "
                    "valid credentials from session",
                )
                return creds
            if creds:
                self.logger.info(
                    "_get_non_interactive_credentials: Got session credentials "
                    "but they are invalid",
                )
            else:
                self.logger.info("_get_non_interactive_credentials: No session credentials found")
        except RequestException as e:
            self.logger.info(
                "_get_non_interactive_credentials: Could not get session credentials: %s", e,
            )
        except (AttributeError, ImportError, RuntimeError, OSError) as e:
            self.logger.info(
                "_get_non_interactive_credentials: Exception getting session credentials: %s", e,
            )

        # If we're in FastAPI context, check if env fallback is allowed
        # (multi-user web service should only use session-based auth unless explicitly allowed)
        if in_fastapi_context:
            allow_env = os.environ.get("TASKS_ALLOW_ENV_IN_SERVICE", "").lower() == "true"
            if not allow_env:
                self.logger.info(
                    """_get_non_interactive_credentials:
                    In FastAPI context, not falling back to env. """
                    "User must authenticate via /auth/login",
                )
                return None
            self.logger.info(
                """_get_non_interactive_credentials:
                In FastAPI context but TASKS_ALLOW_ENV_IN_SERVICE=true, """
                "allowing env fallback",
            )

        # Fall back to environment variables (only for non-FastAPI contexts)
        self.logger.info(
            "_get_non_interactive_credentials: Not in FastAPI context, falling back to env",
        )
        creds = self._auth_from_env(interactive=False)
        self.logger.info(
            "_get_non_interactive_credentials: _auth_from_env returned: %s", creds is not None,
        )
        if creds:
            self.logger.info(
                "_get_non_interactive_credentials: Successfully obtained credentials from env",
            )
        else:
            self.logger.info(
                "_get_non_interactive_credentials: No credentials found in env or session",
            )
        return creds

    def _get_interactive_credentials(self) -> Credentials | None:
        """Get credentials in interactive mode."""
        # If in FastAPI context, check if env fallback is allowed
        # (multi-user web service should only use session-based auth unless explicitly allowed)
        in_fastapi_context = self._is_in_fastapi_context()
        if not in_fastapi_context:
            # For non-FastAPI contexts (CLI/standalone), try env first
            creds = self._auth_from_env(interactive=True)
            if creds:
                return creds
        elif in_fastapi_context:
            # In FastAPI context, check if env fallback is allowed
            allow_env = os.environ.get("TASKS_ALLOW_ENV_IN_SERVICE", "").lower() == "true"
            if allow_env:
                self.logger.info(
                    """_get_interactive_credentials:
                    In FastAPI context but TASKS_ALLOW_ENV_IN_SERVICE=true, """
                    "allowing env fallback",
                )
                creds = self._auth_from_env(interactive=True)
                if creds:
                    return creds

        client_id = os.environ.get("TASKS_CLIENT_ID")
        client_secret = os.environ.get("TASKS_CLIENT_SECRET")
        refresh_token = os.environ.get("TASKS_REFRESH_TOKEN")
        service_available = self._check_service_availability()

        self._validate_interactive_auth_state(
            client_id, client_secret, refresh_token, service_available=service_available,
        )

        if service_available:
            return self._get_credentials_via_service()
        raise RuntimeError(self._get_service_unavailable_error_msg(client_id, client_secret))

    def _validate_interactive_auth_state(
        self,
        client_id: str | None,
        client_secret: str | None,
        refresh_token: str | None,
        *,
        service_available: bool,
    ) -> None:
        """Validate the authentication state and raise errors if invalid."""
        if client_id and client_secret and not refresh_token and not service_available:
            msg = (
                "Failed to obtain credentials via interactive OAuth flow. "
                "Please ensure your browser can open and you complete the "
                "authentication. Alternatively, set TASKS_REFRESH_TOKEN in "
                "your .env file, or start the FastAPI server and authenticate "
                f"via {self.SERVICE_BASE_URL}/auth/login"
            )
            raise RuntimeError(msg)

        if client_id and client_secret and refresh_token and not service_available:
            msg = (
                "Refresh token in .env file is invalid or expired, and "
                "interactive OAuth flow failed. Please ensure your browser can "
                "open and you complete the authentication, or remove "
                "TASKS_REFRESH_TOKEN from your .env file to trigger a new "
                "interactive flow. Alternatively, start the FastAPI server and "
                f"authenticate via {self.SERVICE_BASE_URL}/auth/login"
            )
            raise RuntimeError(msg)

    def _get_credentials_via_service(self) -> Credentials | None:
        """Get credentials via the FastAPI service."""
        self.logger.info(
            "No valid credentials found. Initiating login flow via %s/auth/login",
            self.SERVICE_BASE_URL,
        )
        creds = self._initiate_api_login_flow()
        if not creds:
            msg = (
                "Failed to obtain credentials through login flow. "
                f"Please authenticate via {self.SERVICE_BASE_URL}/auth/login"
            )
            raise RuntimeError(msg)
        return creds

    def _get_service_unavailable_error_msg(
        self, client_id: str | None, client_secret: str | None,
    ) -> str:
        """Get error message when service is unavailable."""
        if not client_id or not client_secret:
            return (
                "FastAPI server is not running and TASKS_CLIENT_ID or "
                "TASKS_CLIENT_SECRET not found in environment. "
                "Please set TASKS_CLIENT_ID and TASKS_CLIENT_SECRET in your "
                ".env file, or start the FastAPI server and authenticate "
                f"via {self.SERVICE_BASE_URL}/auth/login"
            )
        return (
            "FastAPI server is not running and authentication failed. "
            "Please check your .env file has TASKS_CLIENT_ID and "
            "TASKS_CLIENT_SECRET set correctly, or start the FastAPI "
            f"server and authenticate via {self.SERVICE_BASE_URL}/auth/login"
        )

    def _refresh_credentials_if_needed(self, creds: Credentials | None) -> Credentials | None:
        """Refresh credentials if they are invalid but have a refresh token."""
        self.logger.info(
            "_refresh_credentials_if_needed: Called with creds=%s, valid=%s, has_refresh_token=%s",
            creds is not None,
            creds.valid if creds else None,
            bool(creds.refresh_token if creds else None),
        )
        if not creds or creds.valid or not creds.refresh_token:
            self.logger.info(
                "_refresh_credentials_if_needed: No refresh needed. creds=%s, "
                "valid=%s, has_refresh_token=%s",
                creds is not None,
                creds.valid if creds else None,
                bool(creds.refresh_token if creds else None),
            )
            return creds

        self.logger.info("_refresh_credentials_if_needed: Attempting to refresh credentials")
        try:
            creds.refresh(Request())  # type: ignore[no-untyped-call]
            self.logger.info("_refresh_credentials_if_needed: Successfully refreshed credentials")
        except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
            self.logger.warning(
                "_refresh_credentials_if_needed: Failed to refresh credentials: %s", e,
            )
            self.logger.info(
                "_refresh_credentials_if_needed: Attempting to get session credentials as fallback",
            )
            creds = self._get_session_credentials()
            if not creds or not creds.valid:
                msg = "Failed to refresh credentials and no valid session credentials found."
                self.logger.exception("_refresh_credentials_if_needed: %s", msg)
                raise RuntimeError(msg) from e
            self.logger.info(
                "_refresh_credentials_if_needed: Successfully obtained session credentials",
            )

        return creds

    def _get_fastapi_request(self) -> "FastAPIRequest | None":
        """Get the current FastAPI request from context.

        Returns:
            FastAPI request object if available, None otherwise.

        """
        # Check if the dependencies module is available
        if importlib.util.find_spec("task_client_service.dependencies") is None:
            self.logger.info("_get_fastapi_request: dependencies module not found")
            return None

        # Try to import the dependencies module
        try:
            deps_module = importlib.import_module("task_client_service.dependencies")
        except ImportError as e:
            self.logger.info("Could not import dependencies module: %s", e)
            return None

        # Check if current_request is available
        if not hasattr(deps_module, "current_request"):
            self.logger.info(
                "_get_fastapi_request: current_request not found in dependencies module",
            )
            return None

        # Try to get the current request from context
        try:
            return cast("FastAPIRequest | None", deps_module.current_request.get())
        except (AttributeError, RuntimeError, KeyError) as e:
            self.logger.info("No FastAPI request context: %s", e)
            return None

    def _get_creds_data_from_app_state(self, request: "FastAPIRequest") -> dict[str, Any] | None:
        """Get credentials data from FastAPI app state.

        Args:
            request: FastAPI request object.

        Returns:
            Credentials data dictionary if found, None otherwise.

        """
        try:
            creds_data = getattr(request.app.state, "current_session_creds", None)
            self.logger.info(
                "_get_creds_data_from_app_state: current_session_creds from app.state: %s",
                creds_data is not None,
            )
        except AttributeError as e:
            self.logger.info("No current_session_creds in app.state: %s", e)
            creds_data = None
        return creds_data

    def _get_creds_data_from_session(self, request: "FastAPIRequest") -> dict[str, Any] | None:
        """Get credentials data from FastAPI session.

        Args:
            request: FastAPI request object.

        Returns:
            Credentials data dictionary if found, None otherwise.

        """
        if not hasattr(request, "session"):
            return None

        try:
            credentials_json = request.session.get("credentials")
            self.logger.info(
                "_get_creds_data_from_session: session.get('credentials'): %s",
                credentials_json is not None,
            )
            if not credentials_json:
                self.logger.info("_get_creds_data_from_session: No credentials in session dict")
                return None

            try:
                creds_data = json.loads(credentials_json)
                self.logger.info(
                    "_get_creds_data_from_session: Found credentials in session, setting app.state",
                )
                # Also set it in app.state for future use
                request.app.state.current_session_creds = creds_data
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.info("Failed to parse session credentials: %s", e)
                return None
            else:
                return cast("dict[str, Any]", creds_data)
        except AttributeError as e:
            self.logger.info("No session attribute on request: %s", e)
            return None

    def _get_session_credentials(self) -> Credentials | None:
        """Try to obtain credentials from FastAPI context, or return None if unavailable.

        This method will NEVER trigger interactive auth flows or open browsers.
        It only attempts to retrieve existing credentials from the FastAPI request context.

        Returns:
            Credentials object if found in FastAPI context, None otherwise.

        """
        self.logger.info(
            "_get_session_credentials: Attempting to retrieve credentials from FastAPI context",
        )

        request = self._get_fastapi_request()
        if request is None:
            self.logger.info("_get_session_credentials: request is None")
            return None

        # First, try to get credentials from app state (set by get_task_client)
        creds_data = self._get_creds_data_from_app_state(request)

        # If not in app.state, try to get from session directly
        if creds_data is None:
            creds_data = self._get_creds_data_from_session(request)

        if creds_data is None:
            self.logger.info(
                "_get_session_credentials: No credentials found in app.state or session",
            )
            return None

        # Create credentials from the data (this may fail, but won't trigger browser)
        try:
            creds = self._create_credentials_from_dict(creds_data)
        except (KeyError, ValueError, GoogleAuthError, TypeError) as e:
            self.logger.debug("Failed to create credentials from app state: %s", e)
            return None
        else:
            if creds and creds.valid:
                self.logger.debug("Retrieved valid credentials from session")
            else:
                self.logger.debug("Retrieved invalid credentials from session")
            return creds

    def _get_creds_from_fallback_http(self) -> Credentials | None:
        """Try to obtain credentials using fallback HTTP request."""
        try:
            response = requests.get(
                f"{self.SERVICE_BASE_URL}/auth/_give_session_creds",
                timeout=5,
            )
        except RequestException as e:
            self.logger.debug("Failed to connect to FastAPI service for session credentials: %s", e)
            return None

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            self.logger.info("No credentials found in session. User needs to authenticate.")
            return None
        if response.status_code != HTTPStatus.OK:
            self.logger.warning(
                "Failed to retrieve session credentials: HTTP %d",
                response.status_code,
            )
            return None
        try:
            creds_data = response.json()
            return self._create_credentials_from_dict(creds_data)
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            self.logger.warning("Failed to parse session credentials: %s", e)
        return None

    def _initiate_api_login_flow(self) -> Credentials | None:
        """Initiate OAuth login flow through the API and wait for credentials.

        Opens a browser window to the login endpoint and polls for credentials
        until the user completes authentication.

        Returns:
            Credentials object if authentication succeeds, None otherwise.

        """
        login_url = f"{self.SERVICE_BASE_URL}/auth/login"

        # First, check if the service is available
        # If not available (e.g., during startup), return None
        try:
            # Try to connect to the service to see if it's ready
            response = requests.get(
                f"{self.SERVICE_BASE_URL}/auth/_give_session_creds",
                timeout=2,
            )
            # If we get any response (even 401), the service is available
            service_available = True
            has_creds = response.status_code == HTTPStatus.OK
        except RequestException:
            # Service is not available yet (e.g., during startup)
            self.logger.debug(
                "Service not available yet. Cannot initiate login flow. "
                "Please authenticate via %s after service starts.",
                login_url,
            )
            return None

        # If service is available but no credentials, open browser and poll
        if service_available and not has_creds:
            self.logger.info("Opening browser to %s", login_url)

            try:
                # Open browser to login endpoint
                webbrowser.open(login_url)
            except (OSError, RuntimeError) as e:
                self.logger.warning(
                    "Failed to open browser: %s. Please visit %s manually", e, login_url,
                )
                # Continue anyway - user can open manually

            # Poll for credentials with timeout
            max_wait_time = 300  # 5 minutes
            poll_interval = 2  # Check every 2 seconds
            start_time = time.time()

            self.logger.info("Waiting for authentication to complete...")

            while time.time() - start_time < max_wait_time:
                try:
                    creds = self._get_session_credentials()
                    if creds and creds.valid:
                        self.logger.info("Successfully obtained credentials from login flow")
                        return creds
                except RequestException:
                    # Service might not be ready yet, continue polling
                    pass

                time.sleep(poll_interval)

            self.logger.warning(
                "Timeout waiting for authentication. Please complete login at %s",
                login_url,
            )
            return None

        # If credentials already exist, return them
        if has_creds:
            try:
                creds_data = response.json()
                return self._create_credentials_from_dict(creds_data)
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                self.logger.warning("Failed to parse credentials: %s", e)

        return None

    def _create_credentials_from_dict(self, creds_data: dict[str, Any]) -> Credentials | None:
        """Create Credentials object from dictionary data."""
        try:
            creds = Credentials(  # type: ignore[no-untyped-call]
                token=creds_data.get("token"),
                refresh_token=creds_data.get("refresh_token"),
                token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=creds_data.get("client_id"),
                client_secret=creds_data.get("client_secret"),
                scopes=creds_data.get("scopes", self.SCOPES),
            )

            # Refresh if needed
            if not creds.valid and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                    self.logger.warning("Failed to refresh session credentials: %s", e)
                    return None

        except (TypeError, ValueError, GoogleAuthError) as e:
            self.logger.warning("Failed to create credentials from dict: %s", e)
            return None
        else:
            return creds

    def _save_refresh_token_to_env(self, refresh_token: str) -> None:
        """Save refresh token to .env file and os.environ."""
        # Set in current environment
        os.environ["TASKS_REFRESH_TOKEN"] = refresh_token

        # Try to save to .env file
        try:
            env_path = _env_file
            if not env_path.exists():
                # Create .env file if it doesn't exist
                env_path.touch()

            # Read existing .env content
            lines: list[str] = []
            if env_path.exists():
                with env_path.open() as f:
                    lines = f.readlines()

            # Check if TASKS_REFRESH_TOKEN already exists
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith("TASKS_REFRESH_TOKEN="):
                    lines[i] = f"TASKS_REFRESH_TOKEN={refresh_token}\n"
                    found = True
                    break

            # If not found, append it
            if not found:
                lines.append(f"TASKS_REFRESH_TOKEN={refresh_token}\n")

            # Write back to .env file
            with env_path.open("w") as f:
                f.writelines(lines)

            self.logger.info("Saved refresh token to .env file")
        except (OSError, PermissionError) as e:
            self.logger.warning("Failed to save refresh token to .env file: %s", e)

    def _check_service_availability(self) -> bool:
        """Check if the FastAPI service is available.

        Returns:
            True if service is available, False otherwise.

        """
        try:
            requests.get(
                f"{self.SERVICE_BASE_URL}/auth/_give_session_creds",
                timeout=2,
            )
        except RequestException:
            return False
        else:
            # If we get any response (even 401), the service is available
            return True

    def _load_credentials_from_file(
        self, client_id: str | None, client_secret: str | None,
    ) -> tuple[str | None, str | None]:
        """Load client credentials from credentials.json file.

        Args:
            client_id: Existing client_id (if any)
            client_secret: Existing client_secret (if any)

        Returns:
            Tuple of (client_id, client_secret) loaded from file, or (None, None) if failed.

        """
        if client_id and client_secret:
            return client_id, client_secret

        creds_path = Path(self.CREDENTIALS_PATH)
        if not creds_path.exists():
            creds_path = _project_root / self.CREDENTIALS_PATH

        if not creds_path.exists():
            return client_id, client_secret

        try:
            with creds_path.open() as f:
                client_config = json.load(f)
            if "installed" in client_config:
                return (
                    client_config["installed"]["client_id"],
                    client_config["installed"]["client_secret"],
                )
            if "web" in client_config:
                return (
                    client_config["web"]["client_id"],
                    client_config["web"]["client_secret"],
                )
            self.logger.warning("Invalid credentials.json format")
        except (OSError, FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            self.logger.warning("Failed to load credentials from credentials.json: %s", e)

        return client_id, client_secret

    def _get_client_credentials(
        self, client_id: str | None, client_secret: str | None,
    ) -> tuple[str | None, str | None]:
        """Get client credentials from file or environment variables.

        Args:
            client_id: OAuth2 client ID (optional)
            client_secret: OAuth2 client secret (optional)

        Returns:
            Tuple of (client_id, client_secret) or (None, None) if not found.

        """
        client_id, client_secret = self._load_credentials_from_file(client_id, client_secret)

        if not client_id:
            client_id = os.environ.get("TASKS_CLIENT_ID")
        if not client_secret:
            client_secret = os.environ.get("TASKS_CLIENT_SECRET")

        return client_id, client_secret

    def _run_interactive_flow_for_refresh_token(
        self, client_id: str | None = None, client_secret: str | None = None,
    ) -> Credentials | None:
        """Run interactive OAuth flow to obtain refresh token using direct Google API calls.

        This is used when client_id and client_secret are in env but refresh_token is missing.
        Can use either credentials.json file or client_id/client_secret from env.

        Args:
            client_id: OAuth2 client ID (optional, will use env var if not provided)
            client_secret: OAuth2 client secret (optional, will use env var if not provided)

        Returns:
            Credentials object if successful, None otherwise.

        """
        client_id, client_secret = self._get_client_credentials(client_id, client_secret)

        if not client_id or not client_secret:
            self.logger.warning(
                "Cannot run interactive flow: credentials.json not found and "
                "TASKS_CLIENT_ID/TASKS_CLIENT_SECRET not set in environment.",
            )
            return None

        try:
            self.logger.info(
                "Running interactive OAuth flow to obtain refresh token. "
                "Please complete authentication in your browser.",
            )
            creds = self._run_manual_oauth_flow(client_id, client_secret)
        except (OSError, GoogleAuthError, ValueError, RequestException) as e:
            self.logger.warning("Failed to run interactive OAuth flow: %s", e)
            return None

        if creds and creds.refresh_token:
            self._save_refresh_token_to_env(creds.refresh_token)
            return creds

        self.logger.warning("No refresh token obtained from OAuth flow")
        return None

    def _run_manual_oauth_flow(self, client_id: str, client_secret: str) -> Credentials | None:
        """Run manual OAuth2 flow using direct Google API calls.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret

        Returns:
            Credentials object if successful, None otherwise.

        """
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Find an available port
        redirect_port = self._find_available_port()
        redirect_uri = f"http://localhost:{redirect_port}"

        # Build authorization URL
        auth_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.SCOPES),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",  # Force consent screen to ensure refresh token
            "state": state,
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"

        # Create callback handler and start server
        oauth_state: dict[str, str | None] = {"auth_code": None, "error": None}
        handler_class = self._create_oauth_callback_handler(oauth_state)
        server = HTTPServer(("localhost", redirect_port), handler_class)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            self._open_browser_for_auth(auth_url)
            auth_code = self._wait_for_oauth_callback(oauth_state, server, server_thread)

            if not auth_code:
                self.logger.warning("Timeout waiting for authorization code")
                return None

            # Exchange authorization code for tokens
            return self._exchange_code_for_tokens(auth_code, client_id, client_secret, redirect_uri)

        except Exception:
            self.logger.exception("Error in manual OAuth flow")
            return None
        finally:
            # Ensure server is shut down
            try:
                server.shutdown()
                server.server_close()
            except (OSError, AttributeError, RuntimeError) as e:
                self.logger.debug("Error shutting down server (may already be shut down): %s", e)

    def _exchange_code_for_tokens(
        self,
        auth_code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> Credentials | None:
        """Exchange authorization code for access and refresh tokens.

        Args:
            auth_code: Authorization code from OAuth callback.
            client_id: OAuth2 client ID.
            client_secret: OAuth2 client secret.
            redirect_uri: Redirect URI used in authorization request.

        Returns:
            Credentials object if successful, None otherwise.

        """
        token_url = self.OAUTH_TOKEN_URI
        token_data = {
            "code": auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = requests.post(token_url, data=token_data, timeout=30)
            response.raise_for_status()
            token_response = response.json()

        except requests.RequestException:
            self.logger.exception("Failed to exchange authorization code for tokens")
            return None
        except (KeyError, ValueError):
            self.logger.exception("Invalid token response")
            return None
        else:
            # Create Credentials object from token response
            credentials_factory = cast("Any", Credentials)
            return cast(
                "Credentials",
                credentials_factory(
                    token=token_response.get("access_token"),
                    refresh_token=token_response.get("refresh_token"),
                    token_uri=token_url,
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=self.SCOPES,
                ),
            )

    def _create_oauth_callback_handler(
        self, oauth_state: dict[str, str | None],
    ) -> type[BaseHTTPRequestHandler]:
        """Create OAuth callback handler class.

        Args:
            oauth_state: Dictionary to store auth_code and error (mutable state).

        Returns:
            OAuth callback handler class.

        """
        return self._build_oauth_handler_class(oauth_state, self.logger)

    def _build_oauth_handler_class(
        self,
        oauth_state: dict[str, str | None],
        logger: logging.Logger,
    ) -> type[BaseHTTPRequestHandler]:
        """Build OAuth callback handler class with helper functions.

        Args:
            oauth_state: Dictionary to store auth_code and error (mutable state).
            logger: Logger instance for logging.

        Returns:
            OAuth callback handler class.

        """
        return self._create_handler_class(oauth_state, logger)

    @staticmethod
    def _is_oauth_callback(query_params: dict[str, list[str]]) -> bool:
        """Check if request has OAuth parameters."""
        return "code" in query_params or "error" in query_params or "state" in query_params

    @staticmethod
    def _extract_oauth_params(query_params: dict[str, list[str]]) -> dict[str, str | None]:
        """Extract OAuth parameters from query string."""
        return {
            "state": (query_params.get("state", [None])[0] if "state" in query_params else None),
            "code": (query_params.get("code", [None])[0] if "code" in query_params else None),
            "error": (query_params.get("error", [None])[0] if "error" in query_params else None),
        }

    @staticmethod
    def _send_non_oauth_response(handler: BaseHTTPRequestHandler) -> None:
        """Send response for non-OAuth requests."""
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-type", "text/html")
        handler.end_headers()
        handler.wfile.write(b"<html><body></body></html>")
        handler.wfile.flush()

    @staticmethod
    def _send_error_response(
        handler: BaseHTTPRequestHandler, error_msg: str | None, logger: logging.Logger,
    ) -> None:
        """Send error response."""
        handler.send_response(HTTPStatus.BAD_REQUEST)
        handler.send_header("Content-type", "text/html")
        handler.end_headers()
        error_html = f"<html><body><h1>Authentication Error</h1><p>{error_msg}</p></body></html>"
        handler.wfile.write(error_html.encode())
        handler.wfile.flush()
        logger.error("OAuth error received: %s", error_msg)

    @staticmethod
    def _send_success_response(handler: BaseHTTPRequestHandler, logger: logging.Logger) -> None:
        """Send success response."""
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-type", "text/html")
        handler.send_header("Connection", "close")
        handler.end_headers()
        success_html = (
            b"<html><body><h1>Authentication Successful</h1>"
            b"<p>You can close this window.</p></body></html>"
        )
        handler.wfile.write(success_html)
        handler.wfile.flush()
        logger.info("Received authorization code, connection will close")

    @staticmethod
    def _send_failed_response(handler: BaseHTTPRequestHandler, logger: logging.Logger) -> None:
        """Send failed response."""
        handler.send_response(HTTPStatus.BAD_REQUEST)
        handler.send_header("Content-type", "text/html")
        handler.end_headers()
        failed_html = (
            b"<html><body><h1>Authentication Failed</h1>"
            b"<p>No authorization code received.</p></body></html>"
        )
        handler.wfile.write(failed_html)
        handler.wfile.flush()
        logger.warning("OAuth callback received but no authorization code or error found")

    @staticmethod
    def _handle_oauth_response(
        handler: BaseHTTPRequestHandler, params: dict[str, str | None], logger: logging.Logger,
    ) -> None:
        """Handle OAuth callback response."""
        if params["error"]:
            OAuthManager._send_error_response(handler, params["error"], logger)
        elif params["code"]:
            OAuthManager._send_success_response(handler, logger)
        else:
            OAuthManager._send_failed_response(handler, logger)

    def _create_handler_class(
        self,
        oauth_state: dict[str, str | None],
        logger: logging.Logger,
    ) -> type[BaseHTTPRequestHandler]:
        """Create the OAuth callback handler class.

        Args:
            oauth_state: Dictionary to store auth_code and error (mutable state).
            logger: Logger instance for logging.

        Returns:
            OAuth callback handler class.

        """

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                query_params = parse_qs(parsed.query)

                if not OAuthManager._is_oauth_callback(query_params):
                    OAuthManager._send_non_oauth_response(self)
                    return

                extracted = OAuthManager._extract_oauth_params(query_params)
                oauth_state["auth_code"] = extracted["code"]
                oauth_state["error"] = extracted["error"]

                OAuthManager._handle_oauth_response(self, extracted, logger)

            def log_message(self, msg_format: str, *args: str) -> None:
                # Suppress default logging
                pass

        return OAuthCallbackHandler

    def _open_browser_for_auth(self, auth_url: str) -> None:
        """Open browser to authorization URL.

        Args:
            auth_url: The authorization URL to open.

        """
        self.logger.info("Opening browser to %s", auth_url)
        try:
            webbrowser.open(auth_url)
        except (OSError, RuntimeError) as e:
            self.logger.warning("Failed to open browser: %s. Please visit %s manually", e, auth_url)

    def _wait_for_oauth_callback(
        self,
        oauth_state: dict[str, str | None],
        server: HTTPServer,
        server_thread: threading.Thread,
    ) -> str | None:
        """Wait for OAuth callback with timeout.

        Args:
            oauth_state: Dictionary containing auth_code and error (updated by handler).
            server: The HTTP server instance.
            server_thread: The server thread.

        Returns:
            Authorization code if received, None otherwise.

        """
        max_wait_time = 300  # 5 minutes
        poll_interval = 0.5  # Check every 0.5 seconds
        start_time = time.time()

        self.logger.info("Waiting for authentication to complete...")

        while time.time() - start_time < max_wait_time:
            auth_code = oauth_state.get("auth_code")
            error = oauth_state.get("error")
            if auth_code or error:
                self.logger.info(
                    "Authentication callback received (auth_code=%s, error=%s)",
                    "present" if auth_code else "None",
                    "present" if error else "None",
                )
                break
            time.sleep(poll_interval)

        # Stop the server
        server.shutdown()
        server.server_close()
        # Give the server a moment to finish handling any pending requests
        time.sleep(0.1)
        server_thread.join(timeout=2)

        return oauth_state.get("auth_code")

    def _find_available_port(self) -> int:
        """Find an available port for the OAuth callback server.

        Returns:
            An available port number.

        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            sock.listen(1)
            return cast("int", sock.getsockname()[1])

    def _auth_from_env(self, *, interactive: bool = False) -> Credentials | None:
        """Attempt to authenticate using environment variables.

        Expected environment variables:
            TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN
            optional: TASKS_TOKEN_URI

        If client_id and client_secret are present but refresh_token is missing,
        and interactive=True, this will attempt to run an interactive OAuth flow
        to obtain the refresh token and save it to the .env file.

        Args:
            interactive: If True and refresh_token is missing, will run interactive OAuth flow.

        Returns:
            A refreshed Credentials object on success, or None on failure.

        """
        self.logger.info("_auth_from_env: Starting with interactive=%s", interactive)
        client_id = os.environ.get("TASKS_CLIENT_ID")
        client_secret = os.environ.get("TASKS_CLIENT_SECRET")
        refresh_token = os.environ.get("TASKS_REFRESH_TOKEN")
        token_uri = os.environ.get("TASKS_TOKEN_URI", "https://oauth2.googleapis.com/token")

        # Log what we found (without exposing secrets)
        self.logger.info(
            "_auth_from_env: client_id=%s, client_secret=%s, refresh_token=%s",
            "present" if client_id else "missing",
            "present" if client_secret else "missing",
            "present" if refresh_token else "missing",
        )

        # If we have client_id and client_secret but no refresh_token, try to get it
        if client_id and client_secret and not refresh_token:
            self.logger.info("_auth_from_env: Client ID and secret found but refresh token missing")
            if interactive:
                self.logger.info(
                    "_auth_from_env: interactive=True, attempting interactive OAuth flow",
                )
                creds = self._run_interactive_flow_for_refresh_token(client_id, client_secret)
                if creds and creds.valid:
                    self.logger.info(
                        "_auth_from_env: Successfully obtained credentials via interactive flow",
                    )
                    return creds
                # If interactive flow failed, log and return None
                self.logger.warning(
                    "_auth_from_env: Interactive OAuth flow failed or was cancelled",
                )
            else:
                # Not interactive mode, can't get refresh token
                self.logger.info(
                    "_auth_from_env: interactive=False, cannot obtain refresh token. "
                    "Returning None.",
                )
            return None

        # If we don't have all required env vars, return None
        if not (client_id and client_secret and refresh_token):
            self.logger.info(
                "_auth_from_env: Missing required env vars. client_id=%s, "
                "client_secret=%s, refresh_token=%s",
                bool(client_id),
                bool(client_secret),
                bool(refresh_token),
            )
            return None

        # Try to use the refresh token
        self.logger.info(
            "_auth_from_env: All required env vars present, attempting to use refresh token",
        )
        try:
            creds = Credentials(  # type: ignore[no-untyped-call]
                None,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES,
            )
            creds.refresh(Request())  # type: ignore[no-untyped-call]
            self.logger.info(
                "_auth_from_env: Successfully authenticated using refresh token from env",
            )
            return creds  # noqa: TRY300
        except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
            self.logger.warning(
                "_auth_from_env: Failed to authenticate using refresh token: %s",
                e,
            )
            # If interactive mode and refresh token failed, try interactive flow
            if interactive:
                self.logger.info(
                    "_auth_from_env: Refresh token invalid, attempting interactive OAuth flow",
                )
                creds = self._run_interactive_flow_for_refresh_token(client_id, client_secret)
                if creds and creds.valid:
                    self.logger.info(
                        "_auth_from_env: Successfully obtained new credentials "
                        "via interactive flow",
                    )
                    return creds
                self.logger.warning("_auth_from_env: Interactive OAuth flow also failed")
            else:
                self.logger.info(
                    "_auth_from_env: interactive=False, not attempting interactive flow",
                )
            return None

    def ensure_service_initialized(
        self, service: Resource | None, build_service: Callable[[Credentials], Resource],
    ) -> Resource:
        """Ensure the service is initialized with valid credentials.

        If service is None, try to get credentials and initialize it.
        Raises RuntimeError if credentials are not available.

        Args:
            service: The current service object (may be None).
            build_service: Function to build the service with credentials.

        Returns:
            Initialized service object.

        """
        if service is None:
            # Try to get credentials again (might have been authenticated since initialization)
            creds = self._get_session_credentials()
            # Only fall back to env if NOT in FastAPI context (multi-user web service)
            if not creds and not self._is_in_fastapi_context():
                creds = self._auth_from_env(interactive=False)
            if not creds:
                creds = self._initiate_api_login_flow()

            if not creds or not creds.valid:
                msg = (
                    "No valid credentials available. Please authenticate via "
                    f"{self.SERVICE_BASE_URL}/auth/login first."
                )
                raise RuntimeError(msg)

            # Refresh if needed
            if not creds.valid and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                    msg = f"Failed to refresh credentials: {e}"
                    raise RuntimeError(msg) from e

            # Initialize the service
            service = build_service(creds)
            self.logger.info("Service initialized with credentials")
        return service
