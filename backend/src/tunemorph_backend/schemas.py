from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ProjectStatus


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class StyleSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str
    icon: str
    available: bool = True


class ProjectCreate(BaseModel):
    style: str = "music_box"
    settings: dict[str, Any] = Field(default_factory=dict)


class AudioFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    media_type: str
    size_bytes: int
    duration_seconds: float


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    status: ProjectStatus
    original_filename: str | None
    style: str
    settings: dict[str, Any]
    analysis: dict[str, Any] | None
    error: str | None
    audio_file: AudioFileResponse | None = None


class StatusResponse(BaseModel):
    project_id: str
    status: ProjectStatus
    progress: int
    error: str | None
