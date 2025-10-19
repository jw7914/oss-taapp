"""Tests for ServiceClientAdapter in main.py.

These tests monkeypatch the generated API functions so no real HTTP requests are made.
"""

from http import HTTPStatus
from typing import Any

import pytest
from mail_client_service_api_client.client import Client
from mail_client_service_api_client.types import Response

test_message = {
    "id":"1",
    "from_":"test@1.com",
    "to":"test@2.com",
    "date":"2020-1-1",
    "subject":"TEST",
    "body":"This is a test",
}
test_message_other = {
   "id":"2",
    "from_":"test@2.com",
    "to":"test@1.com",
    "date":"2020-1-2",
    "subject":"TEST",
    "body":"This is another test",
}
test_messages = [test_message,test_message_other]

def test_get_messages_respects_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests get message request max results."""
    import service_client_adapter.main as main_mod

    class FakeGetMessages:
        @staticmethod
        def sync_detailed(client : Client, max_results:int) -> Response[Any]:
            _,_  = client, max_results
            return Response(
                status_code=HTTPStatus.OK,
                content=b"{}",
                headers={},
                parsed=test_messages,
            )

    # Monkeypatch the imported get_messages
    monkeypatch.setattr(main_mod, "get_messages", FakeGetMessages)

    adapter = main_mod.ServiceClientAdapter()
    results = adapter.get_messages(max_results=2)
    test_length = 2
    assert isinstance(results, list)
    assert len(results) == test_length
    assert results[0].id == "1"
    assert results[1].id == "2"


def test_get_message_calls_api_and_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests get message api."""
    import service_client_adapter.main as main_mod

    captured : dict[str,Any] = {}
    class FakeGetMessage:
        @staticmethod
        def sync_detailed(message_id : str, client: Client) -> Response[Any]:
            captured["message_id"] = message_id
            captured["client"] = client
            return Response(
                status_code=HTTPStatus.OK,
                content=b"{}",
                headers={},
                parsed={"message": test_message,
                        "status": "success"},
            )

    monkeypatch.setattr(main_mod, "get_message", FakeGetMessage)

    adapter = main_mod.ServiceClientAdapter()
    result = adapter.get_message("1")

    assert result.body == test_message["body"]
    assert captured["message_id"] == "1"
    assert captured["client"] is adapter.Client


def test_delete_and_mark_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests delete message, marking messages as read and login."""
    import service_client_adapter.main as main_mod

    class FakeDelete:
        @staticmethod
        def sync_detailed(message_id: str, client: Client) -> Response[Any]:
            _, _  = message_id, client
            return Response(
                status_code=HTTPStatus.OK,
                content=b"{}",
                headers={},
                parsed={"message": "Message 199f90d8d23a606d marked as read.",
                        "status": "success"},
            )
    class FakeMark:
        @staticmethod
        def sync_detailed(message_id: str, client: Client) -> Response[Any]:
            _, _  = message_id, client
            return Response(
                status_code=HTTPStatus.OK,
                content=b"{}",
                headers={},
                parsed={"detail": {
                    "error": "Message not found",
                    "message": "No message found with ID: .",
                    "status": "error",
                }},
            )


    monkeypatch.setattr(main_mod, "delete_message", FakeDelete)
    monkeypatch.setattr(main_mod, "mark_message_as_read", FakeMark)

    adapter = main_mod.ServiceClientAdapter()

    # delete_message returns True
    assert adapter.delete_message("x") is True
    # mark_as_read returns False
    assert adapter.mark_as_read("x") is False
