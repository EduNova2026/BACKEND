from functools import lru_cache

from shared.config import AppSettings


class Settings(AppSettings):
    app_name: str = "api-gateway"
    identity_service_url: str = "http://identity-service:8000"
    scolarite_service_url: str = "http://scolarite-service:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
