"""Manejo de sesión de usuario autenticado y control de permisos (RBAC)."""

from datetime import datetime
from typing import Optional, Set
import threading

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
                cls._instance._default_tenant_id = 1
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
    def tenant_id(self) -> int:
        """Retorna el identificador de la agencia (tenant) activa en sesión."""
        if self._user and getattr(self._user, "tenant_id", None):
            return int(self._user.tenant_id)
        return getattr(self, "_default_tenant_id", 1)

    @property
    def agency_name(self) -> str:
        """Retorna el nombre comercial de la agencia activa en sesión."""
        if self._user and getattr(self._user, "agencia_nombre", None):
            return str(self._user.agencia_nombre)
        return "AutoRent Pro - Sede Central Managua"

    @property
    def agency_code(self) -> str:
        """Retorna el código identificador de la agencia activa en sesión."""
        if self._user and getattr(self._user, "agencia_codigo", None):
            return str(self._user.agencia_codigo)
        return "AUT-MGA-01"

    def set_default_tenant(self, tenant_id: int) -> None:
        """Fija el tenant por defecto cuando se opera fuera de una sesión interactiva."""
        with self._lock:
            self._default_tenant_id = int(tenant_id)

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
        """Cierra la sesión actual y limpia las credenciales en memoria."""
        with self._lock:
            username = self._user.username if self._user else "Anonimo"
            self._user = None
            self._login_time = None
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
