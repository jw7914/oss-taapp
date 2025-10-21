"""Negative/error-path tests for ServiceClientAdapter.

These tests ensure the adapter raises ValueError when the underlying API
returns validation errors or None in the parsed response.
"""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
from mail_client_service_api_client.models.http_validation_error import HTTPValidationError
from mail_client_service_api_client.types import Response


def test_get_message_raises_on_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_message should raise ValueError when API returns an HTTPValidationError."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=HTTPValidationError(),
    )

    monkeypatch.setattr(main_mod, "get_message", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    with pytest.raises(ValueError, match="Validation error"):
        adapter.get_message("1")

    mock_api.sync_detailed.assert_called_once_with(message_id="1", client=adapter.Client)


def test_delete_message_raises_on_none_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_message should raise ValueError when API parsed is None."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=None,
    )

    monkeypatch.setattr(main_mod, "delete_message", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    with pytest.raises(ValueError, match="Validation error"):
        adapter.delete_message("x")

    mock_api.sync_detailed.assert_called_once_with(message_id="x", client=adapter.Client)


def test_mark_as_read_raises_on_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """mark_as_read should raise ValueError when API returns an HTTPValidationError."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=HTTPValidationError(),
    )

    monkeypatch.setattr(main_mod, "mark_message_as_read", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    with pytest.raises(ValueError, match="Validation error"):
        adapter.mark_as_read("x")

    mock_api.sync_detailed.assert_called_once_with(message_id="x", client=adapter.Client)


def test_get_messages_raises_on_none_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_messages should raise ValueError when API parsed is None."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=None,
    )

    monkeypatch.setattr(main_mod, "get_messages", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    with pytest.raises(ValueError, match="Validation error"):
        adapter.get_messages(max_results=5)

    mock_api.sync_detailed.assert_called_once_with(client=adapter.Client, max_results=5)
