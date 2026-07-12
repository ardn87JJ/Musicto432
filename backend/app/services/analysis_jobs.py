import asyncio
import contextlib
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app.config import Settings
from app.models import AnalysisPublic, JobStatus, TuningResult, utcnow
from app.services.media import MediaValidationError, probe_audio
from app.services.tuning_analyzer import TuningAnalysisError, analyze_tuning
from app.services.youtube import YouTubeImportError, download_youtube_audio, validate_youtube_url


@dataclass
class AnalysisRecord:
    analysis_id: str
    directory: Path
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    stage: str = "preparation"
    error: str | None = None
    result: TuningResult | None = None
    created_at: datetime = field(default_factory=utcnow)
    expires_at: datetime | None = None
    task: asyncio.Task[None] | None = None

    def public(self) -> AnalysisPublic:
        return AnalysisPublic(
            analysis_id=self.analysis_id,
            status=self.status,
            progress=self.progress,
            stage=self.stage,
            error=self.error,
            result=self.result,
            expires_at=self.expires_at,
        )


class AnalysisNotFoundError(KeyError):
    pass


class AnalysisManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._analyses: dict[str, AnalysisRecord] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)

    async def create(self) -> AnalysisRecord:
        analysis_id = uuid.uuid4().hex
        directory = self.settings.temp_root / f"analysis-{analysis_id}"
        directory.mkdir(parents=True, exist_ok=False)
        record = AnalysisRecord(analysis_id=analysis_id, directory=directory)
        async with self._lock:
            self._analyses[analysis_id] = record
        return record

    async def get(self, analysis_id: str) -> AnalysisRecord:
        if len(analysis_id) != 32 or any(ch not in "0123456789abcdef" for ch in analysis_id):
            raise AnalysisNotFoundError(analysis_id)
        async with self._lock:
            record = self._analyses.get(analysis_id)
        if record is None or record.status == JobStatus.DELETED:
            raise AnalysisNotFoundError(analysis_id)
        return record

    def start_file(self, record: AnalysisRecord, source_path: Path) -> None:
        record.task = asyncio.create_task(self._run(record, source_path))

    def start_youtube(self, record: AnalysisRecord, url: str) -> None:
        record.task = asyncio.create_task(self._run_youtube(record, url))

    async def _run_youtube(self, record: AnalysisRecord, url: str) -> None:
        try:
            record.status = JobStatus.PROCESSING
            record.stage = "download"
            record.progress = 3
            checked_url = await validate_youtube_url(url)
            source = await download_youtube_audio(checked_url, record.directory, self.settings)
            record.progress = 10
            await self._analyze_locked(record, source)
        except asyncio.CancelledError:
            raise
        except (YouTubeImportError, MediaValidationError, TuningAnalysisError, OSError) as exc:
            self._fail(record, str(exc))

    async def _run(self, record: AnalysisRecord, source_path: Path) -> None:
        try:
            await self._analyze_locked(record, source_path)
        except asyncio.CancelledError:
            raise
        except (MediaValidationError, TuningAnalysisError, OSError) as exc:
            self._fail(record, str(exc))

    async def _analyze_locked(self, record: AnalysisRecord, source_path: Path) -> None:
        async with self._semaphore:
            record.status = JobStatus.PROCESSING
            record.stage = "preparation"
            record.progress = max(record.progress, 8)
            info = await probe_audio(source_path, self.settings)
            record.stage = "analysis"

            def update_progress(value: int) -> None:
                record.progress = max(record.progress, value)

            record.result = await analyze_tuning(
                source_path, info, self.settings, update_progress
            )
            record.status = JobStatus.COMPLETED
            record.stage = "ready"
            record.progress = 100
            record.expires_at = utcnow() + timedelta(minutes=self.settings.file_ttl_minutes)
            shutil.rmtree(record.directory, ignore_errors=True)

    def _fail(self, record: AnalysisRecord, message: str) -> None:
        record.status = JobStatus.FAILED
        record.error = message[:500] or "L’analyse a échoué."
        record.progress = 0
        shutil.rmtree(record.directory, ignore_errors=True)

    async def delete(self, analysis_id: str) -> None:
        record = await self.get(analysis_id)
        if record.task and not record.task.done():
            record.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await record.task
        shutil.rmtree(record.directory, ignore_errors=True)
        record.status = JobStatus.DELETED

    async def cleanup_expired(self) -> int:
        now = utcnow()
        async with self._lock:
            records = list(self._analyses.values())
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
                self._analyses.pop(record.analysis_id, None)
        return len(expired)

    async def shutdown(self) -> None:
        async with self._lock:
            records = list(self._analyses.values())
        for record in records:
            if record.task and not record.task.done():
                record.task.cancel()
        await asyncio.gather(
            *(record.task for record in records if record.task), return_exceptions=True
        )
