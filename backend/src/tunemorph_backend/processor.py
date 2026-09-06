import asyncio
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from tunemorph_audio.models import ProcessingParameters
from tunemorph_audio.pipeline import (
    analyze_audio,
    render_preview,
    style_notes,
    transcribe_dominant_pitch,
    write_midi,
)

from .database import session_factory
from .models import ProcessingJob, ProcessingResult, Project, ProjectStatus
from .storage import LocalProjectStorage

logger = logging.getLogger(__name__)


class InProcessJobQueue:
    """Small development queue with an API replaceable by a distributed worker."""

    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tunemorph-job")
        self.futures: set[Future[None]] = set()

    def enqueue(self, project_id: str, job_id: str, data_dir: Path) -> None:
        future = self.executor.submit(
            lambda: asyncio.run(process_project(project_id, job_id, data_dir))
        )
        self.futures.add(future)
        future.add_done_callback(self.futures.discard)


job_queue = InProcessJobQueue()


def parameters_from(settings: dict[str, Any]) -> ProcessingParameters:
    allowed = ProcessingParameters.__dataclass_fields__.keys()
    values = {key: value for key, value in settings.items() if key in allowed}
    return ProcessingParameters(**values)


async def set_stage(job_id: str, stage: ProjectStatus, progress: int) -> None:
    async with session_factory() as session:
        job = await session.get(ProcessingJob, job_id)
        if job is None:
            return
        project = await session.get(Project, job.project_id)
        if project is None:
            return
        job.status = project.status = stage
        job.progress = progress
        await session.commit()
        logger.info(
            "processing_stage",
            extra={"project_id": project.id, "job_id": job.id, "processing_stage": stage.value},
        )


async def process_project(project_id: str, job_id: str, data_dir: Path) -> None:
    storage = LocalProjectStorage(data_dir)
    try:
        async with session_factory() as session:
            project = await session.scalar(
                select(Project)
                .where(Project.id == project_id)
                .options(selectinload(Project.audio_file))
            )
            if project is None or project.audio_file is None:
                raise ValueError("Project audio is missing")
            source = storage.resolve(project.audio_file.storage_key)
            style, raw_settings = project.style, project.settings

        await set_stage(job_id, ProjectStatus.analyzing, 15)
        analysis, audio, sample_rate = await asyncio.to_thread(analyze_audio, source)
        await set_stage(job_id, ProjectStatus.transcribing, 40)
        raw_notes = await asyncio.to_thread(
            transcribe_dominant_pitch, audio, sample_rate, analysis.bpm
        )
        await set_stage(job_id, ProjectStatus.post_processing, 60)
        parameters = parameters_from(raw_settings)
        await set_stage(job_id, ProjectStatus.styling, 72)
        styled_notes, program, tempo_factor = await asyncio.to_thread(
            style_notes, raw_notes, style, analysis.bpm, parameters
        )
        output_bpm = analysis.bpm * tempo_factor
        midi_key = f"projects/{project_id}/midi/arrangement_{style}.mid"
        preview_key = f"projects/{project_id}/preview/arrangement_{style}.wav"
        await asyncio.to_thread(
            write_midi, styled_notes, storage.resolve(midi_key), output_bpm, program
        )
        await set_stage(job_id, ProjectStatus.rendering, 88)
        await asyncio.to_thread(
            render_preview,
            styled_notes,
            storage.resolve(preview_key),
            analysis.duration_seconds,
            style,
        )
        async with session_factory() as session:
            project = await session.get(Project, project_id)
            job = await session.get(ProcessingJob, job_id)
            if project is None or job is None:
                return
            project.analysis = {
                "bpm": analysis.bpm,
                "key": analysis.key,
                "confidence": analysis.confidence,
                "duration_seconds": analysis.duration_seconds,
                "note_count": len(styled_notes),
            }
            session.add(
                ProcessingResult(
                    project_id=project_id,
                    midi_storage_key=midi_key,
                    preview_storage_key=preview_key,
                    note_count=len(styled_notes),
                )
            )
            project.status = job.status = ProjectStatus.completed
            job.progress = 100
            await session.commit()
    except Exception as error:
        logger.exception(
            "processing_failed",
            extra={"project_id": project_id, "job_id": job_id, "processing_stage": "failed"},
        )
        async with session_factory() as session:
            project = await session.get(Project, project_id)
            job = await session.get(ProcessingJob, job_id)
            if project:
                project.status = ProjectStatus.failed
                project.error = str(error)
            if job:
                job.status = ProjectStatus.failed
            await session.commit()
