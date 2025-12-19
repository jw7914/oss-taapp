"""Unit tests for OAuthManager authentication workflow.

This module contains unit tests for the OAuthManager authentication flow,
mocking all external dependencies.

The implementation supports two main authentication modes:
1. Local use: .env file with TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN
2. Deployed use: FastAPI service with session credentials

Interactive OAuth flow should NEVER run automatically - only when explicitly requested.
"""

import os
from contextvars import ContextVar
from typing import Any
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from requests.exceptions import RequestException

from gtask_client_impl.auth import HTTPStatus, OAuthManager
from gtask_client_impl.gtask_impl import GTaskClient


class TestGTaskClientInitialization:
    """Test cases for GTaskClient initialization."""

    @patch("gtask_client_impl.gtask_impl.build")
    def test_init_with_provided_service_skips_auth(self, mock_build: Any) -> None:
        """Test that providing a service skips authentication."""
        # ARRANGE
        mock_service = Mock()

        # ACT
        client = GTaskClient(service=mock_service)

        # ASSERT
        assert client.service is mock_service
        mock_build.assert_not_called()

    @patch("gtask_client_impl.gtask_impl.build")
    @patch("gtask_client_impl.auth.Credentials")
    @patch("gtask_client_impl.auth.Request")
    @patch.dict(
        os.environ,
        {
            "TASKS_CLIENT_ID": "test_client_id",
            "TASKS_CLIENT_SECRET": "test_client_secret",
            "TASKS_REFRESH_TOKEN": "test_refresh_token",
        },
    )
    def test_init_with_env_vars_success(
        self,
        mock_request: Any,
        mock_creds_class: Any,
        mock_build: Any,
    ) -> None:
        """Test successful initialization with environment variables."""
        # ARRANGE
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds_class.return_value = mock_creds

        mock_service = Mock()
        mock_build.return_value = mock_service

        # ACT
        with patch.object(OAuthManager, "_get_session_credentials") as mock_session:
            mock_session.return_value = None
            client = GTaskClient()

            # ASSERT
            assert client.service is mock_service
            mock_creds_class.assert_called_once_with(
                None,
                refresh_token="test_refresh_token",
                token_uri="https://oauth2.googleapis.com/token",
                client_id="test_client_id",
                client_secret="test_client_secret",
                scopes=OAuthManager.SCOPES,
            )
            mock_creds.refresh.assert_called_once()
            mock_build.assert_called_once_with("tasks", "v1", credentials=mock_creds)

    def test_init_no_valid_credentials_raises_error(self) -> None:
        """Test that initialization raises error when no valid credentials found."""
        # ARRANGE
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(OAuthManager, "_get_session_credentials") as mock_session,
        ):
            mock_session.return_value = None

            # ACT & ASSERT
            with pytest.raises(
                RuntimeError,
                match=r"Failed to obtain credentials. Please check your setup\.",
            ):
                GTaskClient()


class TestOAuthManagerSelectCredentials:
    """Test cases for OAuthManager.select_credentials()."""

    def test_select_credentials_non_interactive_from_env(self) -> None:
        """Test non-interactive credentials selection from environment."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.object(manager, "_get_non_interactive_credentials") as mock_non_interactive,
            patch.object(manager, "_refresh_credentials_if_needed") as mock_refresh,
        ):
            mock_non_interactive.return_value = mock_creds
            mock_refresh.return_value = mock_creds

            # ACT
            result = manager.select_credentials(interactive=False)

            # ASSERT
            assert result is mock_creds
            mock_non_interactive.assert_called_once()
            mock_refresh.assert_called_once_with(mock_creds)

    def test_select_credentials_interactive_from_env(self) -> None:
        """Test interactive credentials selection from environment."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.object(manager, "_get_interactive_credentials") as mock_interactive,
            patch.object(manager, "_refresh_credentials_if_needed") as mock_refresh,
        ):
            mock_interactive.return_value = mock_creds
            mock_refresh.return_value = mock_creds

            # ACT
            result = manager.select_credentials(interactive=True)

            # ASSERT
            assert result is mock_creds
            mock_interactive.assert_called_once()
            mock_refresh.assert_called_once_with(mock_creds)


