"""Manejo de sesión de usuario autenticado y control de permisos (RBAC)."""

from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional, Set
import threading

from src.core.exceptions import AuthenticationError
from src.core.logger import get_logger
from src.domain.enums import UserRole
from src.domain.models import User

logger = get_logger(__name__)

# Definición de matriz de permisos y acceso a módulos por Rol (RBAC)
ROLE_MODULE_PERMISSIONS: dict[str, Set[str]] = {
    UserRole.ADMINISTRADOR.value: {
        "dashboard",
        "flota",
        "clientes",
        "reservas",
        "contratos",
        "devoluciones",
        "mantenimientos",
        "reportes",
        "usuarios",
    },
    UserRole.GERENTE.value: {
        "dashboard",
        "flota",
        "clientes",
        "reservas",
        "contratos",
        "devoluciones",
        "mantenimientos",
        "reportes",
    },
    UserRole.AGENTE_VENTAS.value: {
        "dashboard",
        "clientes",
        "reservas",
        "contratos",
        "devoluciones",
        "flota",
    },
    UserRole.INSPECTOR_TALLER.value: {
        "dashboard",
        "flota",
        "devoluciones",
        "mantenimientos",
    },
}


class UserSession:
    """Singleton para gestionar el estado de la sesión del usuario conectado en memoria."""

    _instance: Optional["UserSession"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "UserSession":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._user = None
                cls._instance._login_time = None
                cls._instance._default_tenant_id = None
            return cls._instance

    @property
    def is_authenticated(self) -> bool:
        """Indica si existe una sesión activa y válida."""
        return self._user is not None

    @property
    def current_user(self) -> Optional[User]:
        """Retorna el usuario actualmente autenticado."""
        return self._user

    @property
    def active_tenant_id_or_none(self) -> Optional[int]:
        """Retorna el tenant_id activo en sesión (o contexto explícito) sin lanzar excepción si no hay sesión."""
        default_tid = getattr(self, "_default_tenant_id", None)
        if default_tid is not None:
            return int(default_tid)
        if self._user and getattr(self._user, "tenant_id", None) is not None:
            return int(self._user.tenant_id)
        return None

    @property
    def tenant_id(self) -> int:
        """Retorna el identificador de la agencia (tenant) activa en sesión (Fail-Fast si no hay sesión)."""
        tid = self.active_tenant_id_or_none
        if tid is not None:
            return tid
        raise AuthenticationError(
            message="Operación denegada: No existe una agencia (tenant) activa en la sesión actual.",
            code="NO_ACTIVE_TENANT",
        )

    @property
    def agency_name(self) -> str:
        """Retorna el nombre comercial de la agencia activa en sesión."""
        if self._user and getattr(self._user, "agencia_nombre", None):
            return str(self._user.agencia_nombre)
        return "Sin Agencia Activa"

    @property
    def agency_code(self) -> str:
        """Retorna el código identificador de la agencia activa en sesión."""
        if self._user and getattr(self._user, "agencia_codigo", None):
            return str(self._user.agencia_codigo)
        return "SIN-AGENCIA"

    def set_default_tenant(self, tenant_id: Optional[int]) -> None:
        """Fija o limpia el tenant explícito cuando se opera en tareas de sistema previas al login."""
        with self._lock:
            self._default_tenant_id = int(tenant_id) if tenant_id is not None else None

    @contextmanager
    def tenant_context(self, tenant_id: Optional[int]) -> Generator[None, None, None]:
        """Context manager para fijar temporalmente el tenant_id en operaciones explícitas o de login."""
        prev = getattr(self, "_default_tenant_id", None)
        self.set_default_tenant(tenant_id)
        try:
            yield
        finally:
            self.set_default_tenant(prev)

    @property
    def role_name(self) -> str:
        """Retorna el nombre del rol del usuario autenticado."""
        return self._user.rol_nombre if self._user and self._user.rol_nombre else "INVITADO"

    @property
    def login_time(self) -> Optional[datetime]:
        """Retorna la fecha y hora de inicio de sesión."""
        return self._login_time

    def login(self, user: User) -> None:
        """Establece la sesión para el usuario validado."""
        with self._lock:
            self._user = user
            self._login_time = datetime.now()
            logger.info(
                "Sesión iniciada exitosamente para '%s' (Agencia ID: %s, Rol: %s, ID: %s)",
                user.username,
                user.tenant_id,
                user.rol_nombre,
                user.id_usuario,
            )

    def logout(self) -> None:
        """Cierra la sesión actual y limpia las credenciales y agencia en memoria."""
        with self._lock:
            username = self._user.username if self._user else "Anonimo"
            self._user = None
            self._login_time = None
            self._default_tenant_id = None
            logger.info("Sesión cerrada para el usuario '%s'.", username)

    def has_permission(self, module_name: str) -> bool:
        """Verifica si el usuario en sesión tiene autorización para acceder a un módulo.

        Args:
            module_name: Identificador del módulo (ej: 'flota', 'usuarios', 'reportes')

        Returns:
            True si el rol del usuario posee permiso, False en caso contrario.
        """
        if not self.is_authenticated or not self._user or not self._user.rol_nombre:
            return False

        allowed_modules = ROLE_MODULE_PERMISSIONS.get(self._user.rol_nombre, set())
        return module_name.lower() in allowed_modules

    def has_role(self, *roles: str | UserRole) -> bool:
        """Comprueba si el usuario autenticado tiene uno de los roles especificados."""
        if not self.is_authenticated or not self._user or not self._user.rol_nombre:
            return False

        allowed_role_names = {r.value if isinstance(r, UserRole) else str(r) for r in roles}
        return self._user.rol_nombre in allowed_role_names


# Instancia global de sesión
session = UserSession()
