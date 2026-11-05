"""Repositorio ORM de acceso a datos para Liquidaciones Financieras y Cierre de Contratos (SQLAlchemy 2.0)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.core.logger import get_logger
from src.database.orm_models import (
    ClienteORM,
    ContratoORM,
    LiquidacionORM,
    VehiculoORM,
)
from src.domain.models import Settlement
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class SettlementORMRepository(BaseORMRepository[Settlement]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para liquidaciones y balances contables."""

    def create(self, settlement: Settlement, conn: Any = None) -> Settlement:
        """Inserta un registro de liquidación financiera en la base de datos.

        Args:
            settlement (Settlement): Entidad de dominio con los cálculos de cierre del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Settlement: Entidad de dominio actualizada con ``id_liquidacion`` y ``tenant_id``.
        """
        tenant_id = self.current_tenant_id
        settlement.tenant_id = tenant_id
        with self.session_scope(conn) as s:
            orm_liq = LiquidacionORM(
                tenant_id=tenant_id,
                id_contrato=settlement.id_contrato,
                id_devolucion=settlement.id_devolucion,
                fecha_liquidacion=settlement.fecha_liquidacion or datetime.now(),
                dias_facturados=settlement.dias_facturados,
                subtotal_renta=Decimal(str(settlement.subtotal_renta)),
                cargos_retraso=Decimal(str(settlement.cargos_retraso)),
                cargos_combustible=Decimal(str(settlement.cargos_combustible)),
                cargos_km_excedente=Decimal(str(settlement.cargos_km_excedente)),
                cargos_danios=Decimal(str(settlement.cargos_danios)),
                total_bruto=Decimal(str(settlement.total_bruto)),
                monto_garantia_aplicado=Decimal(str(settlement.monto_garantia_aplicado)),
                saldo_cliente=Decimal(str(settlement.saldo_cliente)),
                estado_liquidacion=(
                    settlement.estado_liquidacion.value
                    if hasattr(settlement.estado_liquidacion, "value")
                    else str(settlement.estado_liquidacion)
                ),
                id_usuario=settlement.id_usuario,
            )
            s.add(orm_liq)
            s.flush()

            created_id = orm_liq.id_liquidacion
            settlement.id_liquidacion = created_id
            logger.info(
                "Liquidación ID %s registrada para contrato ID %s (Total Bruto: $%s, Saldo: $%s).",
                created_id,
                settlement.id_contrato,
                settlement.total_bruto,
                settlement.saldo_cliente,
            )
            return settlement

    def get_by_id(self, id_liquidacion: int, conn: Any = None) -> Optional[Settlement]:
        """Recupera una liquidación por su identificador primario junto con sus pagos asociados.

        Args:
            id_liquidacion (int): Identificador primario de la liquidación.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Settlement]: Liquidación encontrada con sus pagos o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(LiquidacionORM)
                .options(selectinload(LiquidacionORM.pagos))
                .where(
                    LiquidacionORM.id_liquidacion == id_liquidacion,
                    LiquidacionORM.tenant_id == self.current_tenant_id,
                )
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain(include_payments=True) if orm_obj else None

    def get_by_contract_id(self, id_contrato: int, conn: Any = None) -> Optional[Settlement]:
        """Obtiene la liquidación asociada a un contrato específico.

        Args:
            id_contrato (int): Identificador primario del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Settlement]: Liquidación asociada al contrato o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(LiquidacionORM)
                .options(selectinload(LiquidacionORM.pagos))
                .where(
                    LiquidacionORM.id_contrato == id_contrato,
                    LiquidacionORM.tenant_id == self.current_tenant_id,
                )
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain(include_payments=True) if orm_obj else None

    def list_all(
        self,
        search: str = "",
        limit: int = 100,
        conn: Any = None,
    ) -> List[Settlement]:
        """Lista las liquidaciones registradas en el sistema para la agencia activa.

        Args:
            search (str): Término de búsqueda por código de contrato, placa o cliente.
            limit (int): Cantidad máxima de registros a retornar.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Settlement]: Lista de liquidaciones ordenadas por fecha de liquidación descendente.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(LiquidacionORM)
                .join(ContratoORM, LiquidacionORM.id_contrato == ContratoORM.id_contrato)
                .join(ClienteORM, ContratoORM.id_cliente == ClienteORM.id_cliente)
                .join(VehiculoORM, ContratoORM.id_vehiculo == VehiculoORM.id_vehiculo)
                .where(LiquidacionORM.tenant_id == self.current_tenant_id)
            )

            if search and search.strip():
                pattern = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        ContratoORM.codigo_contrato.ilike(pattern),
                        VehiculoORM.placa.ilike(pattern),
                        ClienteORM.nombres.ilike(pattern),
                        ClienteORM.apellidos.ilike(pattern),
                    )
                )

            stmt = stmt.order_by(LiquidacionORM.fecha_liquidacion.desc()).limit(limit)
            rows = s.execute(stmt).scalars().unique().all()
            return [l.to_domain(include_payments=False) for l in rows]

    def count_settlements(self, conn: Any = None) -> int:
        """Obtiene la cantidad total de liquidaciones registradas en la agencia activa.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            int: Número total de liquidaciones registradas.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.count()).select_from(LiquidacionORM).where(
                LiquidacionORM.tenant_id == self.current_tenant_id
            )
            val = s.execute(stmt).scalar()
            return int(val or 0)
