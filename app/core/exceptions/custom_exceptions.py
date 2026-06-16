# app/core/exceptions/custom_exceptions.py
"""
Excepciones de dominio de la aplicación.

¿Por qué no usar HTTPException directamente en los services?
  - El service no debería saber de HTTP (es detalle del router/handler).
  - Con excepciones propias el service es testeable sin HTTP.
  - Los exception handlers traducen estas excepciones a respuestas JSON.
"""


class AppError(Exception):
    """
    Excepción base. Todas las excepciones de dominio heredan de esta.
    Permite un único handler que captura cualquier error de la app.
    """

    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str = "Error interno de la aplicación",
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class ResourceNotFoundError(AppError):
    """El recurso solicitado no existe."""

    status_code = 404
    code = "not_found"

    def __init__(
        self,
        message: str | None = None,
        resource: str | None = None,
        identifier: str | int | None = None,
    ) -> None:
        if message is None and resource is not None:
            message = f"No se encontró el {resource}"
            if identifier is not None:
                message += f" con identificador '{identifier}'"
            message += "."
        if message is None:
            message = "Recurso no encontrado."
        super().__init__(message=message)
        self.resource = resource
        self.identifier = str(identifier) if identifier is not None else None


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class DuplicateResourceError(AppError):
    """Se intentó crear un recurso que ya existe (violación de unicidad)."""

    status_code = 409
    code = "duplicate_resource"

    def __init__(
        self,
        message: str | None = None,
        resource: str | None = None,
        field: str | None = None,
        value: str | int | None = None,
    ) -> None:
        if message is None and resource is not None:
            message = f"Ya existe un {resource}"
            if field is not None:
                message += f" con {field}='{value}'"
            message += "."
        if message is None:
            message = "El recurso ya existe."
        super().__init__(message=message)
        self.resource = resource
        self.field = field
        self.value = str(value) if value is not None else None


# ── 400 Bad Request ───────────────────────────────────────────────────────────

class BusinessRuleError(AppError):
    """
    La operación viola una regla de negocio.
    Los datos pueden ser válidos pero la operación no tiene sentido
    (ej: cancelar un pedido ya entregado).
    """

    status_code = 400
    code = "business_rule_violation"

    def __init__(self, message: str = "La operación viola una regla de negocio.") -> None:
        super().__init__(message=message)


# ── 401 / 403 ─────────────────────────────────────────────────────────────────

class AuthenticationError(AppError):
    """No se pudo autenticar al usuario (token inválido, ausente o expirado)."""

    status_code = 401
    code = "authentication_error"

    def __init__(self, message: str = "No autenticado.") -> None:
        super().__init__(message=message)


class AuthorizationError(AppError):
    """El usuario está autenticado pero no tiene permisos para la operación."""

    status_code = 403
    code = "authorization_error"

    def __init__(self, message: str = "Permisos insuficientes.") -> None:
        super().__init__(message=message)