class TestNonInteractiveCredentials:
    """Test cases for non-interactive credential flow."""

    def test_get_non_interactive_credentials_from_env(self) -> None:
        """Test non-interactive credentials from environment variables."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_get_session_credentials") as mock_session,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_session.return_value = None  # No session credentials
            mock_auth_env.return_value = mock_creds

            # ACT
            result = manager._get_non_interactive_credentials()

            # ASSERT
            assert result is mock_creds
            mock_auth_env.assert_called_once_with(interactive=False)
            mock_session.assert_called_once()

    def test_get_non_interactive_credentials_from_session(self) -> None:
        """Test non-interactive credentials from session when env fails."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_get_session_credentials") as mock_session,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_session.return_value = None  # No session credentials first
            mock_auth_env.return_value = None  # Env also fails
            # But then session succeeds on retry (this test seems to test the wrong flow)
            # Actually, the test name says "from session when env fails", so let's fix it:
            mock_session.return_value = mock_creds  # Session has credentials

            # ACT
            result = manager._get_non_interactive_credentials()

            # ASSERT
            assert result is mock_creds
            # Session is checked first, so it should be called
            mock_session.assert_called_once()
            # Since session returns creds, env should not be called
            mock_auth_env.assert_not_called()

    def test_get_non_interactive_credentials_session_exception(self) -> None:
        """Test non-interactive credentials handles session exception."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_get_session_credentials") as mock_session,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_session.side_effect = RequestException("Connection failed")
            mock_auth_env.return_value = None

            # ACT
            result = manager._get_non_interactive_credentials()

            # ASSERT
            assert result is None

    def test_get_non_interactive_credentials_in_fastapi_context_no_env_fallback(self) -> None:
        """Test non-interactive credentials in FastAPI context does not fall back to env."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(os.environ, {"TASKS_ALLOW_ENV_IN_SERVICE": ""}, clear=False),
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_get_session_credentials") as mock_session,
        ):
            mock_is_fastapi.return_value = True  # In FastAPI context
            mock_session.return_value = None  # No session credentials

            # ACT
            result = manager._get_non_interactive_credentials()

            # ASSERT
            assert result is None
            # Should NOT call _auth_from_env when in FastAPI context
            mock_auth_env.assert_not_called()
            mock_session.assert_called_once()


class TestInteractiveCredentials:
    """Test cases for interactive credential flow."""

    def test_get_interactive_credentials_from_env(self) -> None:
        """Test interactive credentials from environment variables."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_auth_env.return_value = mock_creds

            # ACT
            result = manager._get_interactive_credentials()

            # ASSERT
            assert result is mock_creds
            mock_auth_env.assert_called_once_with(interactive=True)

    def test_get_interactive_credentials_via_service(self) -> None:
        """Test interactive credentials via FastAPI service."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_check_service_availability") as mock_check_service,
            patch.object(manager, "_get_credentials_via_service") as mock_get_via_service,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_auth_env.return_value = None
            mock_check_service.return_value = True
            mock_get_via_service.return_value = mock_creds

            # ACT
            result = manager._get_interactive_credentials()

            # ASSERT
            assert result is mock_creds
            mock_check_service.assert_called_once()
            mock_get_via_service.assert_called_once()

    def test_get_interactive_credentials_no_creds_no_service_raises_error(self) -> None:
        """Test interactive credentials raises error when no credentials and service unavailable."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_check_service_availability") as mock_check_service,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_auth_env.return_value = None
            mock_check_service.return_value = False

            # ACT & ASSERT
            with pytest.raises(
                RuntimeError,
                match=r"FastAPI server is not running and TASKS_CLIENT_ID or",
            ):
                manager._get_interactive_credentials()

    def test_get_interactive_credentials_invalid_refresh_token_raises_error(self) -> None:
        """Test interactive credentials raises error when refresh token invalid and service unavailable."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                    "TASKS_REFRESH_TOKEN": "invalid_token",
                },
            ),
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_check_service_availability") as mock_check_service,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_auth_env.return_value = None
            mock_check_service.return_value = False

            # ACT & ASSERT
            with pytest.raises(
                RuntimeError,
                match=r"Refresh token in .env file is invalid or expired",
            ):
                manager._get_interactive_credentials()

    def test_get_interactive_credentials_login_flow_fails_raises_error(self) -> None:
        """Test interactive credentials raises error when login flow fails."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_check_service_availability") as mock_check_service,
            patch.object(manager, "_get_credentials_via_service") as mock_get_via_service,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_auth_env.return_value = None
            mock_check_service.return_value = True
            mock_get_via_service.side_effect = RuntimeError(
                "Failed to obtain credentials through login flow. "
                f"Please authenticate via {manager.SERVICE_BASE_URL}/auth/login"
            )

            # ACT & ASSERT
            with pytest.raises(
                RuntimeError,
                match=r"Failed to obtain credentials through login flow",
            ):
                manager._get_interactive_credentials()

    def test_get_interactive_credentials_in_fastapi_context_no_env(self) -> None:
        """Test interactive credentials in FastAPI context does not use env credentials."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                    "TASKS_REFRESH_TOKEN": "test_refresh_token",
                    "TASKS_ALLOW_ENV_IN_SERVICE": "",  # Clear the flag to disable env fallback
                },
            ),
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_check_service_availability") as mock_check_service,
            patch.object(manager, "_get_credentials_via_service") as mock_get_via_service,
        ):
            mock_is_fastapi.return_value = True  # In FastAPI context
            mock_check_service.return_value = True
            mock_get_via_service.return_value = mock_creds

            # ACT
            result = manager._get_interactive_credentials()

            # ASSERT
            assert result is mock_creds
            # Should NOT call _auth_from_env when in FastAPI context
            mock_auth_env.assert_not_called()
            mock_check_service.assert_called_once()
            mock_get_via_service.assert_called_once()


