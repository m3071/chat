import logging
import time
import uuid

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


logger = logging.getLogger("app.request")
_rate_limit_buckets: dict[str, list[float]] = {}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        if self._rate_limited(request):
            response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
            response.headers["X-Request-Id"] = request_id
            self._apply_security_headers(request, response)
            return response
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-Id"] = request_id
        self._apply_security_headers(request, response)
        logger.info(
            "%s %s -> %s %.2fms request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    def _rate_limited(self, request: Request) -> bool:
        if settings.rate_limit_per_minute <= 0 or request.method in {"GET", "HEAD", "OPTIONS"}:
            return False
        now = time.time()
        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        window_start = now - 60
        bucket = [timestamp for timestamp in _rate_limit_buckets.get(key, []) if timestamp >= window_start]
        if len(bucket) >= settings.rate_limit_per_minute:
            _rate_limit_buckets[key] = bucket
            return True
        bucket.append(now)
        _rate_limit_buckets[key] = bucket
        return False

    def _apply_security_headers(self, request: Request, response) -> None:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
