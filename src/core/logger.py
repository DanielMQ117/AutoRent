"""Sistema centralizado de logging con salida a consola y archivo rotativo."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from src.config.settings import get_settings


_is_logging_configured = False


def setup_logging() -> None:
    """Configura los handlers de consola y archivo para el logger raíz."""
    global _is_logging_configured
    if _is_logging_configured:
        return

    settings = get_settings()
    log_level = getattr(logging, settings.logging.level, logging.INFO)

    # Formato uniforme para trazabilidad técnica
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Logger raíz de la aplicación
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Limpiar handlers previos para evitar duplicación
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. Handler para Consola (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Handler para Archivo Rotativo (5 MB por archivo, hasta 5 respaldos)
    try:
        file_handler = RotatingFileHandler(
            filename=settings.logging.log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        console_handler.handle(
            logging.LogRecord(
                name="logger_setup",
                level=logging.WARNING,
                pathname=__file__,
                lineno=50,
                msg=f"No se pudo inicializar el archivo de log en {settings.logging.log_path}: {e}",
                args=(),
                exc_info=None,
            )
        )

    _is_logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger nombrado garantizando que el sistema de logs esté inicializado."""
    if not _is_logging_configured:
        setup_logging()
    return logging.getLogger(name)