class TestAuthFromEnv:
    """Test cases for authentication from environment variables."""

    def test_auth_from_env_success(self) -> None:
        """Test successful authentication from environment variables."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                    "TASKS_REFRESH_TOKEN": "test_refresh_token",
                },
            ),
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_creds_class.return_value = mock_creds

            # ACT
            result = manager._auth_from_env(interactive=False)

            # ASSERT
            assert result is mock_creds
            mock_creds.refresh.assert_called_once()

    def test_auth_from_env_custom_token_uri(self) -> None:
        """Test authentication with custom token URI."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                    "TASKS_REFRESH_TOKEN": "test_refresh_token",
                    "TASKS_TOKEN_URI": "https://custom.oauth.com/token",
                },
            ),
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_creds_class.return_value = mock_creds

            # ACT
            result = manager._auth_from_env(interactive=False)

            # ASSERT
            assert result is mock_creds
            mock_creds_class.assert_called_once_with(
                None,
                refresh_token="test_refresh_token",
                token_uri="https://custom.oauth.com/token",
                client_id="test_client_id",
                client_secret="test_client_secret",
                scopes=OAuthManager.SCOPES,
            )

    def test_auth_from_env_refresh_failure(self) -> None:
        """Test authentication when refresh fails."""
        # ARRANGE
        manager = OAuthManager()

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                    "TASKS_REFRESH_TOKEN": "invalid_token",
                },
            ),
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.refresh.side_effect = RefreshError
            mock_creds_class.return_value = mock_creds

            # ACT
            result = manager._auth_from_env(interactive=False)

            # ASSERT
            assert result is None

    def test_auth_from_env_no_refresh_token_non_interactive(self) -> None:
        """Test authentication when no refresh token in non-interactive mode."""
        # ARRANGE
        manager = OAuthManager()

        with patch.dict(
            os.environ,
            {
                "TASKS_CLIENT_ID": "test_client_id",
                "TASKS_CLIENT_SECRET": "test_client_secret",
            },
        ):
            # ACT
            result = manager._auth_from_env(interactive=False)

            # ASSERT
            assert result is None

    def test_auth_from_env_no_refresh_token_interactive(self) -> None:
        """Test authentication when no refresh token in interactive mode."""
        # ARRANGE
        manager = OAuthManager()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_creds.refresh_token = "new_refresh_token"

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                },
            ),
            patch.object(manager, "_run_interactive_flow_for_refresh_token") as mock_interactive,
        ):
            mock_interactive.return_value = mock_creds

            # ACT
            result = manager._auth_from_env(interactive=True)

            # ASSERT
            assert result is mock_creds
            mock_interactive.assert_called_once_with("test_client_id", "test_client_secret")

    def test_auth_from_env_invalid_refresh_token_interactive(self) -> None:
        """Test authentication when refresh token invalid in interactive mode."""
        # ARRANGE
        manager = OAuthManager()
        new_creds = Mock(spec=Credentials)
        new_creds.valid = True

        with (
            patch.dict(
                os.environ,
                {
                    "TASKS_CLIENT_ID": "test_client_id",
                    "TASKS_CLIENT_SECRET": "test_client_secret",
                    "TASKS_REFRESH_TOKEN": "invalid_token",
                },
            ),
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
            patch.object(manager, "_run_interactive_flow_for_refresh_token") as mock_interactive,
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.refresh.side_effect = RefreshError
            mock_creds_class.return_value = mock_creds
            mock_interactive.return_value = new_creds

            # ACT
            result = manager._auth_from_env(interactive=True)

            # ASSERT
            assert result is new_creds
            mock_interactive.assert_called_once_with("test_client_id", "test_client_secret")


class TestSessionCredentials:
    """Test cases for session credentials (FastAPI context)."""

    def test_get_session_credentials_success(self) -> None:
        """Test successful retrieval of credentials from FastAPI context."""
        # ARRANGE
        manager = OAuthManager()

        # Create a mock FastAPI app and request
        app = FastAPI()
        mock_request = Mock(spec=Request)
        mock_app_state = Mock()
        mock_app_state.current_session_creds = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": OAuthManager.SCOPES,
        }
        mock_request.app = app
        app.state = mock_app_state

        # Mock the dependencies module
        mock_deps_module = Mock()
        mock_deps_module.current_request = ContextVar("current_request", default=None)
        mock_deps_module.current_request.set(mock_request)

        with (
            patch("gtask_client_impl.auth.importlib.util.find_spec") as mock_find_spec,
            patch("gtask_client_impl.auth.importlib.import_module") as mock_import_module,
            patch.object(manager, "_create_credentials_from_dict") as mock_create_creds,
        ):
            mock_find_spec.return_value = Mock()
            mock_import_module.return_value = mock_deps_module
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_create_creds.return_value = mock_creds

            # ACT
            result = manager._get_session_credentials()

            # ASSERT
            assert result is mock_creds

    def test_get_session_credentials_module_not_available(self) -> None:
        """Test _get_session_credentials when dependencies module is not available."""
        # ARRANGE
        manager = OAuthManager()

        with patch("gtask_client_impl.auth.importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = None

            # ACT
            result = manager._get_session_credentials()

            # ASSERT
            assert result is None

    def test_get_session_credentials_no_request_context(self) -> None:
        """Test _get_session_credentials when no request context available."""
        # ARRANGE
        manager = OAuthManager()

        mock_deps_module = Mock()
        mock_deps_module.current_request = ContextVar("current_request", default=None)
        # Don't set a value, so get() will raise RuntimeError

        with (
            patch("gtask_client_impl.auth.importlib.util.find_spec") as mock_find_spec,
            patch("gtask_client_impl.auth.importlib.import_module") as mock_import_module,
        ):
            mock_find_spec.return_value = Mock()
            mock_import_module.return_value = mock_deps_module

            # ACT
            result = manager._get_session_credentials()

            # ASSERT
            assert result is None

    def test_get_session_credentials_no_creds_in_state(self) -> None:
        """Test _get_session_credentials when no credentials in app state."""
        # ARRANGE
        manager = OAuthManager()

        app = FastAPI()
        mock_request = Mock(spec=Request)
        mock_app_state = Mock()
        mock_app_state.current_session_creds = None
        mock_request.app = app
        app.state = mock_app_state
        # Mock session to return None (no credentials in session either)
        mock_request.session = Mock()
        mock_request.session.get.return_value = None

        mock_deps_module = Mock()
        mock_deps_module.current_request = ContextVar("current_request", default=None)
        mock_deps_module.current_request.set(mock_request)

        with (
            patch("gtask_client_impl.auth.importlib.util.find_spec") as mock_find_spec,
            patch("gtask_client_impl.auth.importlib.import_module") as mock_import_module,
        ):
            mock_find_spec.return_value = Mock()
            mock_import_module.return_value = mock_deps_module

            # ACT
            result = manager._get_session_credentials()

            # ASSERT
            assert result is None


class TestInitiateApiLoginFlow:
    """Test cases for API login flow initiation."""

    def test_initiate_api_login_flow_service_not_available(self) -> None:
        """Test _initiate_api_login_flow when service is not available."""
        # ARRANGE
        manager = OAuthManager()

        with patch("gtask_client_impl.auth.requests") as mock_requests:
            mock_requests.get.side_effect = RequestException("Service not available")

            # ACT
            result = manager._initiate_api_login_flow()

            # ASSERT
            assert result is None

    def test_initiate_api_login_flow_already_has_creds(self) -> None:
        """Test _initiate_api_login_flow when credentials already exist."""
        # ARRANGE
        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.return_value = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": OAuthManager.SCOPES,
        }

        with (
            patch("gtask_client_impl.auth.requests") as mock_requests,
            patch.object(manager, "_create_credentials_from_dict") as mock_create_creds,
        ):
            mock_requests.get.return_value = mock_response
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_create_creds.return_value = mock_creds

            # ACT
            result = manager._initiate_api_login_flow()

            # ASSERT
            assert result is mock_creds

    def test_initiate_api_login_flow_opens_browser_and_polls(self) -> None:
        """Test _initiate_api_login_flow opens browser and polls for credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = HTTPStatus.UNAUTHORIZED

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        with (
            patch("gtask_client_impl.auth.requests") as mock_requests,
            patch("gtask_client_impl.auth.webbrowser") as mock_webbrowser,
            patch("gtask_client_impl.auth.time") as mock_time,
            patch.object(manager, "_get_session_credentials") as mock_get_session,
        ):
            mock_requests.get.return_value = mock_response
            mock_get_session.side_effect = [None, None, mock_creds]
            mock_time.time.side_effect = [0, 1, 2, 3]
            mock_time.sleep = Mock()

            # ACT
            result = manager._initiate_api_login_flow()

            # ASSERT
            assert result is mock_creds
            mock_webbrowser.open.assert_called_once()
            min_session_calls = 2
            assert mock_get_session.call_count >= min_session_calls

    def test_initiate_api_login_flow_timeout(self) -> None:
        """Test _initiate_api_login_flow times out waiting for credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = HTTPStatus.UNAUTHORIZED

        with (
            patch("gtask_client_impl.auth.requests") as mock_requests,
            patch("gtask_client_impl.auth.webbrowser"),
            patch("gtask_client_impl.auth.time") as mock_time,
            patch.object(manager, "_get_session_credentials") as mock_get_session,
        ):
            mock_requests.get.return_value = mock_response
            mock_get_session.return_value = None
            mock_time.time.side_effect = [0, 301]  # Exceeds max_wait_time
            mock_time.sleep = Mock()

            # ACT
            result = manager._initiate_api_login_flow()

            # ASSERT
            assert result is None


