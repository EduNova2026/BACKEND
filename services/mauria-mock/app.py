from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse


app = FastAPI(title="Mauria Mock")


@app.post("/aurion/login")
def login(payload: dict[str, Any] | None = Body(default=None)):
    payload = payload or {}
    email = payload.get("email")
    password = payload.get("password")

    valid_email = isinstance(email, str) and (
        email.endswith("@junia.com") or email.endswith("@ext.junia.com")
    )
    valid_password = isinstance(password, str) and bool(password)

    if valid_email and valid_password:
        return {"status": "ok", "email": email}

    return JSONResponse(status_code=500, content={"error": "Identifiants invalides"})
