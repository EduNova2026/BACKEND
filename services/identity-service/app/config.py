from functools import lru_cache
from typing import Annotated, ClassVar

from pydantic import Field, field_validator
from pydantic_settings import NoDecode, SettingsConfigDict

from shared.config import AppSettings


class Settings(AppSettings):
    app_name: str = "identity-service"
    api_prefix: str = "/api/v1"
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )
    database_url: str | None = None
    database_replica_url: str | None = None
    redis_url: str = "redis://redis:6379/0"
    mauria_api_url: str = "https://mauria-api.fly.dev"
    mauria_login_path: str = "/aurion/login"
    allow_student_bypass: bool = False
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 7
    rate_limit_login_max: int = 5
    rate_limit_login_window: int = 60

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
    )

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
