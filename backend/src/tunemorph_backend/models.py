import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProjectStatus(StrEnum):
    pending = "pending"
    uploading = "uploading"
    analyzing = "analyzing"
    separating = "separating"
    transcribing = "transcribing"
    post_processing = "post_processing"
    styling = "styling"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


def now_utc() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.pending
    )
    original_filename: Mapped[str | None] = mapped_column(String(255))
    style: Mapped[str] = mapped_column(String(32), default="music_box")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)

    audio_file: Mapped["AudioFile | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    result: Mapped["ProcessingResult | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, index=True)
    storage_key: Mapped[str] = mapped_column(String(512))
    media_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float]
    project: Mapped[Project] = relationship(back_populates="audio_file")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.pending
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    project: Mapped[Project] = relationship(back_populates="jobs")


class ProcessingResult(Base):
    __tablename__ = "processing_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, index=True)
    midi_storage_key: Mapped[str | None] = mapped_column(String(512))
    preview_storage_key: Mapped[str | None] = mapped_column(String(512))
    note_count: Mapped[int | None]
    project: Mapped[Project] = relationship(back_populates="result")
