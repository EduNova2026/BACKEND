from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.health import health_response
from shared.logging import configure_logging
from shared.schemas import HealthResponse

from app.config import settings
from app.database import engine, replica_engine, seed_roles
from app.routers.auth import router as auth_router
from app.redis_client import close_redis


def create_app() -> FastAPI:
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            if settings.database_url:
                await seed_roles()

            yield
        finally:
            await close_redis()

            if replica_engine is not None and replica_engine is not engine:
                await replica_engine.dispose()

            if engine is not None:
                await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(_request, call_next):
        response = await call_next(_request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    app.include_router(auth_router, prefix=settings.api_prefix)

    def health_check() -> dict[str, str]:
        return health_response(settings.app_name)

    app.add_api_route(
        "/health",
        health_check,
        methods=["GET"],
        tags=["health"],
        response_model=HealthResponse,
    )

    return app


app = create_app()
