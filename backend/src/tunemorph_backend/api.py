import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .audio_validation import InvalidAudioError, probe_audio
from .config import Settings, get_settings
from .database import get_session
from .models import AudioFile, Project, ProjectStatus
from .schemas import ProjectCreate, ProjectResponse, StatusResponse, StyleSummary
from .storage import LocalProjectStorage, ProjectStorage, UploadTooLargeError

router = APIRouter(prefix="/api")

ALLOWED_UPLOADS = {
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave"},
    ".flac": {"audio/flac", "audio/x-flac"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "video/mp4"},
}


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return LocalProjectStorage(settings.data_dir)


async def find_project(project_id: str, session: AsyncSession) -> Project:
    project = await session.scalar(
        select(Project).where(Project.id == project_id).options(selectinload(Project.audio_file))
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def write_metadata(storage: ProjectStorage, project: Project) -> None:
    project_root = storage.resolve(f"projects/{project.id}")
    metadata = {
        "id": project.id,
        "status": project.status.value,
        "original_filename": project.original_filename,
        "style": project.style,
    }
    (project_root / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


STYLES = (
    StyleSummary(
        id="original",
        name="Original",
        description="Preserve the transcription's structure.",
        icon="waveform",
    ),
    StyleSummary(
        id="music_box",
        name="Music Box",
        description="Bright melody and delicate mechanical arpeggios.",
        icon="sparkles",
    ),
    StyleSummary(
        id="solo_piano",
        name="Solo Piano",
        description="Playable two-hand piano voicings.",
        icon="piano",
    ),
    StyleSummary(
        id="eight_bit",
        name="8-Bit",
        description="Tight quantisation and limited chiptune voices.",
        icon="gamepad",
    ),
    StyleSummary(
        id="lullaby",
        name="Lullaby",
        description="Soft dynamics and a calmer arrangement.",
        icon="moon",
    ),
)


@router.get("/styles", response_model=list[StyleSummary], tags=["styles"])
async def list_styles() -> tuple[StyleSummary, ...]:
    return STYLES


@router.get("/styles/{style_id}", response_model=StyleSummary, tags=["styles"])
async def get_style(style_id: str) -> StyleSummary:
    try:
        return next(style for style in STYLES if style.id == style_id)
    except StopIteration as error:
        raise HTTPException(status_code=404, detail="Style not found") from error


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    storage: ProjectStorage = Depends(get_storage),
) -> Project:
    if payload.style not in {style.id for style in STYLES}:
        raise HTTPException(status_code=422, detail="Unknown style")
    project = Project(style=payload.style, settings=payload.settings)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    storage.create_project(project.id)
    write_metadata(storage, project)
    return await find_project(project.id, session)


@router.get("/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
async def get_project(project_id: str, session: AsyncSession = Depends(get_session)) -> Project:
    return await find_project(project_id, session)


@router.get("/projects/{project_id}/status", response_model=StatusResponse, tags=["projects"])
async def get_project_status(
    project_id: str, session: AsyncSession = Depends(get_session)
) -> StatusResponse:
    project = await find_project(project_id, session)
    progress = 5 if project.status == ProjectStatus.uploading else 0
    return StatusResponse(
        project_id=project.id, status=project.status, progress=progress, error=project.error
    )


@router.post("/projects/{project_id}/audio", response_model=ProjectResponse, tags=["projects"])
async def upload_audio(
    project_id: str,
    audio: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    storage: ProjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> Project:
    project = await find_project(project_id, session)
    if project.audio_file is not None:
        raise HTTPException(status_code=409, detail="Project already has an audio file")
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOADS or audio.content_type not in ALLOWED_UPLOADS[suffix]:
        await audio.close()
        raise HTTPException(status_code=415, detail="Unsupported audio format or MIME type")

    project.status = ProjectStatus.uploading
    supplied_name = (audio.filename or f"audio{suffix}").replace("\\", "/")
    project.original_filename = Path(supplied_name).name[:255]
    await session.commit()
    storage_key: str | None = None
    try:
        storage_key, size = await storage.store_upload(
            project.id, audio, suffix, settings.max_upload_mb * 1024 * 1024
        )
        probed = await probe_audio(storage.resolve(storage_key))
        if probed.duration_seconds > settings.max_audio_duration_seconds:
            raise InvalidAudioError("Audio exceeds the configured duration limit")
    except UploadTooLargeError as error:
        project.status = ProjectStatus.pending
        project.original_filename = None
        await session.commit()
        raise HTTPException(status_code=413, detail="Audio exceeds the upload limit") from error
    except InvalidAudioError as error:
        if storage_key:
            storage.resolve(storage_key).unlink(missing_ok=True)
        project.status = ProjectStatus.pending
        project.original_filename = None
        await session.commit()
        raise HTTPException(status_code=422, detail=str(error)) from error

    project.audio_file = AudioFile(
        storage_key=storage_key,
        media_type=audio.content_type,
        size_bytes=size,
        duration_seconds=probed.duration_seconds,
    )
    project.status = ProjectStatus.pending
    await session.commit()
    await session.refresh(project, attribute_names=["audio_file"])
    write_metadata(storage, project)
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["projects"])
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    storage: ProjectStorage = Depends(get_storage),
) -> None:
    project = await find_project(project_id, session)
    await session.delete(project)
    await session.commit()
    storage.delete_project(project_id)
