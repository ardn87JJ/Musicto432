import math
import wave
from pathlib import Path

import pytest

from app.config import Settings
from app.services.media import (
    MediaValidationError,
    probe_audio,
    sanitize_filename,
    validate_extension,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../Été 2026?.MP3", "Ete-2026.mp3"),
        (".wav", "audio.wav"),
        ("mon morceau final.flac", "mon-morceau-final.flac"),
    ],
)
def test_sanitize_filename(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected


def test_reject_forbidden_extension() -> None:
    with pytest.raises(MediaValidationError, match="Format non autorisé"):
        validate_extension("payload.exe")


@pytest.mark.asyncio
async def test_reject_fake_audio(tmp_path: Path) -> None:
    fake = tmp_path / "fake.mp3"
    fake.write_text("ceci n'est pas un fichier audio")
    with pytest.raises(MediaValidationError, match="pas un fichier audio"):
        await probe_audio(fake, Settings(temp_root=tmp_path))


@pytest.mark.asyncio
async def test_reject_audio_over_duration_limit(tmp_path: Path) -> None:
    source = tmp_path / "too-long.wav"
    sample_rate = 8000
    with wave.open(str(source), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        samples = (
            round(1000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            for index in range(sample_rate * 2)
        )
        frames = b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)
        output.writeframes(frames)
    with pytest.raises(MediaValidationError, match="durée maximale"):
        await probe_audio(source, Settings(temp_root=tmp_path, max_audio_duration_seconds=1))
