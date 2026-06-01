from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import final

import httpx
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import settings
from app.main import app
from app.routers.auth import identity_auth_url
from app.services import http_client


client = TestClient(app)

Handler = Callable[[str, str, bytes, dict[str, str], object], Awaitable[httpx.Response]]


@final
class FakeAsyncClient:
    def __init__(self, handler: Handler) -> None:
        self.handler: Handler = handler

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def request(
        self,
        method: str,
        url: str,
        content: bytes,
        headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        return await self.handler(method, url, content, headers, params)


def _patch_identity_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "identity_service_url", "http://identity-service:8000")


def _patch_async_client(monkeypatch: MonkeyPatch, handler: Handler) -> None:
    monkeypatch.setattr(http_client, "create_async_client", lambda: FakeAsyncClient(handler))


def test_login_proxy_forwards_body_and_returns_upstream_response(monkeypatch: MonkeyPatch) -> None:
    _patch_identity_url(monkeypatch)
    recorded_method = ""
    recorded_url = ""
    recorded_content = b""

    async def handler(
        method: str,
        url: str,
        content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_method, recorded_url, recorded_content
        recorded_method = method
        recorded_url = url
        recorded_content = content
        return httpx.Response(
            200,
            json={"access_token": "token", "token_type": "bearer"},
            headers={"x-upstream": "identity"},
        )

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@junia.com", "password": "secret123"},
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "token", "token_type": "bearer"}
    assert response.headers["x-upstream"] == "identity"
    assert recorded_method == "POST"
    assert recorded_url == "http://identity-service:8000/api/v1/auth/login"
    assert recorded_content == b'{"email":"alice@junia.com","password":"secret123"}'


def test_proxy_removes_client_controlled_forwarding_headers(monkeypatch: MonkeyPatch) -> None:
    _patch_identity_url(monkeypatch)
    recorded_headers: dict[str, str] = {}

    async def handler(
        _method: str,
        _url: str,
        _content: bytes,
        headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_headers
        recorded_headers = headers
        return httpx.Response(200, json={"ok": True})

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@junia.com", "password": "secret123"},
        headers={
            "Authorization": "Bearer access-token",
            "Connection": "keep-alive",
            "Host": "evil.example.test",
            "X-Forwarded-For": "203.0.113.10",
            "X-Forwarded-Host": "evil.example.test",
            "X-Forwarded-Proto": "https",
            "X-Real-IP": "203.0.113.10",
        },
    )

    assert response.status_code == 200
    assert recorded_headers["authorization"] == "Bearer access-token"
    assert "connection" not in recorded_headers
    assert "host" not in recorded_headers
    assert "content-length" not in recorded_headers
    assert "x-forwarded-for" not in recorded_headers
    assert "x-forwarded-host" not in recorded_headers
    assert "x-forwarded-proto" not in recorded_headers
    assert "x-real-ip" not in recorded_headers


def test_proxy_keeps_auth_response_headers(monkeypatch: MonkeyPatch) -> None:
    _patch_identity_url(monkeypatch)

    async def handler(
        _method: str,
        _url: str,
        _content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True},
            headers={
                "Set-Cookie": "refresh_token=abc; HttpOnly; Path=/",
                "Transfer-Encoding": "chunked",
                "X-Trace-Id": "identity-trace",
            },
        )

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.headers["set-cookie"] == "refresh_token=abc; HttpOnly; Path=/"
    assert response.headers["x-trace-id"] == "identity-trace"
    assert "transfer-encoding" not in response.headers


def test_me_proxy_forwards_authorization_header_and_query_params(monkeypatch: MonkeyPatch) -> None:
    _patch_identity_url(monkeypatch)
    recorded_method = ""
    recorded_url = ""
    recorded_content = b"uninitialized"
    recorded_headers: dict[str, str] = {}
    recorded_params: object = None

    async def handler(
        method: str,
        url: str,
        content: bytes,
        headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_method, recorded_url, recorded_content, recorded_headers, recorded_params
        recorded_method = method
        recorded_url = url
        recorded_content = content
        recorded_headers = headers
        recorded_params = params
        return httpx.Response(200, json={"email": "alice@junia.com"})

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/auth/me?include_roles=true",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert recorded_method == "GET"
    assert recorded_url == "http://identity-service:8000/api/v1/auth/me"
    assert recorded_content == b""
    assert recorded_headers["authorization"] == "Bearer access-token"
    assert str(recorded_params) == "include_roles=true"


def test_identity_auth_url_normalizes_slashes(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "identity_service_url", "http://identity-service:8000/")

    assert identity_auth_url("/login") == "http://identity-service:8000/api/v1/auth/login"


def test_proxy_preserves_upstream_status(monkeypatch: MonkeyPatch) -> None:
    _patch_identity_url(monkeypatch)

    async def handler(
        _method: str,
        _url: str,
        _content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Token is invalid or expired"})

    _patch_async_client(monkeypatch, handler)

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Token is invalid or expired"}


def test_proxy_returns_bad_gateway_when_upstream_is_unavailable(monkeypatch: MonkeyPatch) -> None:
    _patch_identity_url(monkeypatch)

    async def handler(
        _method: str,
        _url: str,
        _content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        raise httpx.ConnectError("identity-service unavailable")

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream service unavailable"}
