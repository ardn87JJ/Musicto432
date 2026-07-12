import re
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, limit_per_minute: int) -> None:
        super().__init__(app)
        self.limit = limit_per_minute
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        is_job_status_poll = request.method == "GET" and re.fullmatch(
            r"/api/jobs/[0-9a-f]{32}", request.url.path
        )
        if request.url.path in {"/api/health", "/api/capabilities"} or is_job_status_poll:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self.requests[client]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Réessayez dans une minute."},
                headers={"Retry-After": "60"},
            )
        bucket.append(now)
        return await call_next(request)
