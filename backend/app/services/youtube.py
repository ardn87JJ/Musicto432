import asyncio
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

from app.config import Settings

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


class YouTubeImportError(ValueError):
    pass


async def validate_youtube_url(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise YouTubeImportError("L’URL YouTube est invalide.") from exc
    host = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme != "https" or host not in YOUTUBE_HOSTS or port not in (None, 443):
        raise YouTubeImportError("Seules les URL HTTPS youtube.com et youtu.be sont acceptées.")
    if parsed.username or parsed.password:
        raise YouTubeImportError("L’URL ne doit pas contenir d’identifiants.")
    loop = asyncio.get_running_loop()
    try:
        addresses = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise YouTubeImportError("Le domaine YouTube n’a pas pu être vérifié.") from exc
    if not addresses:
        raise YouTubeImportError("Le domaine YouTube n’a retourné aucune adresse.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise YouTubeImportError("L’URL résout vers une adresse locale ou non publique.")
    return url.strip()


async def download_youtube_audio(
    url: str,
    directory: Path,
    settings: Settings,
) -> Path:
    output_template = str(directory / "youtube-source.%(ext)s")
    args = [
        "yt-dlp",
        "--no-playlist",
        "--no-warnings",
        "--no-progress",
        "--restrict-filenames",
        "--socket-timeout",
        "20",
        "--max-filesize",
        str(settings.max_upload_bytes),
        "--match-filter",
        f"duration <= {settings.max_audio_duration_seconds} & !is_live",
        "--format",
        "bestaudio/best",
        "--output",
        output_template,
        "--",
        url,
    ]
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(), timeout=settings.youtube_timeout_seconds
        )
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise YouTubeImportError("Le téléchargement YouTube a dépassé le délai autorisé.") from exc
    if process.returncode != 0:
        detail = stderr.decode(errors="replace").strip().splitlines()
        suffix = detail[-1][:220] if detail else "erreur inconnue"
        raise YouTubeImportError(
            f"YouTube n’a pas pu fournir la piste audio ({suffix}). Essayez un fichier local."
        )
    candidates = [
        path
        for path in directory.glob("youtube-source.*")
        if path.is_file() and not path.name.endswith((".part", ".ytdl"))
    ]
    if len(candidates) != 1:
        raise YouTubeImportError("La piste audio YouTube n’a pas été récupérée correctement.")
    source = candidates[0]
    if source.stat().st_size == 0 or source.stat().st_size > settings.max_upload_bytes:
        source.unlink(missing_ok=True)
        raise YouTubeImportError("La piste YouTube est vide ou dépasse la taille maximale.")
    return source
