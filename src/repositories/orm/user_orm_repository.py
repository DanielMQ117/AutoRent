"""Repositorio SQLAlchemy 2.0 ORM para la gestión de Usuarios, Roles y Agencias Multi-Tenant."""

from typing import Any, List, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from src.core.session import session
from src.database.orm_models import (
    AgenciaORM,
    ContratoORM,
    DevolucionORM,
    LiquidacionORM,
    MantenimientoORM,
    PagoORM,
    ReservaORM,
    RolORM,
    UsuarioORM,
)
from src.domain.models import Agency, Role, User
from src.repositories.orm.base_orm_repository import BaseORMRepository


class UserORMRepository(BaseORMRepository[User]):
    """Repositorio ORM para la administración y autenticación multi-tenant de usuarios, roles y sedes."""

    @staticmethod
    def _apply_rls_tenant(orm_session: Session, tenant_id: Optional[int]) -> None:
        """Sincroniza explícitamente ``app.current_tenant_id`` en la sesión SQLAlchemy activa.

        Args:
            orm_session (Session): Sesión activa de SQLAlchemy 2.0.
            tenant_id (Optional[int]): Identificador de la agencia o ``None`` para limpiar contexto.
        """
        tid_str = str(int(tenant_id)) if tenant_id is not None else ""
        orm_session.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, false);"),
            {"tid": tid_str},
        )

    def list_agencies(self, only_active: bool = True, conn: Any = None) -> List[Agency]:
        """Retorna el listado de agencias (sedes/inquilinos) registradas en el sistema.

        Args:
            only_active (bool): Si es ``True``, filtra únicamente agencias habilitadas.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[Agency]: Lista de agencias ordenadas por su identificador primario.
        """
        with self.session_scope(conn) as s:
            stmt = select(AgenciaORM)
            if only_active:
                stmt = stmt.where(AgenciaORM.activo.is_(True))
            stmt = stmt.order_by(AgenciaORM.id_agencia.asc())
            rows = s.scalars(stmt).all()
            return [r.to_domain() for r in rows]

    def get_agency_by_id(self, id_agencia: int, conn: Any = None) -> Optional[Agency]:
        """Obtiene una agencia por su identificador primario.

        Args:
            id_agencia (int): Identificador único de la agencia.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Agency]: Entidad ``Agency`` si existe, o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = select(AgenciaORM).where(AgenciaORM.id_agencia == int(id_agencia))
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_by_username(
        self,
        username: str,
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> Optional[User]:
        """Obtiene un usuario por su nombre de usuario y agencia, incluyendo rol y datos de sede.

        Si ``tenant_id`` no se especifica y no existe un inquilino activo en la sesión actual,
        itera sobre las agencias activas sincronizando el contexto RLS hasta localizar el usuario
        activo correspondiente, restaurando el contexto RLS original al finalizar.

        Args:
            username (str): Nombre de usuario a buscar (insensible a mayúsculas/minúsculas).
            tenant_id (Optional[int]): ID de la agencia donde buscar el usuario.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[User]: Entidad de dominio ``User`` si se encuentra, o ``None``.
        """
        clean_username = username.strip()
        target_tid = tenant_id if tenant_id is not None else self.active_tenant_id_or_none

        if target_tid is not None:
            with session.tenant_context(int(target_tid)):
                with self.session_scope(conn) as s:
                    self._apply_rls_tenant(s, int(target_tid))
                    stmt = select(UsuarioORM).where(
                        UsuarioORM.tenant_id == int(target_tid),
                        func.lower(UsuarioORM.username) == clean_username.lower(),
                    )
                    obj = s.scalars(stmt).first()
                    return obj.to_domain() if obj else None

        # Búsqueda multi-agencia cuando no hay tenant activo ni se especificó tenant_id
        prev_tid = self.active_tenant_id_or_none
        with self.session_scope(conn) as s:
            agency_ids = s.scalars(
                select(AgenciaORM.id_agencia)
                .where(AgenciaORM.activo.is_(True))
                .order_by(AgenciaORM.id_agencia.asc())
            ).all()
            try:
                for ag_id in agency_ids:
                    self._apply_rls_tenant(s, int(ag_id))
                    stmt = select(UsuarioORM).where(
                        UsuarioORM.tenant_id == int(ag_id),
                        func.lower(UsuarioORM.username) == clean_username.lower(),
                        UsuarioORM.activo.is_(True),
                    )
                    obj = s.scalars(stmt).first()
                    if obj is not None:
                        return obj.to_domain()
                return None
            finally:
                self._apply_rls_tenant(s, prev_tid)

    def get_by_id(
        self,
        id_usuario: int,
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> Optional[User]:
        """Obtiene un usuario por su identificador primario dentro de la agencia activa.

        Args:
            id_usuario (int): Identificador primario del usuario.
            tenant_id (Optional[int]): Identificador opcional de agencia (por defecto agencia activa).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[User]: Objeto ``User`` con datos de rol y agencia, o ``None``.
        """
        target_tenant = tenant_id if tenant_id is not None else self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                stmt = select(UsuarioORM).where(
                    UsuarioORM.id_usuario == int(id_usuario),
                    UsuarioORM.tenant_id == int(target_tenant),
                )
                obj = s.scalars(stmt).first()
                return obj.to_domain() if obj else None

    def get_by_email(
        self,
        email: str,
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> Optional[User]:
        """Obtiene un usuario por su correo electrónico dentro de la agencia activa.

        Args:
            email (str): Dirección de correo electrónico a consultar.
            tenant_id (Optional[int]): ID de agencia opcional.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[User]: Entidad ``User`` si existe, o ``None``.
        """
        target_tenant = tenant_id if tenant_id is not None else self.current_tenant_id
        clean_email = email.strip().lower()
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                stmt = select(UsuarioORM).where(
                    UsuarioORM.tenant_id == int(target_tenant),
                    func.lower(UsuarioORM.email) == clean_email,
                )
                obj = s.scalars(stmt).first()
                return obj.to_domain() if obj else None

    def list_all(
        self,
        search: Optional[str] = None,
        id_rol: Optional[int] = None,
        activo: Optional[bool] = None,
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> List[User]:
        """Lista los usuarios de la agencia activa con soporte para búsqueda y filtrado dinámico.

        Args:
            search (Optional[str]): Término de búsqueda libre sobre username, nombre o email.
            id_rol (Optional[int]): Filtro opcional por identificador de rol.
            activo (Optional[bool]): Filtro opcional por estado activo/inactivo.
            tenant_id (Optional[int]): Identificador opcional de agencia.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[User]: Lista de usuarios ordenados por ``id_usuario`` ascendente.
        """
        target_tenant = tenant_id if tenant_id is not None else self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                stmt = select(UsuarioORM).where(UsuarioORM.tenant_id == int(target_tenant))

                if search and search.strip():
                    pattern = f"%{search.strip()}%"
                    stmt = stmt.where(
                        or_(
                            UsuarioORM.username.ilike(pattern),
                            UsuarioORM.nombre_completo.ilike(pattern),
                            UsuarioORM.email.ilike(pattern),
                        )
                    )

                if id_rol is not None:
                    stmt = stmt.where(UsuarioORM.id_rol == int(id_rol))

                if activo is not None:
                    stmt = stmt.where(UsuarioORM.activo.is_(bool(activo)))

                stmt = stmt.order_by(UsuarioORM.id_usuario.asc())
                rows = s.scalars(stmt).all()
                return [r.to_domain() for r in rows]

    def create(self, user: User, conn: Any = None) -> User:
        """Inserta un nuevo usuario en la base de datos mediante ORM y retorna la entidad creada.

        Args:
            user (User): Entidad de dominio ``User`` con los datos a registrar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            User: Entidad ``User`` persistida con su ``id_usuario`` y relaciones resueltas.
        """
        target_tenant = user.tenant_id or self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                orm_user = UsuarioORM(
                    tenant_id=int(target_tenant),
                    id_rol=int(user.id_rol),
                    username=user.username.strip(),
                    password_hash=user.password_hash,
                    nombre_completo=user.nombre_completo.strip(),
                    email=user.email.strip().lower(),
                    activo=bool(user.activo),
                )
                s.add(orm_user)
                s.flush()
                s.refresh(orm_user)
                return orm_user.to_domain()

    def update(self, user: User, conn: Any = None) -> User:
        """Actualiza los datos personales, rol y estado activo de un usuario existente.

        Args:
            user (User): Entidad ``User`` con los campos modificados e ``id_usuario`` definido.
            conn (Any): Sesión ORM compartida opcional.

        Raises:
            RuntimeError: Si el usuario no existe dentro de la agencia activa.

        Returns:
            User: Entidad ``User`` actualizada.
        """
        target_tenant = user.tenant_id or self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                stmt = select(UsuarioORM).where(
                    UsuarioORM.id_usuario == int(user.id_usuario),
                    UsuarioORM.tenant_id == int(target_tenant),
                )
                orm_user = s.scalars(stmt).first()
                if orm_user is None:
                    raise RuntimeError(
                        f"Fallo al actualizar usuario ID {user.id_usuario}: Registro no encontrado."
                    )

                orm_user.nombre_completo = user.nombre_completo.strip()
                orm_user.email = user.email.strip().lower()
                orm_user.id_rol = int(user.id_rol)
                orm_user.activo = bool(user.activo)
                s.flush()
                s.refresh(orm_user)
                return orm_user.to_domain()

    def update_password_hash(
        self, id_usuario: int, password_hash: str, conn: Any = None
    ) -> bool:
        """Actualiza el hash bcrypt de la contraseña de un usuario de la agencia activa.

        Args:
            id_usuario (int): Identificador primario del usuario.
            password_hash (str): Nuevo hash de contraseña.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se actualizó el registro, ``False`` si no se encontró.
        """
        target_tenant = self.current_tenant_id
        with self.session_scope(conn) as s:
            self._apply_rls_tenant(s, int(target_tenant))
            stmt = select(UsuarioORM).where(
                UsuarioORM.id_usuario == int(id_usuario),
                UsuarioORM.tenant_id == int(target_tenant),
            )
            orm_user = s.scalars(stmt).first()
            if orm_user is None:
                return False
            orm_user.password_hash = password_hash
            s.flush()
            return True

    def update_password(
        self, id_usuario: int, new_password_hash: str, conn: Any = None
    ) -> None:
        """Actualiza el hash de contraseña de un usuario (método compatible con interfaz ORM).

        Args:
            id_usuario (int): Identificador primario del usuario.
            new_password_hash (str): Nuevo hash bcrypt de la contraseña.
            conn (Any): Sesión ORM compartida opcional.
        """
        self.update_password_hash(id_usuario, new_password_hash, conn=conn)

    def set_active_status(self, id_usuario: int, activo: bool, conn: Any = None) -> bool:
        """Habilita o deshabilita la cuenta de acceso de un usuario dentro de la agencia activa.

        Args:
            id_usuario (int): Identificador primario del usuario.
            activo (bool): Nuevo estado de habilitación (``True`` o ``False``).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si el usuario fue actualizado, ``False`` en caso contrario.
        """
        target_tenant = self.current_tenant_id
        with self.session_scope(conn) as s:
            self._apply_rls_tenant(s, int(target_tenant))
            stmt = select(UsuarioORM).where(
                UsuarioORM.id_usuario == int(id_usuario),
                UsuarioORM.tenant_id == int(target_tenant),
            )
            orm_user = s.scalars(stmt).first()
            if orm_user is None:
                return False
            orm_user.activo = bool(activo)
            s.flush()
            return True

    def delete(self, id_usuario: int, conn: Any = None) -> bool:
        """Elimina físicamente un usuario de la agencia activa si no posee referencias foráneas.

        Args:
            id_usuario (int): Identificador primario del usuario a eliminar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si se eliminó el registro, ``False`` si no existía.
        """
        target_tenant = self.current_tenant_id
        with self.session_scope(conn) as s:
            self._apply_rls_tenant(s, int(target_tenant))
            stmt = select(UsuarioORM).where(
                UsuarioORM.id_usuario == int(id_usuario),
                UsuarioORM.tenant_id == int(target_tenant),
            )
            orm_user = s.scalars(stmt).first()
            if orm_user is None:
                return False
            s.delete(orm_user)
            s.flush()
            return True

    def has_operational_records(self, id_usuario: int, conn: Any = None) -> bool:
        """Comprueba si el usuario tiene registros vinculados en módulos operativos o financieros.

        Args:
            id_usuario (int): Identificador del usuario a verificar.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si tiene historial operativo asociado, ``False`` en caso contrario.
        """
        t_id = self.current_tenant_id
        models = (
            ContratoORM,
            ReservaORM,
            DevolucionORM,
            MantenimientoORM,
            LiquidacionORM,
            PagoORM,
        )
        with self.session_scope(conn) as s:
            self._apply_rls_tenant(s, int(t_id))
            for model in models:
                stmt = (
                    select(1)
                    .where(
                        model.id_usuario == int(id_usuario),
                        model.tenant_id == int(t_id),
                    )
                    .limit(1)
                )
                if s.scalar(stmt) is not None:
                    return True
            return False

    def list_roles(self, conn: Any = None) -> List[Role]:
        """Retorna todos los roles RBAC disponibles en el catálogo global del sistema.

        Args:
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[Role]: Lista de roles ordenados por ``id_rol`` ascendente.
        """
        with self.session_scope(conn) as s:
            stmt = select(RolORM).order_by(RolORM.id_rol.asc())
            rows = s.scalars(stmt).all()
            return [r.to_domain() for r in rows]

    def get_role_by_id(self, id_rol: int, conn: Any = None) -> Optional[Role]:
        """Obtiene un rol de seguridad por su identificador primario.

        Args:
            id_rol (int): Identificador primario del rol.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Role]: Entidad ``Role`` si existe, o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = select(RolORM).where(RolORM.id_rol == int(id_rol))
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def get_role_by_name(self, nombre: str, conn: Any = None) -> Optional[Role]:
        """Obtiene un rol de seguridad por su nombre único.

        Args:
            nombre (str): Nombre del rol (ej. ``ADMINISTRADOR``).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[Role]: Entidad ``Role`` si se encuentra, o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = select(RolORM).where(func.lower(RolORM.nombre) == nombre.strip().lower())
            obj = s.scalars(stmt).first()
            return obj.to_domain() if obj else None

    def count_users_kpis(self, conn: Any = None) -> dict[str, int]:
        """Calcula indicadores agregados (total, activos, inactivos y roles) para el panel de usuarios.

        Args:
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            dict[str, int]: Diccionario con claves ``total``, ``activos``, ``inactivos`` y ``roles``.
        """
        t_id = self.current_tenant_id
        with self.session_scope(conn) as s:
            self._apply_rls_tenant(s, int(t_id))
            total = (
                s.scalar(
                    select(func.count()).select_from(UsuarioORM).where(UsuarioORM.tenant_id == int(t_id))
                )
                or 0
            )
            activos = (
                s.scalar(
                    select(func.count())
                    .select_from(UsuarioORM)
                    .where(UsuarioORM.tenant_id == int(t_id), UsuarioORM.activo.is_(True))
                )
                or 0
            )
            inactivos = (
                s.scalar(
                    select(func.count())
                    .select_from(UsuarioORM)
                    .where(UsuarioORM.tenant_id == int(t_id), UsuarioORM.activo.is_(False))
                )
                or 0
            )
            roles_count = s.scalar(select(func.count()).select_from(RolORM)) or 0
            return {
                "total": int(total),
                "activos": int(activos),
                "inactivos": int(inactivos),
                "roles": int(roles_count),
            }
