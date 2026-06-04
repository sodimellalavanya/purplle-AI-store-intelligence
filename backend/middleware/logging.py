"""
Request/Response logging middleware
"""
import time
import logging
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration = round((time.perf_counter() - start) * 1000, 2)

        log_data = {
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "duration_ms": duration,
            "ip": request.client.host if request.client else "unknown",
        }
        logger.info(json.dumps(log_data))
        response.headers["X-Response-Time"] = f"{duration}ms"
        return response
