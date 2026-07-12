import json
import struct
from pathlib import Path

ROOT = Path(__file__).parents[2]
PUBLIC = ROOT / "frontend" / "public"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", data[16:24])


def test_manifest_and_install_icons() -> None:
    manifest = json.loads((PUBLIC / "manifest.webmanifest").read_text())
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert png_size(PUBLIC / "icons" / "icon-192.png") == (192, 192)
    assert png_size(PUBLIC / "icons" / "icon-512.png") == (512, 512)
    assert png_size(PUBLIC / "icons" / "apple-touch-icon.png") == (180, 180)


def test_service_worker_never_caches_api_or_audio_results() -> None:
    service_worker = (PUBLIC / "sw.js").read_text()
    assert "url.pathname.startsWith('/api/')" in service_worker
    assert "request.method !== 'GET'" in service_worker
    assert "musicto432-frontend-v0.5.0" in service_worker
