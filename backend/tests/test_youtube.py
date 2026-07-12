import asyncio
import socket

import pytest

from app.services.youtube import YouTubeImportError, validate_youtube_url


@pytest.mark.asyncio
async def test_accept_public_youtube_url(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()

    async def public_dns(*args: object, **kwargs: object):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.74.206", 443))]

    monkeypatch.setattr(loop, "getaddrinfo", public_dns)
    assert await validate_youtube_url("https://youtu.be/abcdefghijk") == "https://youtu.be/abcdefghijk"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://youtube.com/watch?v=abcdefghijk",
        "https://example.com/video",
        "https://localhost/video",
        "file:///etc/passwd",
        "https://user:pass@youtube.com/video",
    ],
)
async def test_block_non_allowed_urls(url: str) -> None:
    with pytest.raises(YouTubeImportError):
        await validate_youtube_url(url)


@pytest.mark.asyncio
async def test_block_private_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()

    async def private_dns(*args: object, **kwargs: object):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr(loop, "getaddrinfo", private_dns)
    with pytest.raises(YouTubeImportError, match="locale ou non publique"):
        await validate_youtube_url("https://youtube.com/watch?v=abcdefghijk")

