# app/core/middleware/timing_middleware.py
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logger import get_logger

logger = get_logger("app.middleware.timing")

# Requests que superen este umbral se loguean como WARNING.
SLOW_REQUEST_THRESHOLD_MS = 500.0


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Mide el tiempo total de cada request.

    Agrega dos headers a la response:
      - Server-Timing: total;dur=<ms>   (estándar W3C, legible en DevTools)
      - X-Response-Time-ms: <ms>        (más fácil de parsear en scripts)

    Loguea como WARNING si el request supera SLOW_REQUEST_THRESHOLD_MS.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        response.headers["Server-Timing"] = (
            f'total;dur={duration_ms:.2f};desc="Total request time"'
        )
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"

        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "🐌 SLOW REQUEST: %s %s took %.1fms (threshold: %.0fms)",
                request.method,
                request.url.path,
                duration_ms,
                SLOW_REQUEST_THRESHOLD_MS,
            )

        return response
