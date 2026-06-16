# app/core/logger.py
import logging
import sys

from app.core.config import settings

def setup_logging(level_name: str | None = None) -> None:
    """
    Configura el sistema de logging de la aplicación.

    Idempotente: se puede llamar varias veces sin duplicar handlers.
    Esto importa porque uvicorn puede recargar la app en modo --reload.
    """
    if level_name is None:
        level_name = settings.LOG_LEVEL
    level: int = getattr(logging, level_name)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Logger raíz "app": todos los loggers del proyecto cuelgan de él.
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    # Limpiar handlers previos para no duplicar en --reload.
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.propagate = False

    # Silenciar librerías externas muy verbosas.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Atajo para obtener loggers hijos del logger "app".

    Uso típico en cualquier módulo:
        from app.core.logger import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