class TestCreateCredentialsFromDict:
    """Test cases for creating credentials from dictionary."""

    def test_create_credentials_from_dict_success(self) -> None:
        """Test successful creation of credentials from dictionary."""
        # ARRANGE
        manager = OAuthManager()

        creds_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": OAuthManager.SCOPES,
        }

        with (
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_creds.refresh_token = "test_refresh_token"
            mock_creds_class.return_value = mock_creds

            # ACT
            result = manager._create_credentials_from_dict(creds_data)

            # ASSERT
            assert result is mock_creds
            mock_creds_class.assert_called_once_with(
                token="test_token",
                refresh_token="test_refresh_token",
                token_uri="https://oauth2.googleapis.com/token",
                client_id="test_client_id",
                client_secret="test_client_secret",
                scopes=OAuthManager.SCOPES,
            )

    def test_create_credentials_from_dict_needs_refresh(self) -> None:
        """Test creation of credentials that need refresh."""
        # ARRANGE
        manager = OAuthManager()

        creds_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": OAuthManager.SCOPES,
        }

        with (
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.refresh_token = "test_refresh_token"

            def refresh_effect(request: Any) -> None:
                mock_creds.valid = True

            mock_creds.refresh.side_effect = refresh_effect
            mock_creds_class.return_value = mock_creds

            # ACT
            result = manager._create_credentials_from_dict(creds_data)

            # ASSERT
            assert result is mock_creds
            mock_creds.refresh.assert_called_once()

    def test_create_credentials_from_dict_refresh_failure(self) -> None:
        """Test creation of credentials where refresh fails."""
        # ARRANGE
        manager = OAuthManager()

        creds_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": OAuthManager.SCOPES,
        }

        with (
            patch("gtask_client_impl.auth.Credentials") as mock_creds_class,
            patch("gtask_client_impl.auth.Request"),
        ):
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.refresh_token = "test_refresh_token"
            mock_creds.refresh.side_effect = RefreshError
            mock_creds_class.return_value = mock_creds

            # ACT
            result = manager._create_credentials_from_dict(creds_data)

            # ASSERT
            assert result is None


