from functools import lru_cache
from typing import Annotated, ClassVar

from pydantic import Field, field_validator
from pydantic_settings import NoDecode, SettingsConfigDict

from shared.config import AppSettings


class Settings(AppSettings):
    app_name: str = "api-gateway"
    api_prefix: str = "/api/v1"
    identity_service_url: str = "http://identity-service:8000"
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

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
