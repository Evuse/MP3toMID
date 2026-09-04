from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/tunemorph.db"
    data_dir: Path = Path("data")
    max_upload_mb: int = Field(default=200, ge=1, le=2048)
    max_audio_duration_seconds: int = Field(default=1800, ge=1, le=86_400)
    auto_delete_files_after_hours: int = Field(default=24, ge=1)
    model_cache_dir: Path = Path("data/models")
    preview_soundfont: Path | None = None
    processing_mode: str = "fast"
    backend_cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    @field_validator("processing_mode")
    @classmethod
    def validate_processing_mode(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"fast", "high_quality"}:
            raise ValueError("PROCESSING_MODE must be fast or high_quality")
        return normalized

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
