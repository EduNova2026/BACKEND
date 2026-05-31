from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str
    app_env: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
    )
