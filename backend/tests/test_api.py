import io
import math
import shutil
import subprocess
import time
import wave
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app, settings
from app.models import YouTubeMetadata


def has_rubberband() -> bool:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, check=False, text=True
    )
    return shutil.which("ffmpeg") is not None and "rubberband" in result.stdout


def make_short_tone(path: Path, duration: float = 0.5) -> None:
    sample_rate = 16000
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        frames = bytearray()
        for index in range(round(sample_rate * duration)):
            sample = round(8000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(sample.to_bytes(2, "little", signed=True))
        output.writeframes(frames)


@pytest.mark.audio
@pytest.mark.skipif(not has_rubberband(), reason="FFmpeg Rubber Band indisponible")
def test_complete_upload_download_delete_cycle(tmp_path: Path) -> None:
    source = tmp_path / "api-tone.wav"
    make_short_tone(source)
    with TestClient(app) as client, source.open("rb") as audio:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["checks"]["rubberband"] is True

        created = client.post(
            "/api/jobs/upload",
            files={"file": ("api-tone.wav", audio, "audio/wav")},
            data={
                "output_format": "flac",
                "source_reference_hz": "440",
                "target_reference_hz": "432",
            },
        )
        assert created.status_code == 202
        job_id = created.json()["job_id"]

        state = None
        for _ in range(100):
            state = client.get(f"/api/jobs/{job_id}").json()
            if state["status"] in {"completed", "failed"}:
                break
            time.sleep(0.02)
        assert state is not None
        assert state["status"] == "completed", state
        assert state["progress"] == 100
        assert state["source_reference_hz"] == 440
        assert state["target_reference_hz"] == 432

        download = client.get(f"/api/jobs/{job_id}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("audio/flac")
        assert len(download.content) > 100

        batch = client.post("/api/jobs/batch-download", json={"job_ids": [job_id]})
        assert batch.status_code == 200
        assert batch.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(batch.content)) as archive:
            assert archive.namelist() == ["api-tone_432Hz.flac"]

        assert client.delete(f"/api/jobs/{job_id}").status_code == 204
        assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_reject_identical_source_and_target_frequency(tmp_path: Path) -> None:
    source = tmp_path / "same.wav"
    make_short_tone(source)
    with TestClient(app) as client, source.open("rb") as audio:
        response = client.post(
            "/api/jobs/upload",
            files={"file": ("same.wav", audio, "audio/wav")},
            data={"source_reference_hz": "432", "target_reference_hz": "432"},
        )
    assert response.status_code == 400
    assert "doivent être différentes" in response.json()["detail"]


def test_youtube_inspection_returns_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_inspect(url: str, _settings) -> YouTubeMetadata:
        return YouTubeMetadata(
            title="Titre vérifié",
            uploader="Artiste",
            duration=185,
            thumbnail="https://i.ytimg.com/example.jpg",
            webpage_url=url,
        )

    monkeypatch.setattr("app.main.inspect_youtube", fake_inspect)
    monkeypatch.setattr("app.main.shutil.which", lambda _: "/usr/local/bin/yt-dlp")
    with TestClient(app) as client:
        response = client.post(
            "/api/youtube/inspect",
            json={"url": "https://youtu.be/abcdefghijk", "rights_confirmed": True},
        )
    assert response.status_code == 200
    assert response.json()["title"] == "Titre vérifié"
    assert response.json()["duration"] == 185


def test_upload_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    with TestClient(app) as client:
        response = client.post(
            "/api/jobs/upload",
            files={"file": ("large.wav", b"0" * (1024 * 1024 + 1), "audio/wav")},
            data={"output_format": "mp3"},
        )
    assert response.status_code == 413
    assert "1 Mo" in response.json()["detail"]


def test_progress_polling_is_not_rate_limited() -> None:
    unknown_job = "a" * 32
    with TestClient(app) as client:
        responses = [client.get(f"/api/jobs/{unknown_job}") for _ in range(45)]
    assert all(response.status_code == 404 for response in responses)


def test_analysis_polling_is_not_rate_limited() -> None:
    unknown_analysis = "b" * 32
    with TestClient(app) as client:
        responses = [client.get(f"/api/analysis/{unknown_analysis}") for _ in range(45)]
    assert all(response.status_code == 404 for response in responses)


def test_complete_file_tuning_analysis_cycle(tmp_path: Path) -> None:
    source = tmp_path / "analysis-tone.wav"
    make_short_tone(source, duration=3)
    with TestClient(app) as client, source.open("rb") as audio:
        created = client.post(
            "/api/analysis/upload",
            files={"file": ("analysis-tone.wav", audio, "audio/wav")},
        )
        assert created.status_code == 202
        analysis_id = created.json()["analysis_id"]
        state = None
        for _ in range(100):
            state = client.get(f"/api/analysis/{analysis_id}").json()
            if state["status"] in {"completed", "failed"}:
                break
            time.sleep(0.02)
        assert state is not None
        assert state["status"] == "completed", state
        assert state["result"]["classification"] == "440"
        assert state["result"]["estimated_reference_hz"] == pytest.approx(440, abs=1)
        assert client.delete(f"/api/analysis/{analysis_id}").status_code == 204
