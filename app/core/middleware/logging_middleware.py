# app/core/middleware/logging_middleware.py
import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logger import get_logger

logger = get_logger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Registra cada request y su response: método, ruta, status, duración e IP.

    Asigna un request_id único (UUID) a cada request y lo inyecta en:
      - request.state.request_id  → disponible para exception handlers.
      - Header X-Request-ID de la response → útil para correlacionar con logs.

    Nivel de log según status:
      2xx/3xx → INFO
      4xx     → WARNING
      5xx     → ERROR
    """

    # Rutas excluidas del logging (muy verbosas, poco útiles).
    EXCLUDED_PATHS: set[str] = {
        "/health",
        "/favicon.ico",
        "/openapi.json",
        "/docs",
        "/redoc",
    }

    def __init__(self, app: ASGIApp, log_body: bool = False) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        request.state.request_id = request_id

        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        logger.info(
            "→ %s %s [id=%s] from=%s ua=%s",
            request.method,
            request.url.path,
            request_id,
            self._get_client_ip(request),
            request.headers.get("user-agent", "unknown"),
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "✗ %s %s [id=%s] EXCEPTION after %.1fms: %s",
                request.method,
                request.url.path,
                request_id,
                duration_ms,
                repr(exc),
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        if response.status_code >= 500:
            log_fn = logger.error
        elif response.status_code >= 400:
            log_fn = logger.warning
        else:
            log_fn = logger.info

        log_fn(
            "← %s %s [id=%s] %d in %.1fms",
            request.method,
            request.url.path,
            request_id,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"