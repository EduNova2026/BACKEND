from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.health import health_response
from shared.logging import configure_logging

from app.config import settings
from app.database import seed_roles
from app.routers.auth import router as auth_router


def create_app() -> FastAPI:
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    async def _seed_roles_on_startup() -> None:
        await seed_roles()

    def health_check() -> dict[str, str]:
        return health_response(settings.app_name)

    app.add_api_route("/health", health_check, methods=["GET"], tags=["health"])

    return app


app = create_app()
