from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import final

import httpx
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import settings
from app.main import app
from app.routers.imports import import_url
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


def _patch_import_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "import_service_url", "http://import-service:8000")


def _patch_async_client(monkeypatch: MonkeyPatch, handler: Handler) -> None:
    monkeypatch.setattr(http_client, "create_async_client", lambda: FakeAsyncClient(handler))


def test_import_url_includes_service_api_prefix(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "import_service_url", "http://import-service:8000/")

    assert import_url("/imports/") == "http://import-service:8000/api/v1/imports/"


def test_import_list_forwards_authorization_header(monkeypatch: MonkeyPatch) -> None:
    _patch_import_url(monkeypatch)
    recorded_url = ""
    recorded_headers: dict[str, str] = {}

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_headers
        recorded_url = url
        recorded_headers = headers
        return httpx.Response(200, json=[])

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/imports/",
        headers={"Authorization": "Bearer import-token"},
    )

    assert response.status_code == 200
    assert recorded_url == "http://import-service:8000/api/v1/imports"
    assert recorded_headers["authorization"] == "Bearer import-token"


def test_import_upload_forwards_query_and_multipart_body(monkeypatch: MonkeyPatch) -> None:
    _patch_import_url(monkeypatch)
    recorded_url = ""
    recorded_content = b""
    recorded_headers: dict[str, str] = {}
    recorded_params: object = None

    async def handler(
        _method: str,
        url: str,
        content: bytes,
        headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_content, recorded_headers, recorded_params
        recorded_url = url
        recorded_content = content
        recorded_headers = headers
        recorded_params = params
        return httpx.Response(
            201,
            json={"id": "00000000-0000-0000-0000-000000000001"},
        )

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/imports/upload",
        params={"enseignement_id": "00000000-0000-0000-0000-000000000002"},
        headers={"Authorization": "Bearer upload-token"},
        files={"file": ("notes.csv", b"Nom;Note\nAMARI;12\n", "text/csv")},
    )

    assert response.status_code == 201
    assert recorded_url == "http://import-service:8000/api/v1/imports/upload"
    assert str(recorded_params) == "enseignement_id=00000000-0000-0000-0000-000000000002"
    assert recorded_headers["authorization"] == "Bearer upload-token"
    assert recorded_headers["content-type"].startswith("multipart/form-data")
    assert b"notes.csv" in recorded_content
    assert b"AMARI;12" in recorded_content


def test_import_routes_are_visible_in_gateway_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/imports/" in paths
    assert "/api/v1/imports/{job_id}" in paths
    assert "/api/v1/imports/upload" in paths
    assert "/api/v1/imports/{path}" not in paths
