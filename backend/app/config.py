from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MusicTo432"
    app_version: str = "0.1.1"
    debug: bool = False
    temp_root: Path = Path("/tmp/musicto432")
    max_upload_mb: int = Field(default=250, ge=1, le=2048)
    max_audio_duration_seconds: int = Field(default=3600, ge=1, le=86400)
    file_ttl_minutes: int = Field(default=60, ge=1, le=1440)
    max_concurrent_jobs: int = Field(default=2, ge=1, le=32)
    request_limit_per_minute: int = Field(default=30, ge=1, le=1000)
    youtube_enabled: bool = True
    youtube_timeout_seconds: int = Field(default=180, ge=10, le=1800)
    ffmpeg_timeout_seconds: int = Field(default=7200, ge=30, le=86400)
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