class TestRefreshCredentials:
    """Test cases for credential refresh."""

    def test_refresh_credentials_if_needed_valid_creds(self) -> None:
        """Test refresh when credentials are already valid."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        # ACT
        result = manager._refresh_credentials_if_needed(mock_creds)

        # ASSERT
        assert result is mock_creds
        mock_creds.refresh.assert_not_called()

    def test_refresh_credentials_if_needed_no_refresh_token(self) -> None:
        """Test refresh when credentials have no refresh token."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.refresh_token = None

        # ACT
        result = manager._refresh_credentials_if_needed(mock_creds)

        # ASSERT
        assert result is mock_creds
        mock_creds.refresh.assert_not_called()

    def test_refresh_credentials_if_needed_refresh_success(self) -> None:
        """Test successful refresh of credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.refresh_token = "test_token"

        with patch("gtask_client_impl.auth.Request"):
            # ACT
            result = manager._refresh_credentials_if_needed(mock_creds)

            # ASSERT
            assert result is mock_creds
            mock_creds.refresh.assert_called_once()

    def test_refresh_credentials_if_needed_refresh_failure(self) -> None:
        """Test refresh failure falls back to session credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.refresh_token = "test_token"
        mock_creds.refresh.side_effect = RefreshError

        session_creds = Mock(spec=Credentials)
        session_creds.valid = True

        with (
            patch("gtask_client_impl.auth.Request"),
            patch.object(manager, "_get_session_credentials") as mock_session,
        ):
            mock_session.return_value = session_creds

            # ACT
            result = manager._refresh_credentials_if_needed(mock_creds)

            # ASSERT
            assert result is session_creds
            mock_session.assert_called_once()

    def test_refresh_credentials_if_needed_refresh_failure_no_session(self) -> None:
        """Test refresh failure raises error when no session credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.refresh_token = "test_token"
        mock_creds.refresh.side_effect = RefreshError

        with (
            patch("gtask_client_impl.auth.Request"),
            patch.object(manager, "_get_session_credentials") as mock_session,
        ):
            mock_session.return_value = None

            # ACT & ASSERT
            with pytest.raises(
                RuntimeError,
                match=r"Failed to refresh credentials and no valid session credentials found\.",
            ):
                manager._refresh_credentials_if_needed(mock_creds)


class TestServiceAvailability:
    """Test cases for service availability checks."""

    def test_check_service_availability_success(self) -> None:
        """Test service availability check when service is available."""
        # ARRANGE
        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = HTTPStatus.OK

        with patch("gtask_client_impl.auth.requests") as mock_requests:
            mock_requests.get.return_value = mock_response

            # ACT
            result = manager._check_service_availability()

            # ASSERT
            assert result is True
            mock_requests.get.assert_called_once_with(
                f"{manager.SERVICE_BASE_URL}/auth/_give_session_creds",
                timeout=2,
            )

    def test_check_service_availability_unauthorized(self) -> None:
        """Test service availability check when service returns 401 (still available)."""
        # ARRANGE
        manager = OAuthManager()

        mock_response = Mock()
        mock_response.status_code = HTTPStatus.UNAUTHORIZED

        with patch("gtask_client_impl.auth.requests") as mock_requests:
            mock_requests.get.return_value = mock_response

            # ACT
            result = manager._check_service_availability()

            # ASSERT
            assert result is True

    def test_check_service_availability_connection_error(self) -> None:
        """Test service availability check when service is not available."""
        # ARRANGE
        manager = OAuthManager()

        with patch("gtask_client_impl.auth.requests") as mock_requests:
            mock_requests.get.side_effect = RequestException("Connection failed")

            # ACT
            result = manager._check_service_availability()

            # ASSERT
            assert result is False


class TestEnsureServiceInitialized:
    """Test cases for ensuring service is initialized."""

    def test_ensure_service_initialized_with_session_creds(self) -> None:
        """Test ensure_service_initialized initializes service with session credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        mock_service = Mock()

        def build_service(creds: Any) -> Any:
            assert creds is mock_creds
            return mock_service

        with patch.object(manager, "_get_session_credentials") as mock_session:
            mock_session.return_value = mock_creds

            # ACT
            result = manager.ensure_service_initialized(None, build_service)

            # ASSERT
            assert result is mock_service
            mock_session.assert_called_once()

    def test_ensure_service_initialized_with_env_creds(self) -> None:
        """Test ensure_service_initialized initializes service with env credentials."""
        # ARRANGE
        manager = OAuthManager()

        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True

        mock_service = Mock()

        def build_service(creds: Any) -> Any:
            assert creds is mock_creds
            return mock_service

        with (
            patch.object(manager, "_is_in_fastapi_context") as mock_is_fastapi,
            patch.object(manager, "_get_session_credentials") as mock_session,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
        ):
            mock_is_fastapi.return_value = False  # Not in FastAPI context
            mock_session.return_value = None
            mock_auth_env.return_value = mock_creds

            # ACT
            result = manager.ensure_service_initialized(None, build_service)

            # ASSERT
            assert result is mock_service
            mock_auth_env.assert_called_once_with(interactive=False)

    def test_ensure_service_initialized_no_creds_raises_error(self) -> None:
        """Test ensure_service_initialized raises error when no credentials available."""
        # ARRANGE
        manager = OAuthManager()

        def build_service(creds: Any) -> Any:
            return Mock()

        with (
            patch.object(manager, "_get_session_credentials") as mock_session,
            patch.object(manager, "_auth_from_env") as mock_auth_env,
            patch.object(manager, "_initiate_api_login_flow") as mock_login_flow,
        ):
            mock_session.return_value = None
            mock_auth_env.return_value = None
            mock_login_flow.return_value = None

            # ACT & ASSERT
            with pytest.raises(
                RuntimeError,
                match=r"No valid credentials available",
            ):
                manager.ensure_service_initialized(None, build_service)

    def test_ensure_service_initialized_already_initialized(self) -> None:
        """Test ensure_service_initialized returns existing service if already initialized."""
        # ARRANGE
        manager = OAuthManager()

        existing_service = Mock()

        def build_service(creds: Any) -> Any:
            return Mock()

        # ACT
        result = manager.ensure_service_initialized(existing_service, build_service)

        # ASSERT
        assert result is existing_service


