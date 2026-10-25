"""Servicio de autenticación y control de acceso multi-tenant (Capa de Lógica de Negocio - BLL)."""

from typing import List, Optional
from src.core.exceptions import AuthenticationError, ValidationError
from src.core.security import verify_password
from src.core.session import session
from src.domain.models import Agency, User
from src.repositories.audit_repository import AuditRepository
from src.repositories.user_repository import UserRepository
from src.services.base_service import BaseService


class AuthService(BaseService):
    """Orquesta el proceso de inicio de sesión por agencia (tenant), validación de credenciales y cierre de sesión."""

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

    @staticmethod
    def _attempt_key(username: str, tenant_id: int) -> str:
        return f"{int(tenant_id)}:{username.strip().lower()}"

    def list_agencies(self, only_active: bool = True) -> List[Agency]:
        """Retorna el listado de agencias disponibles para iniciar sesión."""
        return self.user_repo.list_agencies(only_active=only_active)

    def get_failed_attempts(self, username: str, tenant_id: int) -> int:
        """Retorna el número acumulado de intentos fallidos para un usuario en una agencia."""
        return self._failed_attempts.get(self._attempt_key(username, tenant_id), 0)

    def increment_failed_attempts(self, username: str, tenant_id: int) -> int:
        """Incrementa y retorna el número de intentos fallidos para un usuario en una agencia."""
        key = self._attempt_key(username, tenant_id)
        self._failed_attempts[key] = self._failed_attempts.get(key, 0) + 1
        return self._failed_attempts[key]

    def reset_failed_attempts(self, username: str, tenant_id: int) -> None:
        """Reinicia el contador de intentos fallidos."""
        key = self._attempt_key(username, tenant_id)
        self._failed_attempts.pop(key, None)

    def login(self, username: str, password: str, tenant_id: int) -> User:
        """Autentica a un usuario verificando explícitamente agencia, credenciales, estado activo y rol.

        Args:
            username: Nombre de usuario proporcionado.
            password: Password en texto plano ingresado por el usuario.
            tenant_id: Identificador obligatorio de la agencia (tenant) donde inicia sesión.

        Returns:
            Instancia del Usuario autenticado con su rol y agencia asignados.

        Raises:
            ValidationError: Si los campos están vacíos o no se especificó agencia válida.
            AuthenticationError: Si la agencia o el usuario no existen, están deshabilitados o la contraseña es inválida.
        """
        # 1. Validaciones iniciales de entrada (Fail-Fast)
        self.validate_required("Nombre de usuario", username)
        self.validate_required("Contraseña", password)
        self.validate_positive("Agencia / Sucursal", tenant_id)

        clean_username = username.strip()
        target_tenant = int(tenant_id)

        self.logger.info(
            "Intento de inicio de sesión para el usuario: '%s' en Agencia ID: %s",
            clean_username,
            target_tenant,
        )

        # 2. Verificar existencia y estado activo de la Agencia (Tenant)
        agency = self.user_repo.get_agency_by_id(target_tenant)
        if agency is None:
            self.logger.warning("Fallo de autenticación: Agencia inexistente ID %s", target_tenant)
            raise AuthenticationError(
                message="La agencia o sucursal seleccionada no existe.",
                code="TENANT_NOT_FOUND",
            )
        if not agency.activo:
            self.logger.warning("Fallo de autenticación: Agencia deshabilitada ID %s", target_tenant)
            raise AuthenticationError(
                message="La agencia o sucursal seleccionada se encuentra inhabilitada temporalmente.",
                code="TENANT_DISABLED",
            )

        # 3. Consultar usuario en persistencia filtrado por agencia (tenant_id)
        user = self.user_repo.get_by_username(clean_username, tenant_id=target_tenant)

        if user is None:
            self.logger.warning(
                "Fallo de autenticación: Usuario inexistente '%s' en agencia ID %s",
                clean_username,
                target_tenant,
            )
            raise AuthenticationError(
                message="El usuario ingresado no existe en la agencia seleccionada.",
                code="USER_NOT_FOUND",
            )

        # 4. Verificar estado de habilitación
        if not user.activo:
            self.logger.warning("Fallo de autenticación: Usuario deshabilitado '%s'", clean_username)
            raise AuthenticationError(
                message="Su cuenta de usuario se encuentra deshabilitada. Contacte al Administrador.",
                code="USER_DISABLED",
            )

        # 5. Verificar contraseña con hash bcrypt
        if not verify_password(password, user.password_hash):
            self.logger.warning("Fallo de autenticación: Contraseña incorrecta para '%s'", clean_username)
            attempts = self.increment_failed_attempts(clean_username, tenant_id=target_tenant)

            if attempts >= self.MAX_FAILED_ATTEMPTS:
                # RF-03: Inhabilitar automáticamente la cuenta dentro de su agencia
                prev_default = getattr(session, "_default_tenant_id", None)
                try:
                    session.set_default_tenant(target_tenant)
                    self.user_repo.set_active_status(user.id_usuario, False)
                    self.audit_repo.record_action(
                        id_usuario=user.id_usuario,
                        username=user.username,
                        accion="BLOQUEO_AUTOMATICO_INTENTOS",
                        tabla_afectada="usuarios",
                        id_registro=user.id_usuario,
                        detalles=f"Bloqueo automático de cuenta tras {attempts} intentos fallidos consecutivos.",
                        tenant_id=target_tenant,
                    )
                finally:
                    session.set_default_tenant(prev_default)
                self.logger.error("Cuenta bloqueada por fuerza bruta: '%s' (%d intentos)", clean_username, attempts)
                raise AuthenticationError(
                    message=f"Su cuenta ha sido bloqueada tras {attempts} intentos fallidos consecutivos. Contacte al Administrador.",
                    code="ACCOUNT_LOCKED",
                )

            raise AuthenticationError(
                message=f"La contraseña ingresada es incorrecta. (Intento fallido {attempts} de {self.MAX_FAILED_ATTEMPTS})",
                code="INVALID_PASSWORD",
            )

        # 6. Éxito: Limpiar intentos fallidos e inicializar la sesión global en memoria con el tenant activo
        self.reset_failed_attempts(clean_username, tenant_id=target_tenant)
        session.login(user)

        # Registrar evento de inicio de sesión en bitácora de auditoría (RF-05)
        try:
            self.audit_repo.record_action(
                id_usuario=user.id_usuario,
                username=user.username,
                accion="LOGIN_EXITOSO",
                tabla_afectada="usuarios",
                id_registro=user.id_usuario,
                detalles=f"Inicio de sesión exitoso en agencia '{session.agency_code}' con rol '{user.rol_nombre}'.",
                tenant_id=target_tenant,
            )
        except Exception as e:
            self.logger.warning("No se pudo registrar log de auditoría para login: %s", e)

        self.logger.info(
            "Inicio de sesión exitoso para '%s' en agencia '%s' con rol '%s'",
            user.username,
            session.agency_code,
            user.rol_nombre,
        )
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
