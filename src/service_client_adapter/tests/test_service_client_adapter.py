"""Tests for ServiceClientAdapter in main.py.

These tests monkeypatch the generated API functions so no real HTTP requests are made.
"""

from http import HTTPStatus
from typing import Any
from unittest.mock import Mock

import pytest
from mail_client_api.message import Message
from mail_client_service_api_client.client import Client
from mail_client_service_api_client.types import Response

test_message = {
    "id": "1",
    "from_": "test@1.com",
    "to": "test@2.com",
    "date": "2020-1-1",
    "subject": "TEST",
    "body": "This is a test",
}
test_message_other = {
    "id": "2",
    "from_": "test@2.com",
    "to": "test@1.com",
    "date": "2020-1-2",
    "subject": "TEST",
    "body": "This is another test",
}
test_messages = [test_message, test_message_other]


def test_get_messages_respects_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests get message request max results."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=test_messages,
    )

    # Monkeypatch the imported get_messages
    monkeypatch.setattr(main_mod, "get_messages", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    results = adapter.get_messages(max_results=2)
    test_length = 2
    # verify adapter forwarded client and max_results
    mock_api.sync_detailed.assert_called_once_with(client=adapter.Client, max_results=2)
    # result should be a list of domain Message objects
    assert isinstance(results, list)
    assert len(results) == test_length
    assert isinstance(results[0], Message)
    assert isinstance(results[1], Message)
    assert results[0].id == "1"
    assert results[1].id == "2"


def test_get_message_calls_api_and_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests get message api."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={"message": test_message, "status": "success"},
    )

    monkeypatch.setattr(main_mod, "get_message", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    result = adapter.get_message("1")

    # Ensure adapter forwarded message_id and client
    mock_api.sync_detailed.assert_called_once_with(message_id="1", client=adapter.Client)

    # Ensure returned object is the domain Message and values match
    assert isinstance(result, Message)
    assert result.body == test_message["body"]
    assert result.id == test_message["id"]
    assert result.subject == test_message["subject"]


def test_delete_and_mark_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests delete message, marking messages as read and login."""
    import service_client_adapter.main as main_mod

    # Use mocks so we can assert calls and their arguments
    mock_login = Mock()
    mock_login.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={"message": "Login Successful", "status": "success"},
    )

    mock_delete = Mock()
    mock_delete.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={"message": "Message 199f90d8d23a606d marked as read.", "status": "success"},
    )

    mock_mark = Mock()
    mock_mark.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={
            "detail": {
                "error": "Message not found",
                "message": "No message found with ID: .",
                "status": "error",
            },
        },
    )

    monkeypatch.setattr(main_mod, "login", mock_login)
    monkeypatch.setattr(main_mod, "delete_message", mock_delete)
    monkeypatch.setattr(main_mod, "mark_message_as_read", mock_mark)

    adapter = main_mod.ServiceClientAdapter()

    # assert login to succeed and client forwarded
    assert adapter.login() == HTTPStatus.OK
    mock_login.sync_detailed.assert_called_once_with(client=adapter.Client)

    # delete_message returns True and was called once with expected args
    assert adapter.delete_message("x") is True
    mock_delete.sync_detailed.assert_called_once_with(message_id="x", client=adapter.Client)

    # mark_as_read returns False and was called once with expected args
    assert adapter.mark_as_read("x") is False
    mock_mark.sync_detailed.assert_called_once_with(message_id="x", client=adapter.Client)


def test_init_sets_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """ServiceClientAdapter should construct a Client with the expected base_url."""
    import service_client_adapter.main as main_mod

    # Use a Mock to assert the Client constructor is called with expected base_url
    mock_client = Mock()
    monkeypatch.setattr(main_mod, "Client", mock_client)

    adapter = main_mod.ServiceClientAdapter()

    # Ensure the Client constructor was called with the expected base_url
    mock_client.assert_called_once_with(base_url="http://127.0.0.1:8000")
    # And the adapter stored the returned client instance
    assert adapter.Client is mock_client.return_value


def test_get_message_calls_api_with_correct_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure get_message passes message_id and client to the underlying API."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={"message": test_message, "status": "success"},
    )

    monkeypatch.setattr(main_mod, "get_message", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    adapter.get_message("1")

    mock_api.sync_detailed.assert_called_once_with(message_id="1", client=adapter.Client)


def test_get_messages_uses_default_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure get_messages calls API with default max_results=10 when none provided."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=test_messages,
    )

    monkeypatch.setattr(main_mod, "get_messages", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    adapter.get_messages()

    mock_api.sync_detailed.assert_called_once_with(client=adapter.Client, max_results=10)


def test_get_messages_empty_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """If API returns an empty list, adapter.get_messages should return an empty list."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=[],
    )

    monkeypatch.setattr(main_mod, "get_messages", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    results = adapter.get_messages(max_results=5)
    assert isinstance(results, list)
    assert len(results) == 0


def test_mark_as_read_success_returns_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """When API returns a 'message' key, mark_as_read should return True."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={"message": "ok", "status": "success"},
    )

    monkeypatch.setattr(main_mod, "mark_message_as_read", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    assert adapter.mark_as_read("1") is True


def test_delete_message_parsed_but_error_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """If API parsed contains an error payload (no 'message'), delete_message should return False."""
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed={"detail": {"status": "error"}},
    )

    monkeypatch.setattr(main_mod, "delete_message", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    assert adapter.delete_message("1") is False


def test_get_message_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returned message object should expose expected fields (id, subject, body)."""
    import service_client_adapter.main as main_mod

    class FakeGetMessage:
        @staticmethod
        def sync_detailed(message_id: str, client: Client) -> Response[Any]:
            _ = message_id, client
            return Response(
                status_code=HTTPStatus.OK,
                content=b"{}",
                headers={},
                parsed={"message": test_message, "status": "success"},
            )

    monkeypatch.setattr(main_mod, "get_message", FakeGetMessage)

    adapter = main_mod.ServiceClientAdapter()
    msg = adapter.get_message("1")
    # check returned type and common fields
    assert isinstance(msg, Message)
    assert msg.id == test_message["id"]
    assert msg.body == test_message["body"]
    assert msg.subject == test_message["subject"]


def test_get_message_raises_on_malformed_parsed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the API returns a message payload missing required fields, the adapter should raise.

    Also ensure the underlying API was called once with the adapter's client.
    """
    import service_client_adapter.main as main_mod

    mock_api = Mock()
    # parsed contains a 'message' dict but missing required fields (e.g., 'body')
    malformed = {"message": {"id": "1", "subject": "missing body"}, "status": "success"}
    mock_api.sync_detailed.return_value = Response(
        status_code=HTTPStatus.OK,
        content=b"{}",
        headers={},
        parsed=malformed,
    )

    monkeypatch.setattr(main_mod, "get_message", mock_api)

    adapter = main_mod.ServiceClientAdapter()
    with pytest.raises(TypeError, match="missing"):
        adapter.get_message("1")

    mock_api.sync_detailed.assert_called_once_with(message_id="1", client=adapter.Client)
