import asyncio
import contextlib
import shutil
import tempfile
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from app.config import get_settings
from app.models import (
    AnalysisCreated,
    AnalysisPublic,
    AnalysisYouTubeRequest,
    BatchDownloadRequest,
    CapabilitiesResponse,
    HealthResponse,
    JobCreated,
    JobPublic,
    JobStatus,
    OutputFormat,
    YouTubeInspectRequest,
    YouTubeMetadata,
    YouTubeRequest,
)
from app.rate_limit import RateLimitMiddleware
from app.services.analysis_jobs import AnalysisManager, AnalysisNotFoundError
from app.services.jobs import JobManager, JobNotFoundError
from app.services.media import MediaValidationError, sanitize_filename, validate_extension
from app.services.system import command_available, rubberband_available, temp_directory_accessible
from app.services.youtube import YouTubeImportError, inspect_youtube

settings = get_settings()


def validate_reference_change(source: float, target: float) -> None:
    if abs(source - target) < 0.001:
        raise HTTPException(
            status_code=400,
            detail="La fréquence source et la fréquence cible doivent être différentes.",
        )


async def cleanup_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(60)
        await app.state.jobs.cleanup_expired()
        await app.state.analyses.cleanup_expired()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.temp_root.mkdir(parents=True, exist_ok=True)
    rubberband = await rubberband_available()
    app.state.rubberband = rubberband
    app.state.jobs = JobManager(settings, rubberband)
    app.state.analyses = AnalysisManager(settings)
    app.state.cleanup_task = asyncio.create_task(cleanup_loop(app))
    yield
    app.state.cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await app.state.cleanup_task
    await app.state.jobs.shutdown()
    await app.state.analyses.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.request_limit_per_minute)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next: object):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api/jobs") else "no-cache"
    )
    return response


@app.exception_handler(JobNotFoundError)
async def job_not_found(_: Request, __: JobNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Traitement introuvable ou expiré."})


@app.exception_handler(AnalysisNotFoundError)
async def analysis_not_found(_: Request, __: AnalysisNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Analyse introuvable ou expirée."})


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    checks = {
        "ffmpeg": await command_available("ffmpeg"),
        "ffprobe": await command_available("ffprobe"),
        "rubberband": await rubberband_available(),
        "temporary_directory": temp_directory_accessible(settings.temp_root),
    }
    return HealthResponse(
        status="ok" if all(checks.values()) else "degraded",
        version=settings.app_version,
        checks=checks,
    )


@app.get("/api/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    rubberband = await rubberband_available()
    return CapabilitiesResponse(
        input_formats=["mp3", "wav", "flac", "m4a", "aac", "ogg"],
        output_formats=[item.value for item in OutputFormat],
        max_upload_mb=settings.max_upload_mb,
        max_duration_seconds=settings.max_audio_duration_seconds,
        youtube_available=settings.youtube_enabled and shutil.which("yt-dlp") is not None,
        rubberband_available=rubberband,
        tuning_analysis_available=True,
    )


async def save_upload(upload: UploadFile, target: Path) -> None:
    size = 0
    try:
        with target.open("xb") as destination:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Le fichier dépasse la limite de {settings.max_upload_mb} Mo.",
                    )
                destination.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Le fichier envoyé est vide.")


@app.post("/api/jobs/upload", response_model=JobCreated, status_code=202)
async def upload_job(
    file: Annotated[UploadFile, File()],
    output_format: Annotated[OutputFormat, Form()] = OutputFormat.MP3,
    source_reference_hz: Annotated[float, Form(ge=400, le=480)] = 440,
    target_reference_hz: Annotated[float, Form(ge=400, le=480)] = 432,
) -> JobCreated:
    validate_reference_change(source_reference_hz, target_reference_hz)
    filename = sanitize_filename(file.filename or "audio")
    try:
        suffix = validate_extension(filename)
    except MediaValidationError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    record = await app.state.jobs.create(
        output_format,
        filename,
        source_reference_hz,
        target_reference_hz,
    )
    source_path = record.directory / f"source{suffix}"
    try:
        await save_upload(file, source_path)
    except Exception:
        await app.state.jobs.delete(record.job_id)
        raise
    app.state.jobs.start_file(record, source_path)
    return JobCreated(job_id=record.job_id, status=JobStatus.QUEUED)


@app.post("/api/jobs/youtube", response_model=JobCreated, status_code=202)
async def youtube_job(payload: YouTubeRequest) -> JobCreated:
    if not settings.youtube_enabled or shutil.which("yt-dlp") is None:
        raise HTTPException(status_code=503, detail="L’import YouTube est indisponible.")
    if not payload.rights_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Vous devez confirmer disposer des droits nécessaires.",
        )
    validate_reference_change(payload.source_reference_hz, payload.target_reference_hz)
    record = await app.state.jobs.create(
        payload.output_format,
        f"{payload.title}.audio" if payload.title else "youtube-audio",
        payload.source_reference_hz,
        payload.target_reference_hz,
    )
    app.state.jobs.start_youtube(record, payload.url)
    return JobCreated(job_id=record.job_id, status=JobStatus.QUEUED)


@app.post("/api/youtube/inspect", response_model=YouTubeMetadata)
async def youtube_inspect(payload: YouTubeInspectRequest) -> YouTubeMetadata:
    if not settings.youtube_enabled or shutil.which("yt-dlp") is None:
        raise HTTPException(status_code=503, detail="L’import YouTube est indisponible.")
    if not payload.rights_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Confirmez d’abord disposer des droits nécessaires.",
        )
    try:
        return await inspect_youtube(payload.url, settings)
    except YouTubeImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs/batch-download")
