"""Clase base para todos los servicios de la capa de lógica de negocio (BLL).

Provee utilidades de logging, orquestación de transacciones ACID y validaciones de dominio.
"""

from abc import ABC
from contextlib import contextmanager
from typing import Any, Generator, Optional
from src.database.connection import DatabaseManager, db_manager
from src.core.exceptions import ValidationError
from src.core.logger import get_logger


class BaseService(ABC):
    """Servicio base abstracto con soporte para transacciones y validaciones."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.db = manager or db_manager
        self.logger = get_logger(self.__class__.__name__)

    @contextmanager
    def run_in_transaction(self) -> Generator[Any, None, None]:
        """Ejecuta un conjunto de operaciones de repositorio dentro de una transacción atómica."""
        self.logger.debug("Iniciando bloque de transacción en servicio...")
        with self.db.transaction() as conn:
            yield conn
        self.logger.debug("Transacción confirmada (COMMIT) con éxito.")

    @staticmethod
    def validate_required(field_name: str, value: Any) -> None:
        """Valida que un campo obligatorio no sea nulo ni esté vacío."""
        if value is None:
            raise ValidationError(f"El campo '{field_name}' es obligatorio.", code="FIELD_REQUIRED")
        if isinstance(value, str) and not value.strip():
            raise ValidationError(f"El campo '{field_name}' no puede estar en blanco.", code="FIELD_EMPTY")

    @staticmethod
    def validate_positive(field_name: str, value: Any) -> None:
        """Valida que un valor numérico sea estrictamente mayor que cero."""
        if value is None or value <= 0:
            raise ValidationError(
                f"El valor de '{field_name}' debe ser mayor a cero.",
                code="POSITIVE_VALUE_REQUIRED",
            )
