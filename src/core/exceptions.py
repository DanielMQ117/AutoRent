"""Jerarquía centralizada de excepciones para el dominio, persistencia y aplicación."""

from typing import Any, Optional


class AppException(Exception):
    """Excepción raíz de la aplicación."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} | Detalles: {self.details}"
        return f"[{self.code}] {self.message}"


# ============================================================================
# EXCEPCIONES DE BASE DE DATOS E INFRAESTRUCTURA
# ============================================================================

class DatabaseError(AppException):
    """Error base para operaciones en la base de datos."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Error al intentar conectar con PostgreSQL o al obtener una conexión del pool."""
    pass


class RecordNotFoundError(DatabaseError):
    """Se lanza cuando un registro solicitado no existe en la base de datos."""
    pass


class DuplicateRecordError(DatabaseError):
    """Se lanza ante una violación de restricción UNIQUE (registro duplicado)."""
    pass


class ForeignKeyViolationError(DatabaseError):
    """Se lanza ante una violación de restricción de clave foránea."""
    pass


class ExclusionViolationError(DatabaseError):
    """Se lanza ante solapamiento temporal de vehículos (overbooking GiST)."""
    pass


# ============================================================================
# EXCEPCIONES DE DOMINIO Y REGLAS DE NEGOCIO
# ============================================================================

class DomainError(AppException):
    """Error base para reglas del dominio del negocio."""
    pass


class ValidationError(DomainError):
    """Error de validación de datos de entrada o estado de campos."""
    pass


class BusinessRuleViolationError(DomainError):
    """Error producido al infringir una regla de negocio del sistema (RN-xxx)."""
    pass


class InvalidStateTransitionError(DomainError):
    """Error al intentar una transición no permitida en la máquina de estados."""
    pass


class AuthenticationError(DomainError):
    """Error al verificar credenciales de usuario."""
    pass


class AuthorizationError(DomainError):
    """Error por falta de permisos o rol insuficiente para una acción."""
    pass
