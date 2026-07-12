import asyncio
import contextlib
from collections.abc import Callable
from pathlib import Path

from app.config import Settings
from app.models import OutputFormat
from app.services.media import AudioInfo, MediaValidationError, probe_audio

PITCH_RATIO = 432 / 440
PITCH_CENTS = -31.76665363342928


class ConversionError(RuntimeError):
    pass


def build_ffmpeg_args(
    input_path: Path, output_path: Path, output_format: OutputFormat
) -> list[str]:
    codec_args: dict[OutputFormat, list[str]] = {
        OutputFormat.MP3: ["-c:a", "libmp3lame", "-b:a", "320k", "-id3v2_version", "3"],
        OutputFormat.WAV: ["-c:a", "pcm_s24le"],
        OutputFormat.FLAC: ["-c:a", "flac", "-compression_level", "8"],
    }
    if output_format not in codec_args:
        raise ConversionError("Format de sortie non autorisé.")
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:a:0",
        "-map_metadata",
        "0",
        "-af",
        f"rubberband=pitch={PITCH_RATIO:.16f}:tempo=1.0",
        *codec_args[output_format],
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]


async def convert_audio(
    input_path: Path,
    output_path: Path,
    output_format: OutputFormat,
    input_info: AudioInfo,
    settings: Settings,
    progress_callback: Callable[[int], None],
) -> AudioInfo:
    args = build_ffmpeg_args(input_path, output_path, output_format)
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def read_progress() -> None:
        assert process.stdout is not None
        while line := await process.stdout.readline():
            key, _, value = line.decode(errors="replace").strip().partition("=")
            if key in {"out_time_us", "out_time_ms"} and value.isdigit():
                elapsed = int(value) / 1_000_000
                progress_callback(min(99, max(1, round(elapsed / input_info.duration * 100))))

    reader = asyncio.create_task(read_progress())
    try:
        await asyncio.wait_for(process.wait(), timeout=settings.ffmpeg_timeout_seconds)
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        reader.cancel()
        output_path.unlink(missing_ok=True)
        raise
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        reader.cancel()
        raise ConversionError("La conversion audio a dépassé le délai autorisé.") from exc
    finally:
        with contextlib.suppress(asyncio.CancelledError):
            await reader

    stderr = await process.stderr.read() if process.stderr else b""
    if process.returncode != 0:
        output_path.unlink(missing_ok=True)
        detail = stderr.decode(errors="replace").strip().splitlines()
        raise ConversionError(
            "FFmpeg n’a pas pu convertir le fichier. " + (detail[-1][:220] if detail else "")
        )
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ConversionError("FFmpeg n’a produit aucun fichier exploitable.")
    try:
        output_info = await probe_audio(output_path, settings)
    except MediaValidationError as exc:
        raise ConversionError("Le fichier converti n’est pas lisible.") from exc
    tolerance = max(0.25, input_info.duration * 0.01)
    if abs(output_info.duration - input_info.duration) > tolerance:
        raise ConversionError("La durée du résultat diffère anormalement de l’original.")
    if output_info.channels != input_info.channels:
        raise ConversionError("Le nombre de canaux du résultat est incohérent.")
    progress_callback(100)
    return output_info
