import asyncio
import shutil
from pathlib import Path


async def command_available(command: str) -> bool:
    return shutil.which(command) is not None


async def rubberband_available() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-filters",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await process.communicate()
    return process.returncode == 0 and b"rubberband" in stdout


def temp_directory_accessible(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        marker = path / ".write-test"
        marker.touch(exist_ok=True)
        marker.unlink()
        return True
    except OSError:
        return False

