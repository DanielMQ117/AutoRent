"""Servicio de autenticación y control de acceso (Capa de Lógica de Negocio - BLL)."""

from typing import Optional
from src.core.exceptions import AuthenticationError, ValidationError
from src.core.security import verify_password
from src.core.session import session
from src.domain.models import User
from src.repositories.audit_repository import AuditRepository
from src.repositories.user_repository import UserRepository
from src.services.base_service import BaseService


class AuthService(BaseService):
    """Orquesta el proceso de inicio de sesión, validación de credenciales y cierre de sesión."""

    MAX_FAILED_ATTEMPTS = 3

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ) -> None:
        super().__init__()
        self.user_repo = user_repo or UserRepository(self.db)
        self.audit_repo = audit_repo or AuditRepository(self.db)
        self._failed_attempts: dict[str, int] = {}

    def get_failed_attempts(self, username: str) -> int:
        """Retorna el número acumulado de intentos fallidos para un usuario."""
        return self._failed_attempts.get(username.strip().lower(), 0)

    def increment_failed_attempts(self, username: str) -> int:
        """Incrementa y retorna el número de intentos fallidos para un usuario."""
        key = username.strip().lower()
        self._failed_attempts[key] = self._failed_attempts.get(key, 0) + 1
        return self._failed_attempts[key]

    def reset_failed_attempts(self, username: str) -> None:
        """Reinicia el contador de intentos fallidos."""
        key = username.strip().lower()
        self._failed_attempts.pop(key, None)

    def login(self, username: str, password: str) -> User:
        """Autentica a un usuario verificando credenciales, estado activo y rol.

        Args:
            username: Nombre de usuario proporcionado.
            password: Password en texto plano ingresado por el usuario.

        Returns:
            Instancia del Usuario autenticado con su rol asignado.

        Raises:
            ValidationError: Si los campos están vacíos.
            AuthenticationError: Si el usuario no existe, está deshabilitado o la contraseña es inválida.
        """
        # 1. Validaciones iniciales de entrada
        self.validate_required("Nombre de usuario", username)
        self.validate_required("Contraseña", password)

        clean_username = username.strip()

        self.logger.info("Intento de inicio de sesión para el usuario: '%s'", clean_username)

        # 2. Consultar usuario en persistencia mediante el repositorio
        user = self.user_repo.get_by_username(clean_username)

        if user is None:
            self.logger.warning("Fallo de autenticación: Usuario inexistente '%s'", clean_username)
            raise AuthenticationError(
                message="El usuario ingresado no existe en el sistema.",
                code="USER_NOT_FOUND",
            )

        # 3. Verificar estado de habilitación
        if not user.activo:
            self.logger.warning("Fallo de autenticación: Usuario deshabilitado '%s'", clean_username)
            raise AuthenticationError(
                message="Su cuenta de usuario se encuentra deshabilitada. Contacte al Administrador.",
                code="USER_DISABLED",
            )

        # 4. Verificar contraseña con hash bcrypt
        if not verify_password(password, user.password_hash):
            self.logger.warning("Fallo de autenticación: Contraseña incorrecta para '%s'", clean_username)
            attempts = self.increment_failed_attempts(clean_username)

            if attempts >= self.MAX_FAILED_ATTEMPTS:
                # RF-03: Inhabilitar automáticamente la cuenta
                self.user_repo.set_active_status(user.id_usuario, False)
                self.audit_repo.record_action(
                    id_usuario=user.id_usuario,
                    username=user.username,
                    accion="BLOQUEO_AUTOMATICO_INTENTOS",
                    tabla_afectada="usuarios",
                    id_registro=user.id_usuario,
                    detalles=f"Bloqueo automático de cuenta tras {attempts} intentos fallidos consecutivos.",
                )
                self.logger.error("Cuenta bloqueada por fuerza bruta: '%s' (%d intentos)", clean_username, attempts)
                raise AuthenticationError(
                    message=f"Su cuenta ha sido bloqueada tras {attempts} intentos fallidos consecutivos. Contacte al Administrador.",
                    code="ACCOUNT_LOCKED",
                )

            raise AuthenticationError(
                message=f"La contraseña ingresada es incorrecta. (Intento fallido {attempts} de {self.MAX_FAILED_ATTEMPTS})",
                code="INVALID_PASSWORD",
            )

        # 5. Éxito: Limpiar intentos fallidos e inicializar la sesión global en memoria
        self.reset_failed_attempts(clean_username)
        session.login(user)

        # Registrar evento de inicio de sesión en bitácora de auditoría (RF-05)
        try:
            self.audit_repo.record_action(
                id_usuario=user.id_usuario,
                username=user.username,
                accion="LOGIN_EXITOSO",
                tabla_afectada="usuarios",
                id_registro=user.id_usuario,
                detalles=f"Inicio de sesión exitoso con rol '{user.rol_nombre}'.",
            )
        except Exception as e:
            self.logger.warning("No se pudo registrar log de auditoría para login: %s", e)

        self.logger.info("Inicio de sesión exitoso para '%s' con rol '%s'", user.username, user.rol_nombre)
        return user

    def logout(self) -> None:
        """Finaliza la sesión del usuario actual."""
        user = session.current_user
        if user:
            try:
                self.audit_repo.record_action(
                    id_usuario=user.id_usuario,
                    username=user.username,
                    accion="LOGOUT",
                    tabla_afectada="usuarios",
                    id_registro=user.id_usuario,
                    detalles="Cierre voluntario de sesión.",
                )
            except Exception as e:
                self.logger.warning("No se pudo registrar log de auditoría para logout: %s", e)
        session.logout()

    def get_current_user(self) -> Optional[User]:
        """Retorna el usuario actualmente en sesión."""
        return session.current_user

    def is_authenticated(self) -> bool:
        """Indica si existe una sesión activa."""
        return session.is_authenticated


# Instancia reutilizable del servicio
auth_service = AuthService()
