"""Paquete central con utilidades base, logging, seguridad y excepciones."""

from src.core.exceptions import (
    AppException,
    DatabaseError,
    DatabaseConnectionError,
    RecordNotFoundError,
    DuplicateRecordError,
    ForeignKeyViolationError,
    ExclusionViolationError,
    DomainError,
    ValidationError,
    BusinessRuleViolationError,
    InvalidStateTransitionError,
    AuthenticationError,
    AuthorizationError,
)
from src.core.logger import get_logger, setup_logging
from src.core.security import hash_password, verify_password
from src.core.session import UserSession, session

__all__ = [
    "AppException",
    "DatabaseError",
    "DatabaseConnectionError",
    "RecordNotFoundError",
    "DuplicateRecordError",
    "ForeignKeyViolationError",
    "ExclusionViolationError",
    "DomainError",
    "ValidationError",
    "BusinessRuleViolationError",
    "InvalidStateTransitionError",
    "AuthenticationError",
    "AuthorizationError",
    "get_logger",
    "setup_logging",
    "hash_password",
    "verify_password",
    "UserSession",
    "session",
]
