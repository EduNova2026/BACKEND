from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import _proxy_to_real_mauria

client = TestClient(app_module.app)


class FakeUpstreamResponse:
    """Mutable response stub that _proxy_to_real_mauria can read."""

    status_code: int = 200
    content: bytes = b'{"status":"ok","email":"etudiant@student.junia.com"}'

    @property
    def headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}


@pytest.mark.parametrize(
    "email, password",
    [
        ("teacher@junia.com", "secret"),
        ("admin@ext.junia.com", "pass"),
        ("bad@unknown.com", "secret"),
        ("no-domain", "secret"),
    ],
)
def test_mock_rejects_non_student_emails(email: str, password: str) -> None:
    app_module.ALLOW_STUDENT_BYPASS = True

    payload: dict[str, Any] = {"email": email, "password": password}
    resp = client.post("/aurion/login", json=payload)
    assert resp.status_code == 403
    assert resp.json() == {"error": "Accès refusé"}


def test_mock_rejects_student_email_when_bypass_disabled() -> None:
    app_module.ALLOW_STUDENT_BYPASS = False

    resp = client.post(
        "/aurion/login",
        json={"email": "etudiant@student.junia.com", "password": "secret"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"error": "Accès refusé"}


# ---- health ----

def test_health_check() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "mauria-mock"}


# ---- student proxy (unit via _proxy_to_real_mauria) ----


@pytest.mark.asyncio
async def test_proxy_student_success() -> None:
    fake = FakeUpstreamResponse()
    fake.status_code = 200
    fake.content = b'{"status":"ok","email":"etudiant@student.junia.com"}'

    app_module.ALLOW_STUDENT_BYPASS = True
    app_module.MAURIA_API_URL = "https://mauria-api.test"

    with patch("app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = fake
        mock_client_cls.return_value = mock_client

        resp = await _proxy_to_real_mauria("etudiant@student.junia.com", "secret")
        assert resp.status_code == 200
        assert resp.body == b'{"status":"ok","email":"etudiant@student.junia.com"}'
        mock_client.post.assert_awaited_once_with(
            "https://mauria-api.test/aurion/login",
            json={"email": "etudiant@student.junia.com", "password": "secret"},
        )


@pytest.mark.asyncio
async def test_proxy_student_upstream_401() -> None:
    fake = FakeUpstreamResponse()
    fake.status_code = 401
    fake.content = b'{"error":"bad credentials"}'

    app_module.ALLOW_STUDENT_BYPASS = True
    app_module.MAURIA_API_URL = "https://mauria-api.test"

    with patch("app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = fake
        mock_client_cls.return_value = mock_client

        resp = await _proxy_to_real_mauria("etudiant@student.junia.com", "wrong")
        assert resp.status_code == 401
        assert resp.body == b'{"error":"bad credentials"}'


@pytest.mark.asyncio
async def test_proxy_student_upstream_unavailable() -> None:
    app_module.ALLOW_STUDENT_BYPASS = True
    app_module.MAURIA_API_URL = "https://mauria-api.test"

    with patch("app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = httpx.ConnectError("refused")
        mock_client_cls.return_value = mock_client

        resp = await _proxy_to_real_mauria("etudiant@student.junia.com", "secret")
        assert resp.status_code == 502
        assert resp.body == b'{"error":"Mauria upstream unavailable"}'


# ---- integration: student path through the endpoint ----


def test_login_student_proxies_to_real_mauria_success() -> None:
    fake = FakeUpstreamResponse()
    fake.status_code = 200
    fake.content = b'{"status":"ok","email":"etudiant@student.junia.com"}'

    app_module.ALLOW_STUDENT_BYPASS = True
    app_module.MAURIA_API_URL = "https://mauria-api.test"

    with patch("app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = fake
        mock_client_cls.return_value = mock_client

        resp = client.post(
            "/aurion/login",
            json={"email": "etudiant@student.junia.com", "password": "secret"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "email": "etudiant@student.junia.com"}
        mock_client.post.assert_awaited_once_with(
            "https://mauria-api.test/aurion/login",
            json={"email": "etudiant@student.junia.com", "password": "secret"},
        )


def test_login_student_proxies_401() -> None:
    fake = FakeUpstreamResponse()
    fake.status_code = 401
    fake.content = b'{"error":"bad credentials"}'

    app_module.ALLOW_STUDENT_BYPASS = True
    app_module.MAURIA_API_URL = "https://mauria-api.test"

    with patch("app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = fake
        mock_client_cls.return_value = mock_client

        resp = client.post(
            "/aurion/login",
            json={"email": "etudiant@student.junia.com", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert resp.json() == {"error": "bad credentials"}


def test_login_student_upstream_unreachable() -> None:
    app_module.ALLOW_STUDENT_BYPASS = True
    app_module.MAURIA_API_URL = "https://mauria-api.test"

    with patch("app.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = httpx.ConnectError("refused")
        mock_client_cls.return_value = mock_client

        resp = client.post(
            "/aurion/login",
            json={"email": "etudiant@student.junia.com", "password": "secret"},
        )
        assert resp.status_code == 502
        assert resp.json() == {"error": "Mauria upstream unavailable"}
