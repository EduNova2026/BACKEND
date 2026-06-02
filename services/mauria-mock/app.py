import os
from typing import Any

import httpx
from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Mauria Mock")

MAURIA_API_URL = os.environ.get("MAURIA_API_URL", "https://mauria-api.fly.dev")
ALLOW_STUDENT_BYPASS = os.environ.get("ALLOW_STUDENT_BYPASS", "false").lower() == "true"


@app.post("/aurion/login")
async def login(payload: dict[str, Any] | None = Body(default=None)):
    payload = payload or {}
    email = payload.get("email")
    password = payload.get("password")

    if not isinstance(email, str) or not isinstance(password, str) or not password:
        return JSONResponse(status_code=403, content={"error": "Accès refusé"})

    if not email.endswith("@student.junia.com") or not ALLOW_STUDENT_BYPASS:
        return JSONResponse(status_code=403, content={"error": "Accès refusé"})

    return await _proxy_to_real_mauria(email, password)


async def _proxy_to_real_mauria(email: str, password: str) -> Response:
    url = f"{MAURIA_API_URL}/aurion/login"
    try:
        async with httpx.AsyncClient() as client:
            upstream_response = await client.post(url, json={"email": email, "password": password})
    except httpx.HTTPError:
        return JSONResponse(status_code=502, content={"error": "Mauria upstream unavailable"})

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers={"Content-Type": "application/json"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "mauria-mock"}
