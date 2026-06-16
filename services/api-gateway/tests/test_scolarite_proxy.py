from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import final

import httpx
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import settings
from app.main import app
from app.routers.scolarite import scolarite_url
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


def _patch_scolarite_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "scolarite_service_url", "http://scolarite-service:8000")


def _patch_async_client(monkeypatch: MonkeyPatch, handler: Handler) -> None:
    monkeypatch.setattr(http_client, "create_async_client", lambda: FakeAsyncClient(handler))


def test_scolarite_url_includes_service_api_prefix(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "scolarite_service_url", "http://scolarite-service:8000/")

    assert scolarite_url("/promotions/") == "http://scolarite-service:8000/api/v1/promotions/"


def test_collection_without_trailing_slash_forwards_to_prefixed_upstream(
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_scolarite_url(monkeypatch)
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
        "/api/v1/scolarite/promotions",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert recorded_url == "http://scolarite-service:8000/api/v1/promotions/"
    assert recorded_headers["authorization"] == "Bearer access-token"


def test_scolarite_create_forwards_request_body(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_content = b""

    async def handler(
        _method: str,
        url: str,
        content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_content
        recorded_url = url
        recorded_content = content
        return httpx.Response(201, json={"id": "00000000-0000-0000-0000-000000000001"})

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/scolarite/groupes/",
        json={
            "nom": "TD1",
            "promotion_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 201
    assert recorded_url == "http://scolarite-service:8000/api/v1/groupes/"
    assert recorded_content == (
        b'{"nom":"TD1","promotion_id":"00000000-0000-0000-0000-000000000001"}'
    )


def test_scolarite_resolve_forwards_query_params(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_params: object = None

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_params
        recorded_url = url
        recorded_params = params
        return httpx.Response(200, json={"id": "00000000-0000-0000-0000-000000000001"})

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/etudiants/resolve",
        params={
            "promotion_id": "00000000-0000-0000-0000-000000000002",
            "nom": "dupont",
            "prenom": "elodie",
        },
    )

    assert response.status_code == 200
    assert recorded_url == "http://scolarite-service:8000/api/v1/etudiants/resolve"
    assert (
        str(recorded_params)
        == "promotion_id=00000000-0000-0000-0000-000000000002&nom=dupont&prenom=elodie"
    )


def test_scolarite_utilisateurs_list_forwards_query_params(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_params: object = None

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_params
        recorded_url = url
        recorded_params = params
        return httpx.Response(200, json=[])

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/utilisateurs",
        params={"search": "alice", "role": "responsable_pedagogique", "actif": "true"},
    )

    assert response.status_code == 200
    assert recorded_url == "http://scolarite-service:8000/api/v1/utilisateurs/"
    assert str(recorded_params) == "search=alice&role=responsable_pedagogique&actif=true"


def test_scolarite_utilisateur_detail_forwards_to_utilisateur_id(
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_url
        recorded_url = url
        return httpx.Response(
            200,
            json={
                "id": "00000000-0000-0000-0000-000000000001",
                "email": "alice@example.com",
                "nom": "Durand",
                "prenom": "Alice",
                "roles": [],
                "actif": True,
                "premier_login": False,
            },
        )

    _patch_async_client(monkeypatch, handler)

    response = client.get("/api/v1/scolarite/utilisateurs/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 200
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/utilisateurs/"
        "00000000-0000-0000-0000-000000000001"
    )


def test_scolarite_promotion_enroll_forwards_to_prefixed_upstream(
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_method = ""
    recorded_url = ""

    async def handler(
        method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_method, recorded_url
        recorded_method = method
        recorded_url = url
        return httpx.Response(200, json={"id": "00000000-0000-0000-0000-000000000002"})

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/scolarite/promotions/00000000-0000-0000-0000-000000000001/"
        "etudiants/00000000-0000-0000-0000-000000000002"
    )

    assert response.status_code == 200
    assert recorded_method == "POST"
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/promotions/"
        "00000000-0000-0000-0000-000000000001/etudiants/"
        "00000000-0000-0000-0000-000000000002"
    )


def test_scolarite_etudiant_moyenne_forwards_query_params(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_semestre = ""

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_semestre
        recorded_url = url
        if hasattr(params, "get"):
            recorded_semestre = str(params.get("semestre"))
        return httpx.Response(200, json={"moyenne": 14.5})

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/etudiants/00000000-0000-0000-0000-000000000001/moyenne",
        params={"semestre": "1"},
    )

    assert response.status_code == 200
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/etudiants/"
        "00000000-0000-0000-0000-000000000001/moyenne"
    )
    assert recorded_semestre == "1"


def test_scolarite_promotion_moyenne_forwards_query_params(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_semestre = ""

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_semestre
        recorded_url = url
        if hasattr(params, "get"):
            recorded_semestre = str(params.get("semestre"))
        return httpx.Response(200, json={"moyenne": 13.25})

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/promotions/00000000-0000-0000-0000-000000000001/moyenne",
        params={"semestre": "1"},
    )

    assert response.status_code == 200
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/promotions/"
        "00000000-0000-0000-0000-000000000001/moyenne"
    )
    assert recorded_semestre == "1"


def test_scolarite_enseignement_moyenne_forwards_query_params(
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_semestre = ""

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_semestre
        recorded_url = url
        if hasattr(params, "get"):
            recorded_semestre = str(params.get("semestre"))
        return httpx.Response(200, json={"moyenne": 12.75})

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/enseignements/00000000-0000-0000-0000-000000000001/moyenne",
        params={"semestre": "1"},
    )

    assert response.status_code == 200
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/enseignements/"
        "00000000-0000-0000-0000-000000000001/moyenne"
    )
    assert recorded_semestre == "1"


def test_scolarite_promotion_etudiants_moyennes_forwards_query_params(
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_semestre = ""

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_semestre
        recorded_url = url
        if hasattr(params, "get"):
            recorded_semestre = str(params.get("semestre"))
        return httpx.Response(200, json=[])

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/promotions/00000000-0000-0000-0000-000000000001/etudiants/moyennes",
        params={"semestre": "1"},
    )

    assert response.status_code == 200
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/promotions/"
        "00000000-0000-0000-0000-000000000001/etudiants/moyennes"
    )
    assert recorded_semestre == "1"


def test_scolarite_groupe_etudiants_moyennes_forwards_query_params(
    monkeypatch: MonkeyPatch,
) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_semestre = ""

    async def handler(
        _method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_semestre
        recorded_url = url
        if hasattr(params, "get"):
            recorded_semestre = str(params.get("semestre"))
        return httpx.Response(200, json=[])

    _patch_async_client(monkeypatch, handler)

    response = client.get(
        "/api/v1/scolarite/groupes/00000000-0000-0000-0000-000000000001/etudiants/moyennes",
        params={"semestre": "2"},
    )

    assert response.status_code == 200
    assert recorded_url == (
        "http://scolarite-service:8000/api/v1/groupes/"
        "00000000-0000-0000-0000-000000000001/etudiants/moyennes"
    )
    assert recorded_semestre == "2"


def test_scolarite_routes_are_visible_in_gateway_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/scolarite/promotions/" in paths
    assert "/api/v1/scolarite/groupes/" in paths
    assert "/api/v1/scolarite/etudiants/" in paths
    assert "/api/v1/scolarite/promotions/{promotion_id}/etudiants/{etudiant_id}" in paths
    assert "/api/v1/scolarite/etudiants/{etudiant_id}/moyenne" in paths
    assert "/api/v1/scolarite/promotions/{promotion_id}/moyenne" in paths
    assert "/api/v1/scolarite/promotions/{promotion_id}/etudiants/moyennes" in paths
    assert "/api/v1/scolarite/groupes/{groupe_id}/etudiants/moyennes" in paths
    assert "/api/v1/scolarite/enseignements/{enseignement_id}/moyenne" in paths
    assert "/api/v1/scolarite/etudiants/search" in paths
    assert "/api/v1/scolarite/etudiants/resolve" in paths
    assert "/api/v1/scolarite/examens/" in paths
    assert "/api/v1/scolarite/examens/{examen_id}" in paths
    assert "/api/v1/scolarite/notes/" in paths
    assert "/api/v1/scolarite/notes/batch" in paths
    assert "/api/v1/scolarite/notes/{note_id}" in paths
    assert "/api/v1/scolarite/roles/" in paths
    assert "/api/v1/scolarite/utilisateurs/" in paths
    assert "/api/v1/scolarite/utilisateurs/{utilisateur_id}" in paths
    assert "/api/v1/scolarite/{path}" not in paths


def test_scolarite_notes_batch_forwards_request_body(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_url = ""
    recorded_content = b""

    async def handler(
        _method: str,
        url: str,
        content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_url, recorded_content
        recorded_url = url
        recorded_content = content
        return httpx.Response(201, json=[])

    _patch_async_client(monkeypatch, handler)

    response = client.post(
        "/api/v1/scolarite/notes/batch",
        json={
            "examen_id": "00000000-0000-0000-0000-000000000001",
            "notes": [
                {
                    "etudiant_id": "00000000-0000-0000-0000-000000000002",
                    "valeur": 14.5,
                }
            ],
        },
    )

    assert response.status_code == 201
    assert recorded_url == "http://scolarite-service:8000/api/v1/notes/batch"
    assert b'"examen_id":"00000000-0000-0000-0000-000000000001"' in recorded_content


def test_scolarite_note_patch_forwards_to_note_id(monkeypatch: MonkeyPatch) -> None:
    _patch_scolarite_url(monkeypatch)
    recorded_method = ""
    recorded_url = ""

    async def handler(
        method: str,
        url: str,
        _content: bytes,
        _headers: dict[str, str],
        _params: object,
    ) -> httpx.Response:
        nonlocal recorded_method, recorded_url
        recorded_method = method
        recorded_url = url
        return httpx.Response(200, json={"id": "00000000-0000-0000-0000-000000000003"})

    _patch_async_client(monkeypatch, handler)

    response = client.patch(
        "/api/v1/scolarite/notes/00000000-0000-0000-0000-000000000003",
        json={"valeur": 16.0},
    )

    assert response.status_code == 200
    assert recorded_method == "PATCH"
    assert recorded_url == "http://scolarite-service:8000/api/v1/notes/00000000-0000-0000-0000-000000000003"
