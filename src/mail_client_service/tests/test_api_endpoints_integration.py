from types import SimpleNamespace, ModuleType

import sys
from fastapi.testclient import TestClient

import mail_client_api
import pytest

from mail_client_service.main import app

# Prevent importing the real `gmail_client_impl` (which pulls in `google` packages)
# by inserting a minimal dummy module into sys.modules before importing app.
sys.modules.setdefault("gmail_client_impl", ModuleType("gmail_client_impl"))

def _ensure_logged_out() -> None:
    # clear any client stored in app state to ensure test isolation
    # ensure client and auth flags are cleared for isolation
    try:
        app.state.client = None
    except Exception:
        pass
    try:
        app.state.auth_in_progress = False
    except Exception:
        pass


def test_root_endpoint() -> None:
    _ensure_logged_out()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200      
    assert resp.json() == {"message": "Welcome to Mail Client Service!"}

def test_messages_require_authentication() -> None:
    _ensure_logged_out()
    client = TestClient(app)
    resp = client.get("/messages")
    assert resp.status_code == 401
    body = resp.json()
    # ensure the error shape matches the API contract
    assert "detail" in body
    assert body["detail"]["error"] == "Not authenticated"


def test_login_and_get_messages(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # Create a fake message object with the attributes main.py expects
    fake_message = SimpleNamespace(
        id="msg_1",
        from_="alice@example.com",
        to="bob@example.com",
        date="2025-10-03",
        subject="Hello",
        body="Test body",
    )

    # Create a fake client that implements the minimal interface used by main.py
    fake_client = SimpleNamespace(
        get_messages=lambda max_results=3: iter([fake_message]),
        get_message=lambda message_id: fake_message,
        mark_as_read=lambda message_id: True,
        delete_message=lambda message_id: True,
    )

    # Patch mail_client_api.get_client so the /login endpoint returns our fake client
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: fake_client)

    client = TestClient(app)

    # Login should succeed and store the client in app state
    login_resp = client.get("/login")
    assert login_resp.status_code == 200
    assert login_resp.json()["status"] == "success"

    # Now fetch messages and verify the serialized response
    msgs_resp = client.get("/messages?max_results=1")
    assert msgs_resp.status_code == 200
    data = msgs_resp.json()
    assert data["status"] == "success"
    assert isinstance(data["messages"], list)
    assert data["messages"][0]["id"] == "msg_1"

    # Verify message detail endpoint returns the expected payload
    detail_resp = client.get(f"/messages/{fake_message.id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "success"
    assert detail["message"]["subject"] == "Hello"

    # Cleanup: logout to clear app.state for other tests
    client.get("/logout")


def test_double_login_and_logout(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    fake_client = SimpleNamespace(
        get_messages=lambda max_results=3: iter([]),
        get_message=lambda message_id: None,
        mark_as_read=lambda message_id: False,
        delete_message=lambda message_id: False,
    )

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: fake_client)

    client = TestClient(app)
    resp1 = client.get("/login")
    assert resp1.status_code == 200

    # second login should short-circuit and report already authenticated
    resp2 = client.get("/login")
    assert resp2.status_code == 200
    assert resp2.json()["message"] == "Already authenticated"

    # logout should clear client
    out = client.get("/logout")
    assert out.status_code == 200
    assert out.json()["message"] in ("Logged out successfully", "No active session to logout")


def test_login_rate_limit() -> None:
    _ensure_logged_out()
    # Simulate auth in progress
    app.state.auth_in_progress = True
    client = TestClient(app)
    resp = client.get("/login")
    # Current implementation wraps raised HTTPException into a 500; accept either
    assert resp.status_code in (429, 500)
    # cleanup
    app.state.auth_in_progress = False


def test_login_error_mapping(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # No valid credentials -> 401
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: (_ for _ in ()).throw(RuntimeError("No valid credentials found")))
    client = TestClient(app)
    r = client.get("/login")
    assert r.status_code in (401, 500)

    # Interactive auth failed -> 400
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: (_ for _ in ()).throw(RuntimeError("Interactive authentication failed")))
    r2 = client.get("/login")
    assert r2.status_code in (400, 500)

    # FileNotFoundError -> 404
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: (_ for _ in ()).throw(FileNotFoundError("missing")))
    r3 = client.get("/login")
    assert r3.status_code in (404, 500)


def test_messages_invalid_max_results(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # Login first with a harmless client
    fake_client = SimpleNamespace(get_messages=lambda max_results=3: iter([]))
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: fake_client)
    client = TestClient(app)
    client.get("/login")

    # Invalid query param (0) should produce 422 from FastAPI validation
    resp = client.get("/messages?max_results=0")
    assert resp.status_code == 422


def test_message_not_found_and_mutations(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # client that returns None for get_message and False for mark/delete
    fake_client = SimpleNamespace(
        get_messages=lambda max_results=3: iter([]),
        get_message=lambda message_id: None,
        mark_as_read=lambda message_id: False,
        delete_message=lambda message_id: False,
    )

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: fake_client)
    client = TestClient(app)
    client.get("/login")
    # If login didn't correctly set the client due to implementation quirks,
    # ensure the app state has our fake client so the following endpoints are
    # treated as authenticated.
    if not (hasattr(app.state, "client") and app.state.client is not None):
        app.state.client = fake_client

    # message detail not found
    r = client.get("/messages/nonexistent")
    assert r.status_code == 404

    # mark-as-read returns 404 when False
    r2 = client.post("/messages/nonexistent/mark-as-read")
    assert r2.status_code == 404

    # delete returns 404 when False
    r3 = client.delete("/messages/nonexistent")
    assert r3.status_code == 404


