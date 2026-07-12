import math
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from app.config import Settings
from app.models import OutputFormat
from app.services.audio_converter import PITCH_CENTS, PITCH_RATIO, build_ffmpeg_args, convert_audio
from app.services.media import probe_audio


def has_rubberband() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, check=False, text=True
    )
    return "rubberband" in result.stdout


def make_sine(path: Path, frequency: float = 440.0, duration: float = 2.0) -> None:
    sample_rate = 48000
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        frames = bytearray()
        for index in range(round(duration * sample_rate)):
            sample = round(16000 * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames.extend(sample.to_bytes(2, "little", signed=True))
        output.writeframes(frames)


def dominant_frequency(path: Path) -> float:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "astats=metadata=1:reset=0",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    # La vérification spectrale précise est réalisée avec le filtre de détection zero-crossings.
    for line in result.stderr.splitlines():
        if "Zero crossings rate" in line:
            rate = float(line.rsplit(":", 1)[1].strip())
            return rate * 48000 / 2
    raise AssertionError("Fréquence dominante introuvable")


def test_exact_pitch_values() -> None:
    assert PITCH_RATIO == 432 / 440
    assert pytest.approx(0.9818181818181818) == PITCH_RATIO
    assert pytest.approx(1200 * math.log2(PITCH_RATIO)) == PITCH_CENTS


def test_command_is_an_argument_list_without_shell_tokens(tmp_path: Path) -> None:
    source = tmp_path / "source;touch-pwned.wav"
    target = tmp_path / "result.mp3"
    args = build_ffmpeg_args(source, target, OutputFormat.MP3)
    assert args[0] == "ffmpeg"
    assert str(source) in args
    assert "shell=True" not in args
    codec_slice = args[args.index("-c:a") : args.index("-c:a") + 4]
    assert codec_slice == ["-c:a", "libmp3lame", "-b:a", "320k"]
    assert f"rubberband=pitch={PITCH_RATIO:.16f}:tempo=1.0" in args


def test_custom_reference_ratio_is_built_server_side(tmp_path: Path) -> None:
    args = build_ffmpeg_args(
        tmp_path / "source.wav",
        tmp_path / "result.flac",
        OutputFormat.FLAC,
        source_reference_hz=432,
        target_reference_hz=440,
    )
    assert f"rubberband=pitch={440 / 432:.16f}:tempo=1.0" in args


@pytest.mark.audio
@pytest.mark.skipif(not has_rubberband(), reason="FFmpeg Rubber Band indisponible")
@pytest.mark.asyncio
async def test_440_hz_becomes_approximately_432_hz(tmp_path: Path) -> None:
    source = tmp_path / "tone.wav"
    target = tmp_path / "tone_432.wav"
    make_sine(source)
    settings = Settings(temp_root=tmp_path)
    info = await probe_audio(source, settings)
    output_info = await convert_audio(
        source, target, OutputFormat.WAV, info, settings, lambda _: None
    )
    assert output_info.duration == pytest.approx(info.duration, abs=0.05)
    assert dominant_frequency(target) == pytest.approx(432, abs=1.5)
