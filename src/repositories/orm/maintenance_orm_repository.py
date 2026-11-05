"""Repositorio ORM de acceso a datos para Mantenimiento de Flota y Taller Mecánico (SQLAlchemy 2.0)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, or_, select

from src.core.logger import get_logger
from src.database.orm_models import (
    MantenimientoORM,
    MarcaORM,
    ModeloORM,
    VehiculoORM,
)
from src.domain.models import Maintenance
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class MaintenanceORMRepository(BaseORMRepository[Maintenance]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para órdenes de taller preventivo y correctivo."""

    def create(self, maintenance: Maintenance, conn: Any = None) -> Maintenance:
        """Inserta una nueva orden de servicio en taller en la base de datos.

        Args:
            maintenance (Maintenance): Entidad de dominio con los datos de la orden de taller.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Maintenance: Entidad de dominio actualizada con ``id_mantenimiento`` y ``tenant_id``.
        """
        tenant_id = self.current_tenant_id
        maintenance.tenant_id = tenant_id
        with self.session_scope(conn) as s:
            orm_maint = MantenimientoORM(
                tenant_id=tenant_id,
                id_vehiculo=maintenance.id_vehiculo,
                tipo_mantenimiento=(
                    maintenance.tipo_mantenimiento.value
                    if hasattr(maintenance.tipo_mantenimiento, "value")
                    else str(maintenance.tipo_mantenimiento)
                ),
                fecha_ingreso=maintenance.fecha_ingreso or datetime.now(),
                fecha_salida_estimada=maintenance.fecha_salida_estimada or date.today(),
                kilometraje_entrada=maintenance.kilometraje_entrada,
                taller_servicio=maintenance.taller_servicio,
                descripcion_trabajo=maintenance.descripcion_trabajo,
                costo_total=Decimal(str(maintenance.costo_total)),
                estado=(
                    maintenance.estado.value
                    if hasattr(maintenance.estado, "value")
                    else str(maintenance.estado)
                ),
                id_usuario=maintenance.id_usuario,
            )
            s.add(orm_maint)
            s.flush()

            created_id = orm_maint.id_mantenimiento
            maintenance.id_mantenimiento = created_id
            logger.info(
                "Orden de mantenimiento ID %s registrada para vehículo ID %s (%s).",
                created_id,
                maintenance.id_vehiculo,
                maintenance.tipo_mantenimiento,
            )
            return maintenance

    def complete(
        self,
        id_mantenimiento: int,
        fecha_salida_real: datetime,
        costo_total: Decimal,
        descripcion_adicional: Optional[str] = None,
        conn: Any = None,
    ) -> bool:
        """Marca una orden de mantenimiento como FINALIZADA con fecha real y costo total auditado.

        Args:
            id_mantenimiento (int): Identificador primario de la orden de mantenimiento.
            fecha_salida_real (datetime): Fecha y hora real de salida de taller.
            costo_total (Decimal): Costo económico final del servicio.
            descripcion_adicional (Optional[str]): Detalle adicional de los trabajos realizados.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si la orden fue actualizada exitosamente, ``False`` si no existe.
        """
        with self.session_scope(conn) as s:
            stmt = select(MantenimientoORM).where(
                MantenimientoORM.id_mantenimiento == id_mantenimiento,
                MantenimientoORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            if not orm_obj:
                return False

            orm_obj.estado = "FINALIZADO"
            orm_obj.fecha_salida_real = fecha_salida_real
            orm_obj.costo_total = Decimal(str(costo_total))
            if descripcion_adicional and descripcion_adicional.strip():
                orm_obj.descripcion_trabajo = (
                    f"{orm_obj.descripcion_trabajo} | Trabajos finales: {descripcion_adicional}"
                )
            s.flush()
            return True

    def cancel(
        self, id_mantenimiento: int, motivo: Optional[str] = None, conn: Any = None
    ) -> bool:
        """Marca una orden de mantenimiento como CANCELADA.

        Args:
            id_mantenimiento (int): Identificador primario de la orden de mantenimiento.
            motivo (Optional[str]): Motivo de la cancelación de la orden.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si la orden fue cancelada, ``False`` si no existe.
        """
        with self.session_scope(conn) as s:
            stmt = select(MantenimientoORM).where(
                MantenimientoORM.id_mantenimiento == id_mantenimiento,
                MantenimientoORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            if not orm_obj:
                return False

            orm_obj.estado = "CANCELADO"
            if motivo and motivo.strip():
                orm_obj.descripcion_trabajo = (
                    f"{orm_obj.descripcion_trabajo} [Motivo cancelación: {motivo}]"
                )
            s.flush()
            return True

    def get_by_id(self, id_mantenimiento: int, conn: Any = None) -> Optional[Maintenance]:
        """Obtiene una orden de mantenimiento por su ID primario con datos relacionales completos.

        Args:
            id_mantenimiento (int): Identificador primario de la orden de mantenimiento.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Maintenance]: Orden de mantenimiento encontrada o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = select(MantenimientoORM).where(
                MantenimientoORM.id_mantenimiento == id_mantenimiento,
                MantenimientoORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None

    def get_active_by_vehicle(
        self, id_vehiculo: int, conn: Any = None
    ) -> Optional[Maintenance]:
        """Obtiene la orden activa en taller de un vehículo si existe.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Maintenance]: Orden activa en estado ``EN_TALLER`` o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(MantenimientoORM)
                .where(
                    MantenimientoORM.id_vehiculo == id_vehiculo,
                    MantenimientoORM.tenant_id == self.current_tenant_id,
                    MantenimientoORM.estado == "EN_TALLER",
                )
                .order_by(MantenimientoORM.id_mantenimiento.desc())
                .limit(1)
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None

    def list_all(
        self,
        search: str = "",
        status: Optional[str] = None,
        maintenance_type: Optional[str] = None,
        vehicle_id: Optional[int] = None,
        limit: int = 100,
        conn: Any = None,
    ) -> List[Maintenance]:
        """Lista las órdenes de mantenimiento registradas aplicando filtros opcionales.

        Args:
            search (str): Término de búsqueda por placa, marca, modelo, taller o descripción.
            status (Optional[str]): Estado de la orden (o ``TODOS``).
            maintenance_type (Optional[str]): Tipo de mantenimiento (o ``TODOS``).
            vehicle_id (Optional[int]): Filtro por identificador de vehículo.
            limit (int): Límite máximo de registros a retornar.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Maintenance]: Lista de órdenes de mantenimiento.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(MantenimientoORM)
                .join(VehiculoORM, MantenimientoORM.id_vehiculo == VehiculoORM.id_vehiculo)
                .join(ModeloORM, VehiculoORM.id_modelo == ModeloORM.id_modelo)
                .join(MarcaORM, ModeloORM.id_marca == MarcaORM.id_marca)
                .where(MantenimientoORM.tenant_id == self.current_tenant_id)
            )

            if search and search.strip():
                s_term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        VehiculoORM.placa.ilike(s_term),
                        MarcaORM.nombre.ilike(s_term),
                        ModeloORM.nombre.ilike(s_term),
                        MantenimientoORM.taller_servicio.ilike(s_term),
                        MantenimientoORM.descripcion_trabajo.ilike(s_term),
                    )
                )

            if status and status != "TODOS":
                stmt = stmt.where(MantenimientoORM.estado == status)

            if maintenance_type and maintenance_type != "TODOS":
                stmt = stmt.where(MantenimientoORM.tipo_mantenimiento == maintenance_type)

            if vehicle_id:
                stmt = stmt.where(MantenimientoORM.id_vehiculo == vehicle_id)

            stmt = stmt.order_by(MantenimientoORM.id_mantenimiento.desc()).limit(limit)
            rows = s.execute(stmt).scalars().unique().all()
            return [m.to_domain() for m in rows]

    def count_maintenances(self, status: Optional[str] = None, conn: Any = None) -> int:
        """Retorna el número total de órdenes de taller, opcionalmente filtradas por estado.

        Args:
            status (Optional[str]): Estado opcional para filtrar el conteo.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            int: Cantidad de órdenes de mantenimiento.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.count()).select_from(MantenimientoORM).where(
                MantenimientoORM.tenant_id == self.current_tenant_id
            )
            if status:
                stmt = stmt.where(MantenimientoORM.estado == status)
            val = s.execute(stmt).scalar()
            return int(val or 0)

    def get_total_expenses(self, conn: Any = None) -> Decimal:
        """Retorna la sumatoria económica invertida en mantenimiento y taller finalizado.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Decimal: Suma acumulada de costos de órdenes finalizadas.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.coalesce(func.sum(MantenimientoORM.costo_total), 0)).where(
                MantenimientoORM.tenant_id == self.current_tenant_id,
                MantenimientoORM.estado == "FINALIZADO",
            )
            val = s.execute(stmt).scalar()
            return Decimal(str(val or "0.00"))
