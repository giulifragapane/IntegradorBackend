# app/core/rate_limiter.py
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status

from app.core.config import settings


_login_failures: dict[str, list[datetime]] = {}
_register_attempts: dict[str, list[datetime]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def _prune_attempts(attempts: list[datetime]) -> list[datetime]:
    window_start = _now() - timedelta(minutes=settings.auth_rate_limit_window_minutes)
    return [attempt for attempt in attempts if attempt > window_start]


def _ensure_allowed(storage: dict[str, list[datetime]], key: str) -> None:
    attempts = _prune_attempts(storage.get(key, []))
    storage[key] = attempts

    if len(attempts) >= settings.auth_rate_limit_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Demasiados intentos. "
                f"Probá nuevamente en {settings.auth_rate_limit_window_minutes} minutos."
            ),
        )


def _add_attempt(storage: dict[str, list[datetime]], key: str) -> None:
    attempts = _prune_attempts(storage.get(key, []))
    attempts.append(_now())
    storage[key] = attempts


def _clear_attempts(storage: dict[str, list[datetime]], key: str) -> None:
    storage.pop(key, None)


def _login_key(request: Request, email: str) -> str:
    return f"{_client_ip(request)}:{email.strip().lower()}"


def _register_key(request: Request) -> str:
    return _client_ip(request)


def check_login_rate_limit(request: Request, email: str) -> None:
    _ensure_allowed(_login_failures, _login_key(request, email))


def register_login_failure(request: Request, email: str) -> None:
    _add_attempt(_login_failures, _login_key(request, email))


def clear_login_failures(request: Request, email: str) -> None:
    _clear_attempts(_login_failures, _login_key(request, email))


def check_register_rate_limit(request: Request) -> None:
    key = _register_key(request)
    _ensure_allowed(_register_attempts, key)
    _add_attempt(_register_attempts, key)