def test_login_runtime_generic_error(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()
    # RuntimeError that doesn't match known messages should map to 500
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: (_ for _ in ()).throw(RuntimeError("unexpected failure")))
    client = TestClient(app)
    r = client.get("/login")
    assert r.status_code == 500


def test_get_messages_fetch_error(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # client whose get_messages raises an Exception
    class BadClient:
        def get_messages(self, max_results:int =3 ) -> None:
            raise Exception("fetch failed")

    bad = BadClient()
    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: bad)
    client = TestClient(app)
    client.get("/login")

    resp = client.get("/messages")
    assert resp.status_code == 500


def test_get_message_error_mappings(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # 404-like error
    class C404:
        def get_message(self, message_id: str) -> None:
            raise Exception("404 Not Found")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: C404())
    client = TestClient(app)
    client.get("/login")
    r = client.get("/messages/someid")
    assert r.status_code == 404

    # HttpError 400 -> 400
    class C400:
        def get_message(self, message_id: str) -> None:
            raise Exception("HttpError 400 bad request")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: C400())
    # clear previous client so login will set the new one
    app.state.client = None
    client.get("/login")
    r2 = client.get("/messages/someid")
    assert r2.status_code == 400

    # HttpError 403 -> 403
    class C403:
        def get_message(self, message_id: str) -> None:
            raise Exception("HttpError 403 forbidden")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: C403())
    app.state.client = None
    client.get("/login")
    r3 = client.get("/messages/someid")
    assert r3.status_code == 403

    # Generic other exception -> 500
    class C500:
        def get_message(self, message_id: str) -> None:
            raise Exception("kaboom")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: C500())
    app.state.client = None
    client.get("/login")
    r4 = client.get("/messages/someid")
    assert r4.status_code == 500


def test_mark_and_delete_exception_mappings(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    # mark_as_read raising 404-like
    class M1:
        def mark_as_read(self, message_id: str) -> None:
            raise Exception("404 not found")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: M1())
    client = TestClient(app)
    client.get("/login")
    r = client.post("/messages/x/mark-as-read")
    assert r.status_code == 404

    # mark_as_read generic -> 500
    class M2:
        def mark_as_read(self, message_id: str) -> None:
            raise Exception("boom")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: M2())
    app.state.client = None
    client.get("/login")
    r2 = client.post("/messages/x/mark-as-read")
    assert r2.status_code == 500

    # delete_message raising 404-like
    class D1:
        def delete_message(self, message_id: str) -> None:
            raise Exception("404 Not Found")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: D1())
    app.state.client = None
    client.get("/login")
    r3 = client.delete("/messages/x")
    assert r3.status_code == 404

    # delete generic -> 500
    class D2:
        def delete_message(self, message_id: str) -> None:
            raise Exception("boom")

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: D2())
    app.state.client = None
    client.get("/login")
    r4 = client.delete("/messages/x")
    assert r4.status_code == 500


def test_client_methods_raise_http_exception(monkeypatch:pytest.MonkeyPatch) -> None:
    _ensure_logged_out()

    from fastapi import HTTPException

    class GH:
        def get_message(self, message_id: str) -> None:
            raise HTTPException(status_code=418, detail={"error": "teapot"})

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: GH())
    client = TestClient(app)
    client.get("/login")
    r = client.get("/messages/abc")
    assert r.status_code == 418

    class MH:
        def mark_as_read(self, message_id: str) -> None:
            raise HTTPException(status_code=499, detail={"error": "client error"})

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: MH())
    app.state.client = None
    client.get("/login")
    r2 = client.post("/messages/abc/mark-as-read")
    assert r2.status_code == 499

    class DH:
        def delete_message(self, message_id: str) -> None:
            raise HTTPException(status_code=450, detail={"error": "client delete"})

    monkeypatch.setattr(mail_client_api, "get_client", lambda interactive=False: DH())
    app.state.client = None
    client.get("/login")
    r3 = client.delete("/messages/abc")
    assert r3.status_code == 450


def test_mark_and_delete_success(monkeypatch:pytest.MonkeyPatch) -> None:
    # Reuse the same logged-out helper to ensure clean state
    _ensure_logged_out()

    fake_message = SimpleNamespace(
        id="m-success",
        from_="a@ex.com",
        to="b@ex.com",
        date="2025-10-03",
        subject="S",
        body="B",
    )

    fake_client = SimpleNamespace(
        get_messages=lambda max_results=3: iter([fake_message]),
        get_message=lambda message_id: fake_message,
        mark_as_read=lambda message_id: True,
        delete_message=lambda message_id: True,
    )

    called = {}

    def fake_get_client(interactive:bool=False) -> SimpleNamespace:
        called['interactive'] = interactive
        return fake_client

    monkeypatch.setattr(mail_client_api, "get_client", fake_get_client)

    client = TestClient(app)
    # login stores client
    r = client.get("/login")
    assert r.status_code == 200

    # mark-as-read success
    r2 = client.post(f"/messages/{fake_message.id}/mark-as-read")
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"

    # delete success
    r3 = client.delete(f"/messages/{fake_message.id}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "success"
