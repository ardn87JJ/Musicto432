from datetime import timedelta
from pathlib import Path

import pytest

from app.config import Settings
from app.models import JobStatus, OutputFormat, utcnow
from app.services.jobs import JobManager, JobNotFoundError


@pytest.mark.asyncio
async def test_job_manual_deletion(tmp_path: Path) -> None:
    manager = JobManager(Settings(temp_root=tmp_path), rubberband_ready=True)
    record = await manager.create(OutputFormat.MP3, "../../mon titre.mp3")
    assert record.directory.is_dir()
    assert record.original_name == "mon-titre.mp3"
    await manager.delete(record.job_id)
    assert not record.directory.exists()
    with pytest.raises(JobNotFoundError):
        await manager.get(record.job_id)


@pytest.mark.asyncio
async def test_expiration_removes_result(tmp_path: Path) -> None:
    manager = JobManager(Settings(temp_root=tmp_path, file_ttl_minutes=1), True)
    record = await manager.create(OutputFormat.FLAC, "test.wav")
    result = record.directory / "result.flac"
    result.write_bytes(b"result")
    record.result_path = result
    record.status = JobStatus.COMPLETED
    record.expires_at = utcnow() - timedelta(seconds=1)
    assert await manager.cleanup_expired() == 1
    assert not record.directory.exists()
    with pytest.raises(JobNotFoundError):
        await manager.get(record.job_id)

