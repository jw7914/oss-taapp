from http import HTTPStatus
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from discord_service import main

# TestClient for FastAPI app
client = TestClient(main.app)


def make_msg(id: str = "m1", channel_id: str = "c1", author: str = "a", content: str = "hi", ts: str = "t") -> SimpleNamespace:
    return SimpleNamespace(
        message_id=id, id=id, channel_id=channel_id, author=author, author_username=author, content=content, timestamp=ts
    )


def make_channel(id: str = "c1", name: str = "chan", type_: int = 1, pos: int = 0) -> SimpleNamespace:
    return SimpleNamespace(channel_id=id, id=id, channel_name=name, name=name, channel_type=type_, channel_position=pos)


def test_root_returns_welcome() -> None:
    r = client.get("/")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["message"].startswith("Welcome")


def test_login_redirects_with_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    # stub DiscordClient.get_authorization_url
    monkeypatch.setattr(
        "discord_service.main.DiscordClient",
        lambda *args, **kwargs: SimpleNamespace(get_authorization_url=lambda scopes=None: "https://auth"),
    )
    r = client.get("/login?scopes=read%20write", follow_redirects=False)
    assert r.status_code == HTTPStatus.FOUND
    assert r.headers["Location"] == "https://auth"


def test_login_in_progress_returns_429() -> None:
    main.app.state.auth_in_progress = True
    r = client.get("/login")
    assert r.status_code == HTTPStatus.TOO_MANY_REQUESTS
    main.app.state.auth_in_progress = False


def test_auth_callback_missing_code_returns_400() -> None:
    r = client.get("/auth/callback")
    assert r.status_code == HTTPStatus.BAD_REQUEST


def test_logout_clears_client() -> None:
    main.app.state.client = SimpleNamespace()
    r = client.get("/logout")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["status"] == "success"
    # subsequent logout when no client
    main.app.state.client = None
    r2 = client.get("/logout")
    assert r2.status_code == HTTPStatus.OK


def test_get_current_user_success_and_error() -> None:
    main.app.state.client = SimpleNamespace(get_current_user=lambda: {"id": "u1"})
    r = client.get("/user")
    assert r.status_code == HTTPStatus.OK
    # error path
    main.app.state.client = SimpleNamespace(get_current_user=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    r2 = client.get("/user")
    assert r2.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_delete_message_various_responses() -> None:
    # no _http_client -> 501
    main.app.state.client = SimpleNamespace()
    r = client.delete("/channels/c1/messages/m1")
    assert r.status_code == HTTPStatus.NOT_IMPLEMENTED

    # successful delete (204)
    class FakeHTTP:
        def delete(self, path: str) -> SimpleNamespace:
            return SimpleNamespace(status_code=204, text="")

    main.app.state.client = SimpleNamespace(_http_client=FakeHTTP())
    r2 = client.delete("/channels/c1/messages/m1")
    assert r2.status_code == HTTPStatus.OK

    # forbidden
    class ForbiddenHTTP:
        def delete(self, path: str) -> SimpleNamespace:
            return SimpleNamespace(status_code=403, text="forbidden")

    main.app.state.client = SimpleNamespace(_http_client=ForbiddenHTTP())
    r3 = client.delete("/channels/c1/messages/m1")
    assert r3.status_code == HTTPStatus.FORBIDDEN

    # not found
    class NotFoundHTTP:
        def delete(self, path: str) -> SimpleNamespace:
            return SimpleNamespace(status_code=404, text="nf")

    main.app.state.client = SimpleNamespace(_http_client=NotFoundHTTP())
    r4 = client.delete("/channels/c1/messages/m1")
    assert r4.status_code == HTTPStatus.NOT_FOUND

    # other error -> 500
    class OtherHTTP:
        def delete(self, path: str) -> SimpleNamespace:
            return SimpleNamespace(status_code=500, text="err")

    main.app.state.client = SimpleNamespace(_http_client=OtherHTTP())
    r5 = client.delete("/channels/c1/messages/m1")
    assert r5.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_serialize_helpers_handle_alternate_attrs() -> None:
    m = SimpleNamespace(id="i1", channel_id="c1", author="a", author_username="au", content="x", timestamp="t")
    serialized = main.serialize_message(m)
    assert serialized["id"] == "i1"
    ch = SimpleNamespace(id="c2", name="n")
    serialized_ch = main.serialize_channel(ch)
    assert serialized_ch["id"] == "c2"
