import asyncio
import contextlib
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app.config import Settings
from app.models import JobPublic, JobStage, JobStatus, OutputFormat, utcnow
from app.services.audio_converter import ConversionError, convert_audio
from app.services.media import MediaValidationError, probe_audio, sanitize_filename
from app.services.youtube import YouTubeImportError, download_youtube_audio, validate_youtube_url


@dataclass
class JobRecord:
    job_id: str
    directory: Path
    output_format: OutputFormat
    original_name: str
    source_reference_hz: float
    target_reference_hz: float
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    stage: JobStage = JobStage.PREPARATION
    error: str | None = None
    result_path: Path | None = None
    download_name: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    expires_at: datetime | None = None
    task: asyncio.Task[None] | None = None

    def public(self) -> JobPublic:
        return JobPublic(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            stage=self.stage,
            error=self.error,
            expires_at=self.expires_at,
            download_name=self.download_name,
            source_reference_hz=self.source_reference_hz,
            target_reference_hz=self.target_reference_hz,
        )


class JobNotFoundError(KeyError):
    pass


class JobManager:
    def __init__(self, settings: Settings, rubberband_ready: bool) -> None:
        self.settings = settings
        self.rubberband_ready = rubberband_ready
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)

    async def create(
        self,
        output_format: OutputFormat,
        original_name: str,
        source_reference_hz: float = 440,
        target_reference_hz: float = 432,
    ) -> JobRecord:
        job_id = uuid.uuid4().hex
        directory = self.settings.temp_root / job_id
        directory.mkdir(parents=True, exist_ok=False)
        record = JobRecord(
            job_id=job_id,
            directory=directory,
            output_format=output_format,
            original_name=sanitize_filename(original_name),
            source_reference_hz=source_reference_hz,
            target_reference_hz=target_reference_hz,
        )
        async with self._lock:
            self._jobs[job_id] = record
        return record

    async def get(self, job_id: str) -> JobRecord:
        if len(job_id) != 32 or any(ch not in "0123456789abcdef" for ch in job_id):
            raise JobNotFoundError(job_id)
        async with self._lock:
            record = self._jobs.get(job_id)
        if record is None or record.status == JobStatus.DELETED:
            raise JobNotFoundError(job_id)
        return record

    def start_file(self, record: JobRecord, source_path: Path) -> None:
        record.task = asyncio.create_task(self._run_conversion(record, source_path))

    def start_youtube(self, record: JobRecord, url: str) -> None:
        record.task = asyncio.create_task(self._run_youtube(record, url))

    async def _run_youtube(self, record: JobRecord, url: str) -> None:
        try:
            record.status = JobStatus.PROCESSING
            record.stage = JobStage.DOWNLOAD
            record.progress = 2
            checked_url = await validate_youtube_url(url)
            source = await download_youtube_audio(checked_url, record.directory, self.settings)
            record.progress = 9
            await self._convert_locked(record, source)
        except asyncio.CancelledError:
            raise
        except (YouTubeImportError, MediaValidationError, ConversionError, OSError) as exc:
            self._fail(record, str(exc))

    async def _run_conversion(self, record: JobRecord, source_path: Path) -> None:
        try:
            await self._convert_locked(record, source_path)
        except asyncio.CancelledError:
            raise
        except (MediaValidationError, ConversionError, OSError) as exc:
            self._fail(record, str(exc))

    async def _convert_locked(self, record: JobRecord, source_path: Path) -> None:
        async with self._semaphore:
            if not self.rubberband_ready:
                raise ConversionError(
                    "Le serveur FFmpeg ne contient pas le filtre Rubber Band requis."
                )
            record.status = JobStatus.PROCESSING
            record.stage = JobStage.PREPARATION
            record.progress = max(record.progress, 5)
            info = await probe_audio(source_path, self.settings)
            stem = Path(record.original_name).stem or "audio"
            target_label = f"{record.target_reference_hz:g}Hz"
            record.download_name = f"{stem}_{target_label}.{record.output_format.value}"
            result_path = record.directory / f"result.{record.output_format.value}"
            record.stage = JobStage.CONVERSION
            record.progress = 10

            def update_progress(value: int) -> None:
                record.progress = max(record.progress, 10 + round(value * 0.85))

            await convert_audio(
                source_path,
                result_path,
                record.output_format,
                info,
                self.settings,
                update_progress,
                record.source_reference_hz,
                record.target_reference_hz,
            )
            record.stage = JobStage.FINALIZATION
            record.progress = 97
            record.result_path = result_path
            for path in record.directory.iterdir():
                if path != result_path and path.is_file():
                    path.unlink(missing_ok=True)
            record.status = JobStatus.COMPLETED
            record.stage = JobStage.READY
            record.progress = 100
            record.expires_at = utcnow() + timedelta(minutes=self.settings.file_ttl_minutes)

    def _fail(self, record: JobRecord, message: str) -> None:
        record.status = JobStatus.FAILED
        record.error = message[:500] or "Une erreur inconnue est survenue."
        record.progress = 0
        shutil.rmtree(record.directory, ignore_errors=True)

    async def delete(self, job_id: str) -> None:
        record = await self.get(job_id)
        if record.task and not record.task.done():
            record.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await record.task
        shutil.rmtree(record.directory, ignore_errors=True)
        record.status = JobStatus.DELETED
        record.result_path = None

    async def cleanup_expired(self) -> int:
        now = utcnow()
        async with self._lock:
            records = list(self._jobs.values())
        expired = [
            record
            for record in records
            if (record.expires_at and record.expires_at <= now)
            or record.created_at + timedelta(minutes=self.settings.file_ttl_minutes * 2) <= now
        ]
        for record in expired:
            if record.task and not record.task.done():
                record.task.cancel()
            shutil.rmtree(record.directory, ignore_errors=True)
            record.status = JobStatus.DELETED
            async with self._lock:
                self._jobs.pop(record.job_id, None)
        return len(expired)

    async def shutdown(self) -> None:
        async with self._lock:
            records = list(self._jobs.values())
        for record in records:
            if record.task and not record.task.done():
                record.task.cancel()
        await asyncio.gather(
            *(record.task for record in records if record.task), return_exceptions=True
        )
