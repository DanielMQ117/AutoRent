"""Repositorio ORM de acceso a datos para Devoluciones de Vehículos e Inspecciones de Retorno (SQLAlchemy 2.0)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.core.logger import get_logger
from src.database.orm_models import (
    ClienteORM,
    ContratoORM,
    DanioORM,
    DevolucionORM,
    VehiculoORM,
)
from src.domain.models import ReturnInspection
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class ReturnORMRepository(BaseORMRepository[ReturnInspection]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para recepciones físicas, odómetro y averías."""

    def create(self, return_data: ReturnInspection, conn: Any = None) -> ReturnInspection:
        """Inserta la devolución física y sus daños asociados en la base de datos.

        Args:
            return_data (ReturnInspection): Datos del acta de devolución y lista de averías.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            ReturnInspection: Entidad de dominio actualizada con los IDs generados.
        """
        tenant_id = self.current_tenant_id
        return_data.tenant_id = tenant_id
        with self.session_scope(conn) as s:
            orm_dev = DevolucionORM(
                tenant_id=tenant_id,
                id_contrato=return_data.id_contrato,
                fecha_hora_retorno_real=return_data.fecha_hora_retorno_real or datetime.now(),
                kilometraje_retorno=return_data.kilometraje_retorno,
                combustible_retorno=Decimal(str(return_data.combustible_retorno)),
                horas_retraso=return_data.horas_retraso,
                limpieza_aprobada=return_data.limpieza_aprobada,
                accesorios_completos=return_data.accesorios_completos,
                observaciones=return_data.observaciones,
                id_usuario=return_data.id_usuario,
            )
            s.add(orm_dev)
            s.flush()

            created_id = orm_dev.id_devolucion
            return_data.id_devolucion = created_id

            if return_data.danios:
                for danio in return_data.danios:
                    danio.tenant_id = tenant_id
                    danio.id_devolucion = created_id
                    orm_danio = DanioORM(
                        tenant_id=tenant_id,
                        id_devolucion=created_id,
                        zona_carroceria=danio.zona_carroceria,
                        tipo_danio=(
                            danio.tipo_danio.value
                            if hasattr(danio.tipo_danio, "value")
                            else str(danio.tipo_danio)
                        ),
                        gravedad=(
                            danio.gravedad.value
                            if hasattr(danio.gravedad, "value")
                            else str(danio.gravedad)
                        ),
                        descripcion=danio.descripcion,
                        costo_reparacion=Decimal(str(danio.costo_reparacion)),
                    )
                    s.add(orm_danio)
                    s.flush()
                    danio.id_danio = orm_danio.id_danio

            logger.info(
                "Devolución ID %s registrada para contrato ID %s con %d daños asociados.",
                created_id,
                return_data.id_contrato,
                len(return_data.danios),
            )
            return return_data

    def get_by_id(self, id_devolucion: int, conn: Any = None) -> Optional[ReturnInspection]:
        """Recupera un acta de devolución por su identificador primario con sus averías asociadas.

        Args:
            id_devolucion (int): Identificador primario de la devolución.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[ReturnInspection]: Acta de devolución con daños incluidos o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(DevolucionORM)
                .options(selectinload(DevolucionORM.danios))
                .where(
                    DevolucionORM.id_devolucion == id_devolucion,
                    DevolucionORM.tenant_id == self.current_tenant_id,
                )
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None

    def get_by_contract_id(self, id_contrato: int, conn: Any = None) -> Optional[ReturnInspection]:
        """Obtiene la devolución asociada a un contrato si ya fue recibida.

        Args:
            id_contrato (int): Identificador primario del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[ReturnInspection]: Acta de devolución del contrato o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(DevolucionORM)
                .options(selectinload(DevolucionORM.danios))
                .where(
                    DevolucionORM.id_contrato == id_contrato,
                    DevolucionORM.tenant_id == self.current_tenant_id,
                )
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None

    def list_all(
        self,
        search: str = "",
        limit: int = 100,
        conn: Any = None,
    ) -> List[ReturnInspection]:
        """Lista las actas de devolución registradas con filtros opcionales de búsqueda.

        Args:
            search (str): Término de búsqueda opcional por contrato, placa o cliente.
            limit (int): Límite máximo de registros a retornar.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[ReturnInspection]: Lista de actas de devolución con sus daños asociados.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(DevolucionORM)
                .options(selectinload(DevolucionORM.danios))
                .join(ContratoORM, DevolucionORM.id_contrato == ContratoORM.id_contrato)
                .join(ClienteORM, ContratoORM.id_cliente == ClienteORM.id_cliente)
                .join(VehiculoORM, ContratoORM.id_vehiculo == VehiculoORM.id_vehiculo)
                .where(DevolucionORM.tenant_id == self.current_tenant_id)
            )

            if search and search.strip():
                pattern = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        ContratoORM.codigo_contrato.ilike(pattern),
                        VehiculoORM.placa.ilike(pattern),
                        ClienteORM.nombres.ilike(pattern),
                        ClienteORM.apellidos.ilike(pattern),
                        ClienteORM.identificacion.ilike(pattern),
                    )
                )

            stmt = stmt.order_by(DevolucionORM.fecha_hora_retorno_real.desc()).limit(limit)
            rows = s.execute(stmt).scalars().unique().all()
            return [r.to_domain() for r in rows]

    def count_returns(self, conn: Any = None) -> int:
        """Obtiene la cantidad total de devoluciones registradas en la agencia activa.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            int: Número total de devoluciones registradas.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.count()).select_from(DevolucionORM).where(
                DevolucionORM.tenant_id == self.current_tenant_id
            )
            val = s.execute(stmt).scalar()
            return int(val or 0)
