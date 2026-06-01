from functools import lru_cache
from shared.config import DatabaseSettings


class Settings(DatabaseSettings):
    app_name: str = "scolarite-service"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
