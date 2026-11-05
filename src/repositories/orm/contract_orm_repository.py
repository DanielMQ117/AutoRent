"""Repositorios ORM de acceso a datos para Coberturas, Pagos y Contratos de Alquiler (SQLAlchemy 2.0)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.core.logger import get_logger
from src.database.orm_models import (
    ClienteORM,
    CoberturaSeguroORM,
    ConductorAdicionalORM,
    ContratoORM,
    PagoORM,
    VehiculoORM,
)
from src.domain.enums import ContractStatus, PaymentMethod, PaymentType
from src.domain.models import Contract, InsuranceCoverage, Payment
from src.repositories.orm.base_orm_repository import BaseORMRepository

logger = get_logger(__name__)


class CoverageORMRepository(BaseORMRepository[InsuranceCoverage]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para el catálogo de coberturas de seguro."""

    def list_all(self, conn: Any = None) -> List[InsuranceCoverage]:
        """Retorna todas las pólizas/coberturas de seguro disponibles en la agencia activa ordenadas por costo.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[InsuranceCoverage]: Lista de coberturas de seguro ordenadas por costo diario ascendente.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(CoberturaSeguroORM)
                .where(CoberturaSeguroORM.tenant_id == self.current_tenant_id)
                .order_by(CoberturaSeguroORM.costo_diario.asc())
            )
            rows = s.execute(stmt).scalars().all()
            return [c.to_domain() for c in rows]

    def get_by_id(self, id_cobertura: int, conn: Any = None) -> Optional[InsuranceCoverage]:
        """Obtiene una cobertura específica por su identificador primario dentro de la agencia activa.

        Args:
            id_cobertura (int): Identificador primario de la cobertura.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[InsuranceCoverage]: Cobertura de seguro encontrada o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = select(CoberturaSeguroORM).where(
                CoberturaSeguroORM.id_cobertura == id_cobertura,
                CoberturaSeguroORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain() if orm_obj else None


class PaymentORMRepository(BaseORMRepository[Payment]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para transacciones financieras y pagos."""

    def create(self, payment: Payment, conn: Any = None) -> Payment:
        """Inserta un nuevo pago / movimiento financiero y retorna la entidad actualizada.

        Args:
            payment (Payment): Objeto de dominio con los datos de la transacción financiera.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Payment: Entidad de dominio actualizada con ``id_pago``, ``tenant_id`` y ``fecha_hora``.
        """
        target_tenant = self.current_tenant_id
        with self.session_scope(conn) as s:
            tipo_val = (
                payment.tipo_movimiento.value
                if isinstance(payment.tipo_movimiento, PaymentType)
                else str(payment.tipo_movimiento)
            )
            metodo_val = (
                payment.metodo_pago.value
                if isinstance(payment.metodo_pago, PaymentMethod)
                else str(payment.metodo_pago)
            )
            orm_obj = PagoORM(
                tenant_id=target_tenant,
                codigo_transaccion=payment.codigo_transaccion,
                id_contrato=payment.id_contrato,
                id_reserva=payment.id_reserva,
                id_liquidacion=payment.id_liquidacion,
                tipo_movimiento=tipo_val,
                metodo_pago=metodo_val,
                monto=Decimal(str(payment.monto)),
                referencia=payment.referencia,
                id_usuario=payment.id_usuario,
            )
            s.add(orm_obj)
            s.flush()
            s.refresh(orm_obj)

            payment.id_pago = orm_obj.id_pago
            payment.tenant_id = orm_obj.tenant_id
            payment.fecha_hora = orm_obj.fecha_hora
            logger.info(
                "Pago registrado exitosamente [%s] Tipo: %s, Monto: $%s",
                payment.codigo_transaccion,
                tipo_val,
                payment.monto,
            )
            return payment

    def list_by_contract(self, id_contrato: int, conn: Any = None) -> List[Payment]:
        """Obtiene todas las transacciones financieras asociadas a un contrato específico.

        Args:
            id_contrato (int): Identificador primario del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Payment]: Lista de pagos ordenados cronológicamente.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(PagoORM)
                .where(
                    PagoORM.id_contrato == id_contrato,
                    PagoORM.tenant_id == self.current_tenant_id,
                )
                .order_by(PagoORM.fecha_hora.asc())
            )
            rows = s.execute(stmt).scalars().unique().all()
            return [p.to_domain() for p in rows]

    def list_by_reservation(self, id_reserva: int, conn: Any = None) -> List[Payment]:
        """Obtiene las transacciones asociadas a una reserva (ej. anticipo).

        Args:
            id_reserva (int): Identificador primario de la reserva.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Payment]: Lista de pagos de la reserva ordenados cronológicamente.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(PagoORM)
                .where(
                    PagoORM.id_reserva == id_reserva,
                    PagoORM.tenant_id == self.current_tenant_id,
                )
                .order_by(PagoORM.fecha_hora.asc())
            )
            rows = s.execute(stmt).scalars().unique().all()
            return [p.to_domain() for p in rows]

    def count_payments(self, conn: Any = None) -> int:
        """Retorna el número total de pagos de la agencia para generación de correlativos.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            int: Cantidad total de pagos registrados en la agencia activa.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.count()).select_from(PagoORM).where(
                PagoORM.tenant_id == self.current_tenant_id
            )
            val = s.execute(stmt).scalar()
            return int(val or 0)

    def sum_total_income(self, conn: Any = None) -> Decimal:
        """Calcula la recaudación bruta histórica acumulada por cobros de renta, anticipos y garantías.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Decimal: Suma total de ingresos positivos percibidos en la agencia activa.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.coalesce(func.sum(PagoORM.monto), 0)).where(
                PagoORM.tenant_id == self.current_tenant_id,
                PagoORM.tipo_movimiento.in_(
                    ["ANTICIPO_RESERVA", "DEPOSITO_GARANTIA", "COBRO_LIQUIDACION"]
                ),
            )
            val = s.execute(stmt).scalar()
            return Decimal(str(val or "0.00"))


class ContractORMRepository(BaseORMRepository[Contract]):
    """Operaciones de persistencia mediante SQLAlchemy 2.0 ORM para contratos, entregas y conductores."""

    def get_by_id(self, id_contrato: int, conn: Any = None) -> Optional[Contract]:
        """Obtiene un contrato por su ID primario con todos sus datos relacionales, conductores y pagos.

        Args:
            id_contrato (int): Identificador primario del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Contract]: Entidad Contract con sus colecciones cargadas o ``None``.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(ContratoORM)
                .options(
                    selectinload(ContratoORM.conductores_adicionales),
                    selectinload(ContratoORM.pagos),
                )
                .where(
                    ContratoORM.id_contrato == id_contrato,
                    ContratoORM.tenant_id == self.current_tenant_id,
                )
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain(include_collections=True) if orm_obj else None

    def get_by_codigo(self, codigo_contrato: str, conn: Any = None) -> Optional[Contract]:
        """Obtiene un contrato por su código único alfanumérico (ej. ``CTR-202609-0001``).

        Args:
            codigo_contrato (str): Código alfanumérico del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Contract]: Entidad Contract con sus colecciones cargadas o ``None``.
        """
        clean_code = codigo_contrato.strip().upper()
        with self.session_scope(conn) as s:
            stmt = (
                select(ContratoORM)
                .options(
                    selectinload(ContratoORM.conductores_adicionales),
                    selectinload(ContratoORM.pagos),
                )
                .where(
                    func.upper(ContratoORM.codigo_contrato) == clean_code,
                    ContratoORM.tenant_id == self.current_tenant_id,
                )
            )
            orm_obj = s.execute(stmt).scalars().first()
            return orm_obj.to_domain(include_collections=True) if orm_obj else None

    def get_by_reserva_id(self, id_reserva: int, conn: Any = None) -> Optional[Contract]:
        """Obtiene el contrato originado a partir de una reserva previa.

        Args:
            id_reserva (int): Identificador primario de la reserva vinculada.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Contract]: Contrato asociado a la reserva o ``None`` si no existe.
        """
        with self.session_scope(conn) as s:
            stmt = select(ContratoORM.id_contrato).where(
                ContratoORM.id_reserva == id_reserva,
                ContratoORM.tenant_id == self.current_tenant_id,
            )
            cid = s.execute(stmt).scalar()
            if not cid:
                return None
            return self.get_by_id(int(cid), conn=s)

    def list_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        conn: Any = None,
    ) -> List[Contract]:
        """Lista contratos aplicando filtros opcionales de búsqueda, estado y período.

        Args:
            search (Optional[str]): Término de búsqueda por código, cliente o placa.
            status (Optional[str]): Estado del contrato a filtrar (o ``TODOS``).
            client_id (Optional[int]): Filtro por identificador de cliente.
            vehicle_id (Optional[int]): Filtro por identificador de vehículo.
            from_date (Optional[datetime]): Inicio mínimo del contrato.
            to_date (Optional[datetime]): Fin máximo del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            List[Contract]: Lista de contratos ordenados por fecha de inicio pactada descendente.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(ContratoORM)
                .join(ClienteORM, ContratoORM.id_cliente == ClienteORM.id_cliente)
                .join(VehiculoORM, ContratoORM.id_vehiculo == VehiculoORM.id_vehiculo)
                .where(ContratoORM.tenant_id == self.current_tenant_id)
            )

            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        ContratoORM.codigo_contrato.ilike(term),
                        ClienteORM.nombres.ilike(term),
                        ClienteORM.apellidos.ilike(term),
                        ClienteORM.identificacion.ilike(term),
                        VehiculoORM.placa.ilike(term),
                    )
                )

            if status and status.strip() and status != "TODOS":
                stmt = stmt.where(ContratoORM.estado == status.strip())

            if client_id is not None:
                stmt = stmt.where(ContratoORM.id_cliente == client_id)

            if vehicle_id is not None:
                stmt = stmt.where(ContratoORM.id_vehiculo == vehicle_id)

            if from_date:
                stmt = stmt.where(ContratoORM.fecha_hora_inicio_pactada >= from_date)

            if to_date:
                stmt = stmt.where(ContratoORM.fecha_hora_fin_pactada <= to_date)

            stmt = stmt.order_by(ContratoORM.fecha_hora_inicio_pactada.desc())
            rows = s.execute(stmt).scalars().unique().all()
            return [c.to_domain(include_collections=False) for c in rows]

    def create(self, contract: Contract, conn: Any = None) -> Contract:
        """Inserta un nuevo contrato y sus conductores adicionales en PostgreSQL mediante ORM.

        Args:
            contract (Contract): Entidad de dominio Contract con sus datos y conductores adicionales.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Contract: Entidad de dominio actualizada con los IDs generados.
        """
        tenant_id = self.current_tenant_id
        contract.tenant_id = tenant_id
        with self.session_scope(conn) as s:
            orm_contract = ContratoORM(
                tenant_id=tenant_id,
                codigo_contrato=contract.codigo_contrato,
                id_reserva=contract.id_reserva,
                id_cliente=contract.id_cliente,
                id_vehiculo=contract.id_vehiculo,
                id_cobertura=contract.id_cobertura,
                fecha_hora_inicio_pactada=contract.fecha_hora_inicio_pactada,
                fecha_hora_fin_pactada=contract.fecha_hora_fin_pactada,
                fecha_hora_salida_real=contract.fecha_hora_salida_real or datetime.now(),
                kilometraje_salida=contract.kilometraje_salida,
                combustible_salida=Decimal(str(contract.combustible_salida)),
                tarifa_diaria_aplicada=Decimal(str(contract.tarifa_diaria_aplicada)),
                monto_garantia=Decimal(str(contract.monto_garantia)),
                kilometraje_ilimitado=contract.kilometraje_ilimitado,
                limite_km_diario=contract.limite_km_diario,
                costo_km_excedente=Decimal(str(contract.costo_km_excedente)),
                estado=(
                    contract.estado.value
                    if isinstance(contract.estado, ContractStatus)
                    else str(contract.estado)
                ),
                id_usuario=contract.id_usuario,
            )
            s.add(orm_contract)
            s.flush()
            s.refresh(orm_contract)

            contract.id_contrato = orm_contract.id_contrato
            contract.fecha_creacion = orm_contract.fecha_creacion

            if contract.conductores_adicionales:
                for driver in contract.conductores_adicionales:
                    driver.tenant_id = tenant_id
                    driver.id_contrato = contract.id_contrato
                    orm_driver = ConductorAdicionalORM(
                        tenant_id=tenant_id,
                        id_contrato=contract.id_contrato,
                        nombre_completo=driver.nombre_completo.strip(),
                        identificacion=driver.identificacion.strip(),
                        numero_licencia=driver.numero_licencia.strip(),
                        fecha_vencimiento_licencia=driver.fecha_vencimiento_licencia,
                    )
                    s.add(orm_driver)
                    s.flush()
                    driver.id_conductor = orm_driver.id_conductor

            logger.info(
                "Contrato '%s' registrado exitosamente con ID %s",
                contract.codigo_contrato,
                contract.id_contrato,
            )
            return contract

    def update_status(
        self, id_contrato: int, status: ContractStatus, conn: Any = None
    ) -> bool:
        """Actualiza el estado operativo de un contrato.

        Args:
            id_contrato (int): Identificador primario del contrato.
            status (ContractStatus): Nuevo estado operativo del contrato.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si el contrato fue encontrado y actualizado, ``False`` en caso contrario.
        """
        with self.session_scope(conn) as s:
            stmt = select(ContratoORM).where(
                ContratoORM.id_contrato == id_contrato,
                ContratoORM.tenant_id == self.current_tenant_id,
            )
            orm_obj = s.execute(stmt).scalars().first()
            if not orm_obj:
                return False
            orm_obj.estado = (
                status.value if isinstance(status, ContractStatus) else str(status)
            )
            s.flush()
            return True

    def check_vehicle_contract_conflict(
        self,
        id_vehiculo: int,
        start_dt: datetime,
        end_dt: datetime,
        exclude_contract_id: Optional[int] = None,
        conn: Any = None,
    ) -> bool:
        """Comprueba si un vehículo ya se encuentra bajo un contrato activo en el rango indicado.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            start_dt (datetime): Fecha/hora inicial pactada.
            end_dt (datetime): Fecha/hora final pactada.
            exclude_contract_id (Optional[int]): Contrato a excluir de la verificación.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            bool: ``True`` si existe conflicto con otro contrato vigente, ``False`` si está libre.
        """
        with self.session_scope(conn) as s:
            stmt = select(ContratoORM.id_contrato).where(
                ContratoORM.tenant_id == self.current_tenant_id,
                ContratoORM.id_vehiculo == id_vehiculo,
                ContratoORM.estado.in_(["ACTIVO", "EN_INSPECCION", "EN_LIQUIDACION"]),
                ContratoORM.fecha_hora_inicio_pactada < end_dt,
                ContratoORM.fecha_hora_fin_pactada > start_dt,
            )
            if exclude_contract_id is not None:
                stmt = stmt.where(ContratoORM.id_contrato != exclude_contract_id)

            return s.execute(stmt.limit(1)).first() is not None

    def get_active_contract_by_vehicle(
        self, id_vehiculo: int, conn: Any = None
    ) -> Optional[Contract]:
        """Retorna el contrato activo actualmente en curso para un vehículo específico.

        Args:
            id_vehiculo (int): Identificador primario del vehículo.
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            Optional[Contract]: Contrato activo en curso o ``None`` si no tiene contrato activo.
        """
        with self.session_scope(conn) as s:
            stmt = (
                select(ContratoORM.id_contrato)
                .where(
                    ContratoORM.id_vehiculo == id_vehiculo,
                    ContratoORM.tenant_id == self.current_tenant_id,
                    ContratoORM.estado == "ACTIVO",
                )
                .limit(1)
            )
            cid = s.execute(stmt).scalar()
            if not cid:
                return None
            return self.get_by_id(int(cid), conn=s)

    def count_contracts(self, conn: Any = None) -> int:
        """Retorna el número total de contratos para generación del código correlativo.

        Args:
            conn (Any, optional): Sesión ORM compartida opcional.

        Returns:
            int: Cantidad total de contratos en la agencia activa.
        """
        with self.session_scope(conn) as s:
            stmt = select(func.count()).select_from(ContratoORM).where(
                ContratoORM.tenant_id == self.current_tenant_id
            )
            val = s.execute(stmt).scalar()
            return int(val or 0)
