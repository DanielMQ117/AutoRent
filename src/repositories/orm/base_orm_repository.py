"""Repositorio genérico base para acceso a datos mediante SQLAlchemy 2.0 ORM."""

from contextlib import contextmanager
from typing import Any, Generator, Generic, List, Optional, TypeVar

from sqlalchemy.orm import Session

from src.core.exceptions import (
    AppException,
    DatabaseError,
    DuplicateRecordError,
    ExclusionViolationError,
    ForeignKeyViolationError,
)
from src.core.logger import get_logger
from src.core.session import session as app_session
from src.database.connection import db_manager
from src.database.orm_base import get_orm_session

logger = get_logger(__name__)

T = TypeVar("T")


class BaseORMRepository(Generic[T]):
    """Clase base para todos los repositorios ORM basados en SQLAlchemy 2.0.

    Proporciona:
    1. Validación Fail-Fast del inquilino activo (``current_tenant_id``).
    2. Gestión unificada de sesiones transaccionales ORM compatibles con el parámetro
       ``conn`` de los servicios de negocio.
    3. Sincronización automática del contexto PostgreSQL Row Level Security (RLS).
    4. Traducción de errores SQLAlchemy/PostgreSQL a excepciones de dominio tipadas.
    """

    def __init__(self, manager: Any = None) -> None:
        """Inicializa el repositorio ORM conservando referencia opcional al gestor de base de datos.

        Args:
            manager (Any): Instancia opcional de ``DatabaseManager`` por retrocompatibilidad con servicios y pruebas.
        """
        self.db = manager or db_manager

    @property
    def current_tenant_id(self) -> int:
        """Retorna el ``tenant_id`` activo en la sesión actual (Fail-Fast).

        Raises:
            AuthenticationError: Si se intenta operar sobre una entidad multi-tenant
                sin haber establecido una agencia activa en sesión (``NO_ACTIVE_TENANT``).

        Returns:
            int: Identificador único de la agencia/sucursal activa.
        """
        return app_session.tenant_id

    @property
    def active_tenant_id_or_none(self) -> Optional[int]:
        """Retorna el ``tenant_id`` activo o ``None`` si aún no hay sesión autenticada.

        Returns:
            Optional[int]: ID del inquilino activo o ``None``.
        """
        return app_session.active_tenant_id_or_none

    def _translate_db_error(self, error: Exception, context: str = "ORM operation") -> Exception:
        """Traduce excepciones de SQLAlchemy / PostgreSQL a excepciones de dominio tipadas.

        Args:
            error (Exception): Excepción capturada durante la ejecución ORM.
            context (str): Descripción del contexto donde ocurrió la excepción.

        Returns:
            Exception: Excepción de dominio tipada (DuplicateRecordError, ForeignKeyViolationError, etc.).
        """
        if isinstance(error, AppException):
            return error

        err_str = str(error)
        err_type = type(error).__name__

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

        logger.error("Error de base de datos ORM en %s [%s]: %s", context, err_type, err_str)
        return DatabaseError(
            message=f"Error en la operación de base de datos ORM: {context}",
            details=err_str,
        )

    @contextmanager
    def session_scope(self, conn: Any = None) -> Generator[Session, None, None]:
        """Abre o reutiliza una sesión transaccional de SQLAlchemy ORM sincronizada con RLS.

        Si ``conn`` es una instancia de ``sqlalchemy.orm.Session``, reutiliza dicha sesión
        sin hacer commit ni cerrarla al salir del bloque, permitiendo transacciones compuestas.
        De lo contrario, abre una nueva sesión ORM, sincroniza ``app.current_tenant_id`` en
        PostgreSQL, ejecuta el bloque, confirma (``commit``) o revierte (``rollback``) ante error.

        Args:
            conn (Any): Sesión ORM opcional compartida o ``None``.

        Yields:
            Session: Sesión activa de SQLAlchemy 2.0.
        """
        try:
            with get_orm_session(existing_session=conn) as orm_session:
                yield orm_session
        except Exception as exc:
            raise self._translate_db_error(exc, context=self.__class__.__name__) from exc

    def execute_query(
        self,
        query: str,
        params: Optional[tuple | dict] = None,
        conn: Any = None,
    ) -> List[dict]:
        """Ejecuta una consulta SELECT parametrizada de soporte y retorna una lista de diccionarios.

        Args:
            query (str): Sentencia SQL a ejecutar.
            params (Optional[tuple | dict]): Parámetros posicionales o nombrados.
            conn (Any): Conexión compartida opcional.

        Returns:
            List[dict]: Lista de filas mapeadas a diccionarios.
        """
        raw_conn = None if isinstance(conn, Session) else conn
        try:
            with self.db.cursor(conn=raw_conn, dict_cursor=True) as cur:
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
        """Ejecuta una consulta SQL parametrizada de soporte y retorna una única fila como diccionario o ``None``.

        Args:
            query (str): Sentencia SQL a ejecutar.
            params (Optional[tuple | dict]): Parámetros posicionales o nombrados.
            conn (Any): Conexión compartida opcional.

        Returns:
            Optional[dict]: Diccionario con la fila resultante o ``None``.
        """
        raw_conn = None if isinstance(conn, Session) else conn
        try:
            with self.db.cursor(conn=raw_conn, dict_cursor=True) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if (
                    raw_conn is None
                    and cur.connection
                    and any(k in query.upper() for k in ("INSERT ", "UPDATE ", "DELETE "))
                ):
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
        """Ejecuta una sentencia DML de soporte (INSERT, UPDATE o DELETE) y retorna las filas afectadas.

        Args:
            query (str): Sentencia DML a ejecutar.
            params (Optional[tuple | dict]): Parámetros posicionales o nombrados.
            conn (Any): Conexión compartida opcional.

        Returns:
            int: Cantidad de filas afectadas.
        """
        raw_conn = None if isinstance(conn, Session) else conn
        try:
            with self.db.cursor(conn=raw_conn, dict_cursor=False) as cur:
                cur.execute(query, params)
                count = cur.rowcount
                if raw_conn is None and cur.connection:
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
        """Ejecuta una consulta escalar de soporte y retorna el primer valor de la primera fila.

        Args:
            query (str): Sentencia SQL escalar.
            params (Optional[tuple | dict]): Parámetros posicionales o nombrados.
            conn (Any): Conexión compartida opcional.

        Returns:
            Any: Valor escalar retornado o ``None``.
        """
        raw_conn = None if isinstance(conn, Session) else conn
        try:
            with self.db.cursor(conn=raw_conn, dict_cursor=False) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return row[0] if row is not None else None
        except Exception as e:
            raise self._translate_db_error(e, context=f"execute_scalar: {query[:60]}...") from e
