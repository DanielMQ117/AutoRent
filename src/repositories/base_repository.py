"""Clase base para todos los repositorios de persistencia (Capa de Acceso a Datos - DAL).

Centraliza la ejecución de consultas SQL parametrizadas y la traducción de errores
del motor PostgreSQL a excepciones tipadas de la aplicación.
"""

from abc import ABC
from typing import Any, List, Optional, TypeVar, Generic
from src.database.connection import DatabaseManager, db_manager
from src.core.exceptions import (
    DatabaseError,
    DuplicateRecordError,
    ForeignKeyViolationError,
    ExclusionViolationError,
    RecordNotFoundError,
)
from src.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Repositorio base abstracto con operaciones fundamentales y manejo de excepciones."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.db = manager or db_manager

    def _translate_db_error(self, error: Exception, context: str = "") -> Exception:
        """Traduce excepciones de bajo nivel de PostgreSQL a excepciones de dominio tipadas."""
        err_str = str(error)
        err_type = type(error).__name__

        # Detección por tipo o código de error PostgreSQL estándar
        if "UniqueViolation" in err_type or "unique constraint" in err_str.lower():
            logger.warning("Violación de restricción UNIQUE en %s: %s", context, err_str)
            return DuplicateRecordError(
                message="Ya existe un registro con los mismos datos únicos especificados.",
                details=err_str,
            )

        if "ForeignKeyViolation" in err_type or "foreign key constraint" in err_str.lower():
            logger.warning("Violación de clave foránea en %s: %s", context, err_str)
            return ForeignKeyViolationError(
                message="Operación inválida: El registro hace referencia a una entidad inexistente o está vinculado a otros registros.",
                details=err_str,
            )

        if "ExclusionViolation" in err_type or "exclusion constraint" in err_str.lower():
            logger.warning("Violación de exclusión GiST (solapamiento temporal) en %s: %s", context, err_str)
            return ExclusionViolationError(
                message="Conflicto de disponibilidad: El vehículo ya se encuentra reservado o alquilado en el rango de fechas seleccionado.",
                details=err_str,
            )

        logger.error("Error no clasificado de base de datos en %s [%s]: %s", context, err_type, err_str)
        return DatabaseError(
            message=f"Error en la operación de base de datos: {context}",
            details=err_str,
        )

    def execute_query(
        self,
        query: str,
        params: Optional[tuple | dict] = None,
        conn: Any = None,
    ) -> List[dict]:
        """Ejecuta una consulta SELECT y retorna una lista de filas mapeadas a diccionarios."""
        try:
            with self.db.cursor(conn=conn, dict_cursor=True) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            raise self._translate_db_error(e, context=f"execute_query: {query[:60]}...") from e

    def execute_query_one(
        self,
        query: str,
        params: Optional[tuple | dict] = None,
        conn: Any = None,
    ) -> Optional[dict]:
        """Ejecuta una consulta SELECT y retorna una única fila como diccionario o None."""
        try:
            with self.db.cursor(conn=conn, dict_cursor=True) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if conn is None and cur.connection and any(k in query.upper() for k in ("INSERT ", "UPDATE ", "DELETE ")):
                    cur.connection.commit()
                return dict(row) if row is not None else None
        except Exception as e:
            raise self._translate_db_error(e, context=f"execute_query_one: {query[:60]}...") from e

    def execute_non_query(
        self,
        query: str,
        params: Optional[tuple | dict] = None,
        conn: Any = None,
    ) -> int:
        """Ejecuta INSERT, UPDATE o DELETE y retorna el número de filas afectadas."""
        try:
            with self.db.cursor(conn=conn, dict_cursor=False) as cur:
                cur.execute(query, params)
                count = cur.rowcount
                if conn is None and cur.connection:
                    cur.connection.commit()
                return count
        except Exception as e:
            raise self._translate_db_error(e, context=f"execute_non_query: {query[:60]}...") from e

    def execute_scalar(
        self,
        query: str,
        params: Optional[tuple | dict] = None,
        conn: Any = None,
    ) -> Any:
        """Ejecuta una consulta agregada y retorna el valor de la primera columna de la primera fila."""
        try:
            with self.db.cursor(conn=conn, dict_cursor=False) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return row[0] if row is not None else None
        except Exception as e:
            raise self._translate_db_error(e, context=f"execute_scalar: {query[:60]}...") from e