async def batch_download(payload: BatchDownloadRequest) -> FileResponse:
    records = []
    for job_id in dict.fromkeys(payload.job_ids):
        record = await app.state.jobs.get(job_id)
        if record.status != JobStatus.COMPLETED or not record.result_path:
            raise HTTPException(
                status_code=409,
                detail="Un résultat de la sélection n’est pas prêt.",
            )
        if not record.result_path.is_file():
            raise HTTPException(status_code=410, detail="Un résultat de la sélection a expiré.")
        records.append(record)
    with tempfile.NamedTemporaryFile(
        prefix="musicto432-batch-", suffix=".zip", dir=settings.temp_root, delete=False
    ) as archive_file:
        archive_path = Path(archive_file.name)
    used_names: set[str] = set()
    try:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, record in enumerate(records, start=1):
                name = record.download_name or f"resultat-{index}.{record.output_format.value}"
                if name in used_names:
                    name = f"{Path(name).stem}-{index}{Path(name).suffix}"
                used_names.add(name)
                archive.write(record.result_path, arcname=name)
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename="MusicTo432_resultats.zip",
        background=BackgroundTask(archive_path.unlink, missing_ok=True),
    )


@app.get("/api/jobs/{job_id}", response_model=JobPublic)
async def get_job(job_id: str) -> JobPublic:
    return (await app.state.jobs.get(job_id)).public()


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str) -> FileResponse:
    record = await app.state.jobs.get(job_id)
    if record.status != JobStatus.COMPLETED or not record.result_path:
        raise HTTPException(status_code=409, detail="Le résultat n’est pas encore disponible.")
    if not record.result_path.is_file():
        raise HTTPException(status_code=410, detail="Le fichier a expiré.")
    media_types = {"mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac"}
    return FileResponse(
        record.result_path,
        media_type=media_types[record.output_format.value],
        filename=record.download_name,
    )


@app.delete("/api/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str) -> None:
    await app.state.jobs.delete(job_id)


@app.post("/api/analysis/upload", response_model=AnalysisCreated, status_code=202)
async def analysis_upload(
    file: Annotated[UploadFile, File()],
) -> AnalysisCreated:
    filename = sanitize_filename(file.filename or "audio")
    try:
        suffix = validate_extension(filename)
    except MediaValidationError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    record = await app.state.analyses.create()
    source_path = record.directory / f"source{suffix}"
    try:
        await save_upload(file, source_path)
    except Exception:
        await app.state.analyses.delete(record.analysis_id)
        raise
    app.state.analyses.start_file(record, source_path)
    return AnalysisCreated(analysis_id=record.analysis_id, status=JobStatus.QUEUED)


@app.post("/api/analysis/youtube", response_model=AnalysisCreated, status_code=202)
async def analysis_youtube(payload: AnalysisYouTubeRequest) -> AnalysisCreated:
    if not settings.youtube_enabled or shutil.which("yt-dlp") is None:
        raise HTTPException(status_code=503, detail="L’import YouTube est indisponible.")
    if not payload.rights_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Vous devez confirmer disposer des droits nécessaires.",
        )
    record = await app.state.analyses.create()
    app.state.analyses.start_youtube(record, payload.url)
    return AnalysisCreated(analysis_id=record.analysis_id, status=JobStatus.QUEUED)


@app.get("/api/analysis/{analysis_id}", response_model=AnalysisPublic)
async def get_analysis(analysis_id: str) -> AnalysisPublic:
    return (await app.state.analyses.get(analysis_id)).public()


@app.delete("/api/analysis/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: str) -> None:
    await app.state.analyses.delete(analysis_id)
