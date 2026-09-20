"""Servicio de gestión de usuarios, roles, seguridad y auditoría (Fase 10 - BLL)."""

import re
from typing import Any, List, Optional
from src.core.exceptions import (
    DuplicateRecordError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.security import hash_password
from src.core.session import session
from src.domain.models import AuditLog, Role, User
from src.repositories.audit_repository import AuditRepository
from src.repositories.user_repository import UserRepository
from src.services.auth_service import auth_service
from src.services.base_service import BaseService

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,50}$")


class UserService(BaseService):
    """Lógica de negocio para la administración de usuarios, control de acceso RBAC y auditoría."""

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ) -> None:
        super().__init__()
        self.user_repo = user_repo or UserRepository(self.db)
        self.audit_repo = audit_repo or AuditRepository(self.db)

    def _get_current_actor(self) -> tuple[Optional[int], str]:
        """Retorna la tupla (id_usuario, username) del usuario que ejecuta la acción en sesión."""
        user = session.current_user
        if user:
            return user.id_usuario, user.username
        return None, "SISTEMA"

    def list_users(
        self,
        search: Optional[str] = None,
        id_rol: Optional[int] = None,
        activo: Optional[bool] = None,
    ) -> List[User]:
        """Obtiene la lista de usuarios aplicando los filtros solicitados."""
        return self.user_repo.list_all(search=search, id_rol=id_rol, activo=activo)

    def get_user_by_id(self, id_usuario: int) -> User:
        """Obtiene un usuario por su identificador único."""
        user = self.user_repo.get_by_id(id_usuario)
        if not user:
            raise RecordNotFoundError(
                message=f"No se encontró el usuario con ID {id_usuario}.",
                code="USER_NOT_FOUND",
            )
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Busca un usuario por su nombre de usuario."""
        return self.user_repo.get_by_username(username)

    def list_roles(self) -> List[Role]:
        """Retorna la lista de roles definidos en el sistema."""
        return self.user_repo.list_roles()

    def get_kpis(self) -> dict[str, int]:
        """Retorna métricas cuantitativas para el panel de usuarios."""
        return self.user_repo.count_users_kpis()

    def create_user(
        self,
        username: str,
        password: str,
        nombre_completo: str,
        email: str,
        id_rol: int,
        activo: bool = True,
    ) -> User:
        """Valida y crea una nueva cuenta de usuario en el sistema.

        Args:
            username: Nombre de usuario único (3 a 50 caracteres alfanuméricos).
            password: Contraseña en texto plano (mínimo 6 caracteres).
            nombre_completo: Nombre y apellidos del usuario.
            email: Correo electrónico válido y único.
            id_rol: Identificador de rol del sistema.
            activo: Estado inicial de habilitación.

        Returns:
            Entidad User creada con su ID primario asignado.
        """
        # 1. Validaciones de presencia y formato
        self.validate_required("Nombre de usuario", username)
        self.validate_required("Contraseña", password)
        self.validate_required("Nombre completo", nombre_completo)
        self.validate_required("Correo electrónico", email)

        clean_username = username.strip()
        clean_nombre = nombre_completo.strip()
        clean_email = email.strip().lower()

        if not USERNAME_REGEX.match(clean_username):
            raise ValidationError(
                message="El nombre de usuario debe tener entre 3 y 50 caracteres (letras, números, puntos o guiones).",
                code="INVALID_USERNAME",
            )

        if len(clean_nombre) < 3 or len(clean_nombre) > 100:
            raise ValidationError(
                message="El nombre completo debe tener entre 3 y 100 caracteres.",
                code="INVALID_NAME",
            )

        if not EMAIL_REGEX.match(clean_email):
            raise ValidationError(
                message="El formato del correo electrónico es inválido.",
                code="INVALID_EMAIL",
            )

        if len(password) < 6:
            raise ValidationError(
                message="La contraseña debe tener al menos 6 caracteres.",
                code="PASSWORD_TOO_SHORT",
            )

        # 2. Validar existencia del rol
        role = self.user_repo.get_role_by_id(id_rol)
        if not role:
            raise ValidationError(
                message=f"El rol seleccionado con ID {id_rol} no es válido.",
                code="INVALID_ROLE",
            )

        # 3. Validar unicidad de username y email
        existing_user = self.user_repo.get_by_username(clean_username)
        if existing_user:
            raise DuplicateRecordError(
                message=f"El nombre de usuario '{clean_username}' ya se encuentra registrado.",
                details="username ya existe en tabla usuarios",
            )

        existing_email = self.user_repo.get_by_email(clean_email)
        if existing_email:
            raise DuplicateRecordError(
                message=f"El correo electrónico '{clean_email}' ya está registrado con otra cuenta.",
                details="email ya existe en tabla usuarios",
            )

        # 4. Hash seguro de la contraseña con bcrypt
        pw_hash = hash_password(password)

        new_user = User(
            id_rol=id_rol,
            username=clean_username,
            password_hash=pw_hash,
            nombre_completo=clean_nombre,
            email=clean_email,
            activo=activo,
        )

        with self.run_in_transaction() as conn:
            created = self.user_repo.create(new_user, conn=conn)
            actor_id, actor_name = self._get_current_actor()
            self.audit_repo.record_action(
                id_usuario=actor_id,
                username=actor_name,
                accion="CREAR_USUARIO",
                tabla_afectada="usuarios",
                id_registro=created.id_usuario,
                detalles=f"Creación de cuenta @{created.username} ({created.nombre_completo}) con rol {role.nombre}.",
                conn=conn,
            )

        self.logger.info("Usuario creado exitosamente: @%s (ID: %d)", created.username, created.id_usuario)
        return created

    def update_user(
        self,
        id_usuario: int,
        nombre_completo: str,
        email: str,
        id_rol: int,
        activo: bool = True,
    ) -> User:
        """Actualiza los datos de perfil, rol y estado de un usuario existente.

        Aplica reglas de seguridad para proteger la cuenta de Administrador principal.
        """
        existing = self.get_user_by_id(id_usuario)

        self.validate_required("Nombre completo", nombre_completo)
        self.validate_required("Correo electrónico", email)

        clean_nombre = nombre_completo.strip()
        clean_email = email.strip().lower()

        if len(clean_nombre) < 3 or len(clean_nombre) > 100:
            raise ValidationError(
                message="El nombre completo debe tener entre 3 y 100 caracteres.",
                code="INVALID_NAME",
            )

        if not EMAIL_REGEX.match(clean_email):
            raise ValidationError(
                message="El formato del correo electrónico es inválido.",
                code="INVALID_EMAIL",
            )

        # Protección del Administrador Primario (ID 1 o username 'admin')
        is_primary_admin = existing.id_usuario == 1 or existing.username.lower() == "admin"
        if is_primary_admin:
            admin_role = self.user_repo.get_role_by_name("ADMINISTRADOR")
            if admin_role and id_rol != admin_role.id_rol:
                raise ValidationError(
                    message="No está permitido modificar el rol del Administrador principal del sistema.",
                    code="CANNOT_DOWNGRADE_ADMIN",
                )
            if not activo:
                raise ValidationError(
                    message="No se puede deshabilitar la cuenta del Administrador principal del sistema.",
                    code="CANNOT_DISABLE_ADMIN",
                )

        # Validar existencia de rol
        role = self.user_repo.get_role_by_id(id_rol)
        if not role:
            raise ValidationError(
                message=f"El rol seleccionado con ID {id_rol} no es válido.",
                code="INVALID_ROLE",
            )

        # Validar unicidad de correo excluyendo al usuario actual
        user_with_email = self.user_repo.get_by_email(clean_email)
        if user_with_email and user_with_email.id_usuario != id_usuario:
            raise DuplicateRecordError(
                message=f"El correo '{clean_email}' ya pertenece a otra cuenta de usuario.",
                details="email duplicado",
            )

        existing.nombre_completo = clean_nombre
        existing.email = clean_email
        existing.id_rol = id_rol
        existing.activo = activo

        with self.run_in_transaction() as conn:
            updated = self.user_repo.update(existing, conn=conn)
            actor_id, actor_name = self._get_current_actor()
            self.audit_repo.record_action(
                id_usuario=actor_id,
                username=actor_name,
                accion="ACTUALIZAR_USUARIO",
                tabla_afectada="usuarios",
                id_registro=updated.id_usuario,
                detalles=f"Modificación de perfil @{updated.username}: Nombre='{clean_nombre}', Rol='{role.nombre}', Activo={activo}.",
                conn=conn,
            )

        self.logger.info("Usuario ID %d actualizado correctamente.", id_usuario)
        return updated

    def toggle_active_status(self, id_usuario: int) -> bool:
        """Conmuta el estado de habilitación de un usuario (Activo <-> Inactivo)."""
        user = self.get_user_by_id(id_usuario)

        if user.id_usuario == 1 or user.username.lower() == "admin":
            raise ValidationError(
                message="La cuenta del Administrador principal no puede ser deshabilitada.",
                code="CANNOT_DISABLE_ADMIN",
            )

        new_status = not user.activo

        with self.run_in_transaction() as conn:
            self.user_repo.set_active_status(id_usuario, new_status, conn=conn)
            actor_id, actor_name = self._get_current_actor()
            self.audit_repo.record_action(
                id_usuario=actor_id,
                username=actor_name,
                accion="CAMBIO_ESTADO_USUARIO",
                tabla_afectada="usuarios",
                id_registro=id_usuario,
                detalles=f"Cuenta @{user.username} cambió de estado a {'ACTIVO' if new_status else 'INACTIVO'}.",
                conn=conn,
            )

        if new_status:
            auth_service.reset_failed_attempts(user.username)
        return new_status

    def unlock_user(self, id_usuario: int) -> bool:
        """Desbloquea una cuenta de usuario inhabilitada y reinicia sus intentos erróneos."""
        user = self.get_user_by_id(id_usuario)

        with self.run_in_transaction() as conn:
            self.user_repo.set_active_status(id_usuario, True, conn=conn)
            actor_id, actor_name = self._get_current_actor()
            self.audit_repo.record_action(
                id_usuario=actor_id,
                username=actor_name,
                accion="DESBLOQUEAR_CUENTA",
                tabla_afectada="usuarios",
                id_registro=id_usuario,
                detalles=f"Desbloqueo manual y reactivación de la cuenta @{user.username}.",
                conn=conn,
            )

        auth_service.reset_failed_attempts(user.username)
        self.logger.info("Cuenta de usuario @%s (ID %d) desbloqueada.", user.username, id_usuario)
        return True

    def reset_password(self, id_usuario: int, new_password: str) -> bool:
        """Restablece la contraseña de acceso de un usuario.

        Args:
            id_usuario: Identificador de la cuenta.
            new_password: Nueva clave en texto plano.

        Raises:
            ValidationError: Si la contraseña no cumple la longitud mínima.
        """
        user = self.get_user_by_id(id_usuario)

        self.validate_required("Nueva contraseña", new_password)
        if len(new_password) < 6:
            raise ValidationError(
                message="La nueva contraseña debe tener al menos 6 caracteres.",
                code="PASSWORD_TOO_SHORT",
            )

        new_hash = hash_password(new_password)

        with self.run_in_transaction() as conn:
            self.user_repo.update_password_hash(id_usuario, new_hash, conn=conn)
            actor_id, actor_name = self._get_current_actor()
            self.audit_repo.record_action(
                id_usuario=actor_id,
                username=actor_name,
                accion="RESETEO_PASSWORD",
                tabla_afectada="usuarios",
                id_registro=id_usuario,
                detalles=f"Restablecimiento administrativo de credenciales para @{user.username}.",
                conn=conn,
            )

        auth_service.reset_failed_attempts(user.username)
        self.logger.info("Contraseña restablecida exitosamente para @%s.", user.username)
        return True

    def delete_user(self, id_usuario: int) -> bool:
        """Elimina físicamente una cuenta de usuario si no posee historial operativo."""
        user = self.get_user_by_id(id_usuario)

        if user.id_usuario == 1 or user.username.lower() == "admin":
            raise ValidationError(
                message="No está permitido eliminar la cuenta del Administrador principal del sistema.",
                code="CANNOT_DELETE_ADMIN",
            )

        current_user = session.current_user
        if current_user and current_user.id_usuario == id_usuario:
            raise ValidationError(
                message="No puede eliminar su propia cuenta mientras se encuentra en sesión activa.",
                code="CANNOT_DELETE_SELF",
            )

        if self.user_repo.has_operational_records(id_usuario):
            raise ValidationError(
                message=(
                    f"No se puede eliminar al usuario @{user.username} porque tiene registros históricos "
                    "(contratos, reservas, mantenimientos o liquidaciones) asociados. "
                    "Considere deshabilitar la cuenta para revocar el acceso."
                ),
                code="USER_HAS_RECORDS",
            )

        with self.run_in_transaction() as conn:
            actor_id, actor_name = self._get_current_actor()
            self.audit_repo.record_action(
                id_usuario=actor_id,
                username=actor_name,
                accion="ELIMINAR_USUARIO",
                tabla_afectada="usuarios",
                id_registro=id_usuario,
                detalles=f"Eliminación física del usuario @{user.username} ({user.nombre_completo}).",
                conn=conn,
            )
            self.user_repo.delete(id_usuario, conn=conn)

        auth_service.reset_failed_attempts(user.username)
        self.logger.info("Usuario @%s (ID %d) eliminado del sistema.", user.username, id_usuario)
        return True

    def get_audit_logs(
        self,
        limit: int = 150,
        accion: Optional[str] = None,
        username: Optional[str] = None,
        tabla_afectada: Optional[str] = None,
    ) -> List[AuditLog]:
        """Consulta los eventos registrados en la bitácora de auditoría."""
        return self.audit_repo.list_logs(
            limit=limit,
            accion=accion,
            username=username,
            tabla_afectada=tabla_afectada,
        )

    def record_audit(
        self,
        accion: str,
        tabla_afectada: str,
        id_registro: Optional[int] = None,
        detalles: Optional[str] = None,
    ) -> int:
        """Registra un evento operativo en la bitácora de auditoría desde cualquier flujo del sistema."""
        actor_id, actor_name = self._get_current_actor()
        return self.audit_repo.record_action(
            id_usuario=actor_id,
            username=actor_name,
            accion=accion,
            tabla_afectada=tabla_afectada,
            id_registro=id_registro,
            detalles=detalles,
        )


# Instancia reutilizable del servicio
user_service = UserService()
