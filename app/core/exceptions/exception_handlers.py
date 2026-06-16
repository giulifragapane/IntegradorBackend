# app/core/exceptions/exception_handlers.py
"""
Handlers globales de excepciones.

Todas las respuestas de error siguen este formato JSON:
  {
    "error": {
      "code": "not_found",
      "message": "No se encontró el producto con identificador '5'.",
      "request_id": "uuid...",
      "timestamp": "2026-..."
    }
  }

El request_id permite correlacionar errores del cliente con los logs del servidor.
"""

from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions.custom_exceptions import AppError
from app.core.logger import get_logger

logger = get_logger("app.exceptions")


def _build_error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    request_id: str | None = None,
    extra: dict | None = None,
) -> JSONResponse:
    """Construye la respuesta JSON estándar para todos los errores."""
    body: dict = {
        # Campo "detail" mantenido por compatibilidad con el frontend existente.
        # El frontend puede leer error.response.data.detail igual que antes.
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    if extra:
        body["error"].update(extra)
    return JSONResponse(status_code=status_code, content=body)

def _get_request_id(request: Request) -> str | None:
    """Recupera el request_id guardado por LoggingMiddleware."""
    return getattr(request.state, "request_id", None)


# ── Handler 1: Excepciones de dominio (AppError y subclases) ──────────────────

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Captura ResourceNotFoundError, DuplicateResourceError, BusinessRuleError,
    AuthenticationError, AuthorizationError y cualquier subclase de AppError.
    """
    request_id = _get_request_id(request)

    if exc.status_code >= 500:
        logger.error(
            "[%s] AppError %d %s: %s",
            request_id, exc.status_code, exc.code, exc.message,
        )
    else:
        logger.warning(
            "[%s] AppError %d %s: %s",
            request_id, exc.status_code, exc.code, exc.message,
        )

    return _build_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
    )


# ── Handler 2: HTTPException estándar de FastAPI ──────────────────────────────

async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Override del handler por defecto de FastAPI para usar nuestro
    formato JSON consistente en lugar de {"detail": "..."}.
    """
    request_id = _get_request_id(request)
    logger.warning(
        "[%s] HTTPException %d: %s",
        request_id, exc.status_code, exc.detail,
    )

    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
    }
    code = code_map.get(exc.status_code, "http_error")

    return _build_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
    )


# ── Handler 3: Errores de validación de Pydantic (422) ───────────────────────

async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Reformatea los errores de Pydantic a algo más amigable para el frontend.
    """
    request_id = _get_request_id(request)

    errors = []
    for err in exc.errors():
        location = ".".join(str(x) for x in err.get("loc", []))
        errors.append({
            "field": location,
            "message": err.get("msg", "Error de validación"),
            "type": err.get("type", "validation_error"),
        })

    logger.info(
        "[%s] Validation error: %d campo(s) inválido(s) en %s",
        request_id, len(errors), request.url.path,
    )

    return _build_error_response(
        code="validation_error",
        message="Los datos enviados no son válidos.",
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        request_id=request_id,
        extra={"fields": errors},
    )


# ── Handler 4: Errores de SQLAlchemy ─────────────────────────────────────────

async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Captura errores de base de datos no manejados en el service.
    NO expone el mensaje original de SQLAlchemy al cliente (puede
    contener detalles del schema o queries).
    """
    request_id = _get_request_id(request)

    if isinstance(exc, IntegrityError):
        logger.warning(
            "[%s] IntegrityError en %s: %s",
            request_id, request.url.path, str(exc.orig),
        )
        return _build_error_response(
            code="duplicate_resource",
            message="La operación viola una restricción de unicidad o integridad.",
            status_code=status.HTTP_409_CONFLICT,
            request_id=request_id,
        )

    logger.error(
        "[%s] SQLAlchemyError en %s: %s",
        request_id, request.url.path, repr(exc),
        exc_info=True,
    )
    return _build_error_response(
        code="database_error",
        message="Error de base de datos. Contactá al administrador.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )


# ── Handler 5: Catch-all ──────────────────────────────────────────────────────

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Red de seguridad: captura cualquier excepción no manejada por los handlers
    anteriores. Si llegamos acá, es un bug. Loguea con stack trace completo.
    """
    request_id = _get_request_id(request)
    logger.critical(
        "[%s] UNHANDLED EXCEPTION en %s: %s",
        request_id, request.url.path, repr(exc),
        exc_info=True,
    )
    return _build_error_response(
        code="internal_error",
        message="Error interno del servidor. El equipo ha sido notificado.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )


# ── Función de registro ───────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra todos los handlers en la app. Llamar una vez en main.py.
    """
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
