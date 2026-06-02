from functools import lru_cache

from pydantic import model_validator

from shared.config import DatabaseSettings


class Settings(DatabaseSettings):
    app_name: str = "identity-service"
    redis_url: str = "redis://redis:6379/0"
    mauria_api_url: str = "https://mauria-api.fly.dev"
    mauria_mock_url: str | None = None
    mauria_login_path: str = "/aurion/login"
    allow_student_bypass: bool = False
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 7
    rate_limit_login_max: int = 5
    rate_limit_login_window: int = 60

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.app_env == "production" and self.allow_student_bypass:
            raise ValueError("ALLOW_STUDENT_BYPASS cannot be enabled in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
