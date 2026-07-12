import math
import wave
from pathlib import Path

import pytest

from app.config import Settings
from app.services.media import probe_audio
from app.services.tuning_analyzer import analyze_tuning


def make_tone(path: Path, frequency: float, duration: float = 6.0) -> None:
    sample_rate = 44100
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        frames = bytearray()
        for index in range(round(duration * sample_rate)):
            fundamental = math.sin(2 * math.pi * frequency * index / sample_rate)
            harmonic = 0.22 * math.sin(2 * math.pi * frequency * 2 * index / sample_rate)
            sample = round(12000 * (fundamental + harmonic))
            frames.extend(sample.to_bytes(2, "little", signed=True))
        output.writeframes(frames)


@pytest.mark.audio
@pytest.mark.asyncio
@pytest.mark.parametrize(("frequency", "classification"), [(440.0, "440"), (432.0, "432")])
async def test_estimates_reference_tuning(
    tmp_path: Path, frequency: float, classification: str
) -> None:
    source = tmp_path / f"tone-{frequency}.wav"
    make_tone(source, frequency)
    settings = Settings(temp_root=tmp_path, analysis_segment_seconds=5)
    info = await probe_audio(source, settings)
    result = await analyze_tuning(source, info, settings, lambda _: None)
    assert result.classification == classification
    assert result.estimated_reference_hz == pytest.approx(frequency, abs=0.8)
    assert result.confidence >= 40
