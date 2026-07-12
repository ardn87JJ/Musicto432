import asyncio
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class MediaValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AudioInfo:
    duration: float
    channels: int
    sample_rate: int
    format_name: str


def sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKD", Path(filename).name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    if ascii_name.lower() in ALLOWED_EXTENSIONS:
        ascii_name = f"audio{ascii_name.lower()}"
    stem = SAFE_NAME_RE.sub("-", Path(ascii_name).stem).strip("-._") or "audio"
    suffix = Path(ascii_name).suffix.lower()
    return f"{stem[:100]}{suffix}"


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        formats = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise MediaValidationError(f"Format non autorisé. Formats acceptés : {formats}.")
    return suffix


async def probe_audio(path: Path, settings: Settings) -> AudioInfo:
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_type,channels,sample_rate:format=duration,format_name",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except TimeoutError as exc:
        process.kill()
        raise MediaValidationError("L’analyse du fichier audio a expiré.") from exc
    if process.returncode != 0:
        detail = stderr.decode(errors="replace").strip()
        raise MediaValidationError(f"Le contenu n’est pas un fichier audio lisible. {detail[:180]}")
    try:
        data = json.loads(stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        channels = int(stream["channels"])
        sample_rate = int(stream["sample_rate"])
        format_name = str(data["format"]["format_name"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MediaValidationError("Aucune piste audio exploitable n’a été trouvée.") from exc
    if duration <= 0:
        raise MediaValidationError("La durée du fichier audio est invalide.")
    if duration > settings.max_audio_duration_seconds:
        raise MediaValidationError(
            "Le morceau dépasse la durée maximale de "
            f"{settings.max_audio_duration_seconds} secondes."
        )
    if channels < 1 or channels > 32 or sample_rate < 8000 or sample_rate > 768000:
        raise MediaValidationError("Les caractéristiques de la piste audio ne sont pas valides.")
    return AudioInfo(duration, channels, sample_rate, format_name)
