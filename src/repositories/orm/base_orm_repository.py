"""Repositorio genérico base para acceso a datos mediante SQLAlchemy 2.0 ORM."""

from contextlib import contextmanager
from typing import Any, Generator, Generic, Optional, TypeVar

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