class TestOAuthManagerWithFastAPIService:
    """Test cases for OAuthManager integration with FastAPI service using TestClient."""

    def test_get_session_credentials_via_test_client(self) -> None:
        """Test getting session credentials via FastAPI TestClient."""
        # ARRANGE
        from task_client_service import app

        manager = OAuthManager()
        creds_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": OAuthManager.SCOPES,
        }

        # Set credentials in app state
        app.state.current_session_creds = creds_data

        with (
            TestClient(app),
            patch("gtask_client_impl.auth.importlib.util.find_spec") as mock_find_spec,
            patch("gtask_client_impl.auth.importlib.import_module") as mock_import_module,
            patch.object(manager, "_create_credentials_from_dict") as mock_create_creds,
        ):
            # Mock the dependencies module to return the request from TestClient
            mock_deps_module = Mock()
            mock_deps_module.current_request = ContextVar("current_request", default=None)

            # Create a mock request that mimics TestClient's request
            mock_request = Mock(spec=Request)
            mock_request.app = app

            # Set the request in the context
            mock_deps_module.current_request.set(mock_request)

            mock_find_spec.return_value = Mock()
            mock_import_module.return_value = mock_deps_module

            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_create_creds.return_value = mock_creds

            # ACT
            result = manager._get_session_credentials()

            # ASSERT
            assert result is mock_creds

    def test_check_service_availability_via_test_client(self) -> None:
        """Test service availability check using FastAPI TestClient."""
        # ARRANGE
        from task_client_service import app

        manager = OAuthManager()

        with (
            TestClient(app) as test_client,
            patch("gtask_client_impl.auth.requests") as mock_requests,
        ):
            # Update SERVICE_BASE_URL to match TestClient's base URL
            original_base_url = manager.SERVICE_BASE_URL
            # TestClient base_url is like "http://testserver"
            manager.SERVICE_BASE_URL = str(test_client.base_url)

            try:
                # Mock the requests.get call to return a successful response
                # (TestClient doesn't actually start a server, so we need to mock requests)
                mock_response = Mock()
                mock_response.status_code = (
                    HTTPStatus.UNAUTHORIZED
                )  # Even 401 means service is available
                mock_requests.get.return_value = mock_response

                # ACT
                result = manager._check_service_availability()

                # ASSERT
                assert result is True
            finally:
                # Restore original base URL
                manager.SERVICE_BASE_URL = original_base_url

    def test_initiate_api_login_flow_via_test_client(self) -> None:
        """Test API login flow using FastAPI TestClient."""
        # ARRANGE
        from task_client_service import app

        manager = OAuthManager()

        with (
            TestClient(app) as test_client,
            patch("gtask_client_impl.auth.webbrowser") as mock_webbrowser,
            patch("gtask_client_impl.auth.time") as mock_time,
            patch("gtask_client_impl.auth.requests") as mock_requests,
            patch.object(manager, "_get_session_credentials") as mock_get_session,
        ):
            # Update SERVICE_BASE_URL to match TestClient's base URL
            original_base_url = manager.SERVICE_BASE_URL
            manager.SERVICE_BASE_URL = str(test_client.base_url)

            try:
                # Mock the initial service availability check (returns 401 - no credentials)
                mock_response = Mock()
                mock_response.status_code = HTTPStatus.UNAUTHORIZED
                mock_requests.get.return_value = mock_response

                # Set credentials in app state after a delay
                mock_creds = Mock(spec=Credentials)
                mock_creds.valid = True
                mock_get_session.side_effect = [None, None, mock_creds]
                mock_time.time.side_effect = [0, 1, 2, 3]
                mock_time.sleep = Mock()

                # ACT
                result = manager._initiate_api_login_flow()

                # ASSERT
                assert result is mock_creds
                mock_webbrowser.open.assert_called_once()
            finally:
                # Restore original base URL
                manager.SERVICE_BASE_URL = original_base_url


class TestOAuthManagerConstants:
    """Test cases for OAuthManager constants and class attributes."""

    def test_scopes_constant(self) -> None:
        """Test that SCOPES constant is correctly defined."""
        expected_scopes = [
            "https://www.googleapis.com/auth/tasks",
        ]
        assert expected_scopes == OAuthManager.SCOPES

    def test_service_base_url_constant(self) -> None:
        """Test that SERVICE_BASE_URL constant is defined."""
        assert OAuthManager.SERVICE_BASE_URL is not None
        assert isinstance(OAuthManager.SERVICE_BASE_URL, str)
        assert len(OAuthManager.SERVICE_BASE_URL) > 0


class TestGTaskClientConstants:
    """Test cases for GTaskClient constants and class attributes."""

    def test_failure_message_constant(self) -> None:
        """Test that failure message constant is defined."""
        assert (
            GTaskClient.FAILURE_TO_CRED == "Failed to obtain credentials. Please check your setup."
        )
        assert isinstance(GTaskClient.FAILURE_TO_CRED, str)
        assert len(GTaskClient.FAILURE_TO_CRED) > 0
