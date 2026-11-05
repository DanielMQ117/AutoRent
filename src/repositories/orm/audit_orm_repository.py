"""Repositorio SQLAlchemy 2.0 ORM para la Bitácora de Auditoría Inmutable (RF-05)."""

from typing import Any, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.core.session import session
from src.database.orm_models import AuditoriaORM
from src.domain.models import AuditLog
from src.repositories.orm.base_orm_repository import BaseORMRepository


class AuditORMRepository(BaseORMRepository[AuditLog]):
    """Operaciones de persistencia inmutable mediante SQLAlchemy 2.0 ORM para auditoría y seguridad."""

    @staticmethod
    def _apply_rls_tenant(orm_session: Session, tenant_id: Optional[int]) -> None:
        """Sincroniza explícitamente ``app.current_tenant_id`` en la sesión SQLAlchemy activa.

        Args:
            orm_session (Session): Sesión activa de SQLAlchemy 2.0.
            tenant_id (Optional[int]): Identificador de la agencia o ``None``.
        """
        tid_str = str(int(tenant_id)) if tenant_id is not None else ""
        orm_session.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, false);"),
            {"tid": tid_str},
        )

    def record_action(
        self,
        id_usuario: Optional[int],
        username: str,
        accion: str,
        tabla_afectada: str,
        id_registro: Optional[int] = None,
        detalles: Optional[str] = None,
        ip_origen: str = "127.0.0.1",
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> int:
        """Inserta un nuevo registro inmutable en la bitácora de auditoría para la agencia activa.

        Args:
            id_usuario (Optional[int]): ID del usuario que ejecuta la acción o ``None``.
            username (str): Nombre de usuario actor (ej. ``admin`` o ``SISTEMA``).
            accion (str): Código o nombre de la operación auditada.
            tabla_afectada (str): Nombre de la tabla de base de datos afectada.
            id_registro (Optional[int]): ID del registro afectado si aplica.
            detalles (Optional[str]): Descripción detallada del evento.
            ip_origen (str): Dirección IP origen del cliente (por defecto ``127.0.0.1``).
            tenant_id (Optional[int]): ID de agencia explícito o ``None`` para usar sesión actual.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            int: Identificador primario ``id_auditoria`` del evento registrado.
        """
        target_tenant = tenant_id if tenant_id is not None else self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                orm_audit = AuditoriaORM(
                    tenant_id=int(target_tenant),
                    id_usuario=int(id_usuario) if id_usuario is not None else None,
                    username=username.strip(),
                    accion=accion.strip().upper(),
                    tabla_afectada=tabla_afectada.strip().lower(),
                    id_registro=int(id_registro) if id_registro is not None else None,
                    detalles=detalles,
                    ip_origen=ip_origen,
                )
                s.add(orm_audit)
                s.flush()
                return int(orm_audit.id_auditoria)

    def register_event(
        self,
        id_usuario: Optional[int],
        username: str,
        accion: str,
        tabla_afectada: str,
        id_registro: Optional[int] = None,
        detalles: Optional[str] = None,
        ip_origen: str = "127.0.0.1",
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> Optional[int]:
        """Registra un evento en la bitácora de auditoría (alias compatible de ``record_action``).

        Args:
            id_usuario (Optional[int]): ID del usuario que ejecuta la acción o ``None``.
            username (str): Nombre de usuario actor.
            accion (str): Código o nombre de la operación auditada.
            tabla_afectada (str): Nombre de la tabla de base de datos afectada.
            id_registro (Optional[int]): ID del registro afectado si aplica.
            detalles (Optional[str]): Descripción detallada del evento.
            ip_origen (str): Dirección IP origen del cliente.
            tenant_id (Optional[int]): ID de agencia explícito o ``None`` para usar sesión actual.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            Optional[int]: Identificador ``id_auditoria`` generado.
        """
        return self.record_action(
            id_usuario=id_usuario,
            username=username,
            accion=accion,
            tabla_afectada=tabla_afectada,
            id_registro=id_registro,
            detalles=detalles,
            ip_origen=ip_origen,
            tenant_id=tenant_id,
            conn=conn,
        )

    def list_logs(
        self,
        limit: int = 150,
        accion: Optional[str] = None,
        username: Optional[str] = None,
        tabla_afectada: Optional[str] = None,
        tenant_id: Optional[int] = None,
        conn: Any = None,
    ) -> List[AuditLog]:
        """Consulta los eventos de auditoría más recientes de la agencia con filtros opcionales.

        Args:
            limit (int): Cantidad máxima de registros a retornar (por defecto 150).
            accion (Optional[str]): Filtro exacto por tipo de acción.
            username (Optional[str]): Filtro parcial (ILIKE) por nombre de usuario.
            tabla_afectada (Optional[str]): Filtro exacto por nombre de tabla afectada.
            tenant_id (Optional[int]): Identificador opcional de agencia.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[AuditLog]: Lista de registros de auditoría ordenados del más reciente al más antiguo.
        """
        target_tenant = tenant_id if tenant_id is not None else self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                stmt = select(AuditoriaORM).where(
                    AuditoriaORM.tenant_id == int(target_tenant)
                )

                if accion and accion.strip():
                    stmt = stmt.where(AuditoriaORM.accion == accion.strip().upper())

                if username and username.strip():
                    stmt = stmt.where(AuditoriaORM.username.ilike(f"%{username.strip()}%"))

                if tabla_afectada and tabla_afectada.strip():
                    stmt = stmt.where(
                        AuditoriaORM.tabla_afectada == tabla_afectada.strip().lower()
                    )

                stmt = stmt.order_by(AuditoriaORM.id_auditoria.desc()).limit(int(limit))
                rows = s.scalars(stmt).all()
                return [r.to_domain() for r in rows]

    def list_recent(self, limit: int = 100, conn: Any = None) -> List[AuditLog]:
        """Retorna los eventos más recientes de la bitácora de auditoría para la agencia activa.

        Args:
            limit (int): Límite máximo de eventos a consultar (por defecto 100).
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            List[AuditLog]: Lista de eventos de auditoría recientes.
        """
        return self.list_logs(limit=limit, conn=conn)

    def count_total_logs(
        self, tenant_id: Optional[int] = None, conn: Any = None
    ) -> int:
        """Retorna la cantidad total de eventos registrados en la bitácora de la agencia.

        Args:
            tenant_id (Optional[int]): Identificador opcional de agencia.
            conn (Any): Sesión ORM compartida opcional.

        Returns:
            int: Total de registros en la tabla ``auditoria`` para el inquilino.
        """
        target_tenant = tenant_id if tenant_id is not None else self.current_tenant_id
        with session.tenant_context(int(target_tenant)):
            with self.session_scope(conn) as s:
                self._apply_rls_tenant(s, int(target_tenant))
                stmt = (
                    select(func.count())
                    .select_from(AuditoriaORM)
                    .where(AuditoriaORM.tenant_id == int(target_tenant))
                )
                return int(s.scalar(stmt) or 0)
