from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OutputFormat(StrEnum):
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class JobStage(StrEnum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    PREPARATION = "preparation"
    CONVERSION = "conversion"
    FINALIZATION = "finalization"
    READY = "ready"


class JobPublic(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    stage: JobStage
    error: str | None = None
    expires_at: datetime | None = None
    download_name: str | None = None


class JobCreated(BaseModel):
    job_id: str
    status: JobStatus


class YouTubeRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    rights_confirmed: bool
    output_format: OutputFormat = OutputFormat.MP3


class AnalysisYouTubeRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    rights_confirmed: bool


class TuningResult(BaseModel):
    estimated_reference_hz: float
    offset_from_440_cents: float
    offset_from_432_cents: float
    classification: str
    confidence: int = Field(ge=0, le=100)
    analyzed_seconds: float
    diagnostic: str
    explanation: str


class AnalysisPublic(BaseModel):
    analysis_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    stage: str
    error: str | None = None
    result: TuningResult | None = None
    expires_at: datetime | None = None


class AnalysisCreated(BaseModel):
    analysis_id: str
    status: JobStatus


class HealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, bool]


class CapabilitiesResponse(BaseModel):
    input_formats: list[str]
    output_formats: list[str]
    max_upload_mb: int
    max_duration_seconds: int
    youtube_available: bool
    rubberband_available: bool
    tuning_analysis_available: bool


def utcnow() -> datetime:
    return datetime.now(UTC)
