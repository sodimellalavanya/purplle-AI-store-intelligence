"""
Simple in-memory rate limiter middleware
For production, use Redis-backed rate limiting
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._store: dict = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip health checks
        if request.url.path in ("/", "/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.period

        # Clean old entries
        self._store[client_ip] = [t for t in self._store[client_ip] if t > window_start]

        if len(self._store[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.calls} requests per {self.period}s"
            )

        self._store[client_ip].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - len(self._store[client_ip]))
        return response
