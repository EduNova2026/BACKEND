from functools import lru_cache
from shared.config import DatabaseSettings


class Settings(DatabaseSettings):
    app_name: str = "scolarite-service"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    cache_roles_ttl_seconds: int = 3600
    cache_reference_ttl_seconds: int = 1800


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
