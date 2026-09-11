"""Servicio de lógica de negocio para Contratos, Formalización y Entrega de Vehículos (BLL)."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from src.core.exceptions import (
    BusinessRuleViolationError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import get_logger
from src.core.session import session
from src.domain.enums import (
    ClientStatus,
    ContractStatus,
    PaymentMethod,
    PaymentType,
    ReservationStatus,
    VehicleStatus,
)
from src.domain.models import (
    AdditionalDriver,
    Contract,
    InsuranceCoverage,
    Payment,
    Vehicle,
)
from src.repositories.client_repository import ClientRepository
from src.repositories.contract_repository import ContractRepository
from src.repositories.coverage_repository import CoverageRepository
from src.repositories.payment_repository import PaymentRepository
from src.repositories.reservation_repository import ReservationRepository
from src.repositories.vehicle_repository import VehicleRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


class ContractService(BaseService):
    """Servicio empresarial que orquesta la formalización de alquileres, contratos y entrega física."""

    def __init__(
        self,
        contract_repo: Optional[ContractRepository] = None,
        coverage_repo: Optional[CoverageRepository] = None,
        payment_repo: Optional[PaymentRepository] = None,
        vehicle_repo: Optional[VehicleRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        reservation_repo: Optional[ReservationRepository] = None,
    ) -> None:
        super().__init__()
        self.contract_repo = contract_repo or ContractRepository(self.db)
        self.coverage_repo = coverage_repo or CoverageRepository(self.db)
        self.payment_repo = payment_repo or PaymentRepository(self.db)
        self.vehicle_repo = vehicle_repo or VehicleRepository(self.db)
        self.client_repo = client_repo or ClientRepository(self.db)
        self.reservation_repo = reservation_repo or ReservationRepository(self.db)

    def _generate_contract_code(self) -> str:
        """Genera un código único correlativo para el contrato: CTR-YYYYMM-XXXX."""
        count = self.contract_repo.count_contracts() + 1
        now = datetime.now()
        return f"CTR-{now.strftime('%Y%m')}-{count:04d}"

    def _generate_payment_code(self, prefix: str = "TRX-GAR") -> str:
        """Genera un código único para transacciones de pagos o garantías."""
        count = self.payment_repo.count_payments() + 1
        now = datetime.now()
        return f"{prefix}-{now.strftime('%Y%m')}-{count:04d}"

    def calculate_quote(
        self,
        id_vehiculo: int,
        id_cobertura: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> Tuple[int, Decimal, Decimal, Decimal, Decimal]:
        """Calcula los días facturables, tarifa diaria, seguro y depósito en garantía sugerido.

        Returns:
            Tupla con (dias, tarifa_diaria, costo_seguro_diario, total_alquiler, garantia_sugerida)
        """
        if end_dt <= start_dt:
            raise ValidationError(
                "La fecha de finalización pactada debe ser posterior a la fecha de inicio.",
                code="INVALID_DATE_RANGE",
            )

        vehicle = self.vehicle_repo.get_by_id(id_vehiculo)
        if not vehicle:
            raise RecordNotFoundError(f"Vehículo con ID {id_vehiculo} no encontrado.")

        categories = self.vehicle_repo.list_categories()
        category = next((c for c in categories if c.id_categoria == vehicle.id_categoria), None)
        if not category:
            raise RecordNotFoundError("No se encontró la categoría del vehículo seleccionado.")

        coverage = self.coverage_repo.get_by_id(id_cobertura)
        if not coverage:
            raise RecordNotFoundError(f"Cobertura de seguro con ID {id_cobertura} no encontrada.")

        delta = end_dt - start_dt
        dias = delta.days
        if delta.seconds > 3600:
            dias += 1
        dias = max(1, dias)

        tarifa = category.tarifa_base_diaria
        seguro_diario = coverage.costo_diario
        total_renta = (tarifa + seguro_diario) * Decimal(dias)
        garantia_sugerida = category.deposito_garantia_sugerido

        return dias, tarifa, seguro_diario, total_renta, garantia_sugerida

    def validate_contract_rules(
        self,
        contract: Contract,
        is_update: bool = False,
    ) -> None:
        """Aplica todas las reglas de negocio e integridad para la emisión de contratos."""
        # 1. Campos obligatorios y rangos positivos
        self.validate_positive("Cliente", contract.id_cliente)
        self.validate_positive("Vehículo", contract.id_vehiculo)
        self.validate_positive("Cobertura de Seguro", contract.id_cobertura)
        self.validate_required("Fecha de Inicio Pactada", contract.fecha_hora_inicio_pactada)
        self.validate_required("Fecha de Fin Pactada", contract.fecha_hora_fin_pactada)

        start_dt = contract.fecha_hora_inicio_pactada
        end_dt = contract.fecha_hora_fin_pactada

        # 2. Coherencia cronológica de fechas
        if end_dt <= start_dt:
            raise ValidationError(
                "La fecha de culminación pactada debe ser estrictamente posterior a la fecha de inicio.",
                code="INVALID_DATE_RANGE",
            )

        # 3. Elegibilidad del Cliente (RN-001, RN-002)
        client = self.client_repo.get_by_id(contract.id_cliente)
        if not client:
            raise RecordNotFoundError(f"No se encontró el cliente con ID {contract.id_cliente}.")

        if client.estado_cliente == ClientStatus.VETADO:
            raise BusinessRuleViolationError(
                f"Operación denegada: El cliente '{client.nombre_completo}' está VETADO en el sistema.",
                code="CLIENT_BANNED",
            )

        if client.estado_cliente == ClientStatus.MOROSO:
            raise BusinessRuleViolationError(
                f"Operación denegada: El cliente '{client.nombre_completo}' presenta saldo MOROSO pendiente.",
                code="CLIENT_IN_DEBT",
            )

        if not client.licencia:
            raise BusinessRuleViolationError(
                f"El cliente '{client.nombre_completo}' no posee licencia de conducir registrada.",
                code="CLIENT_NO_LICENSE",
            )

        if client.licencia.fecha_vencimiento < end_dt.date():
            raise BusinessRuleViolationError(
                f"Licencia no válida: La licencia del cliente vence el {client.licencia.fecha_vencimiento.strftime('%d/%m/%Y')}, "
                f"antes del fin pactado del contrato ({end_dt.strftime('%d/%m/%Y')}).",
                code="EXPIRED_LICENSE_FOR_CONTRACT",
            )

        # 4. Validación de Conductores Adicionales
        for idx, driver in enumerate(contract.conductores_adicionales, start=1):
            if not driver.nombre_completo.strip():
                raise ValidationError(f"El conductor adicional #{idx} no tiene nombre completo.", code="MISSING_DRIVER_NAME")
            if not driver.numero_licencia.strip():
                raise ValidationError(f"El conductor adicional #{idx} no tiene número de licencia.", code="MISSING_DRIVER_LICENSE")
            if not driver.fecha_vencimiento_licencia:
                raise ValidationError(f"El conductor adicional #{idx} no tiene fecha de vencimiento de licencia.", code="MISSING_DRIVER_LICENSE_EXPIRY")
            if driver.fecha_vencimiento_licencia < end_dt.date():
                raise BusinessRuleViolationError(
                    f"Licencia no válida: La licencia del conductor adicional '{driver.nombre_completo}' "
                    f"vence el {driver.fecha_vencimiento_licencia.strftime('%d/%m/%Y')}, antes del fin del contrato.",
                    code="EXPIRED_ADDITIONAL_DRIVER_LICENSE",
                )

        # 5. Estado y Odómetro del Vehículo
        vehicle = self.vehicle_repo.get_by_id(contract.id_vehiculo)
        if not vehicle:
            raise RecordNotFoundError(f"Vehículo con ID {contract.id_vehiculo} no encontrado.")

        if not vehicle.activo or vehicle.estado == VehicleStatus.DE_BAJA:
            raise BusinessRuleViolationError(
                f"El vehículo con placa '{vehicle.placa}' está inactivo o dado de baja.",
                code="VEHICLE_DECOMMISSIONED",
            )

        if vehicle.estado == VehicleStatus.EN_MANTENIMIENTO:
            raise BusinessRuleViolationError(
                f"El vehículo con placa '{vehicle.placa}' está actualmente en mantenimiento.",
                code="VEHICLE_IN_MAINTENANCE",
            )

        # Si el contrato es nuevo y no proviene de reserva previa, el vehículo debe estar DISPONIBLE
        if not is_update and not contract.id_reserva:
            if vehicle.estado != VehicleStatus.DISPONIBLE:
                raise BusinessRuleViolationError(
                    f"El vehículo '{vehicle.placa}' no se encuentra disponible (Estado actual: '{vehicle.estado.value}').",
                    code="VEHICLE_NOT_AVAILABLE",
                )

        # Comprobar conflicto de contrato por solapamiento temporal
        has_conflict = self.contract_repo.check_vehicle_contract_conflict(
            id_vehiculo=contract.id_vehiculo,
            start_dt=start_dt,
            end_dt=end_dt,
            exclude_contract_id=contract.id_contrato if is_update else None,
        )
        if has_conflict:
            raise BusinessRuleViolationError(
                f"El vehículo '{vehicle.placa}' ya se encuentra comprometido en un contrato activo para las fechas solicitadas.",
                code="VEHICLE_CONTRACT_CONFLICT",
            )

        # Validación del odómetro de salida (no puede ser menor al actual)
        if contract.kilometraje_salida < vehicle.kilometraje_actual:
            raise BusinessRuleViolationError(
                f"Incoherencia de odómetro: El kilometraje de salida ({contract.kilometraje_salida} km) "
                f"no puede ser menor al kilometraje actual registrado del vehículo ({vehicle.kilometraje_actual} km).",
                code="INVALID_ODOMETER_VALUE",
            )

        # Nivel de combustible de salida
        if contract.combustible_salida < Decimal("0.00") or contract.combustible_salida > Decimal("1.00"):
            raise ValidationError(
                "El nivel de combustible de salida debe estar comprendido entre 0.00 y 1.00.",
                code="INVALID_FUEL_LEVEL",
            )

        # Tarifas y garantías
        if contract.tarifa_diaria_aplicada <= Decimal("0.00"):
            raise ValidationError("La tarifa diaria aplicada debe ser mayor a 0.", code="INVALID_DAILY_RATE")
        if contract.monto_garantia < Decimal("0.00"):
            raise ValidationError("El monto de la garantía no puede ser negativo.", code="INVALID_GUARANTEE_AMOUNT")

    def create_contract(
        self,
        contract: Contract,
        metodo_pago_garantia: PaymentMethod = PaymentMethod.EFECTIVO,
        referencia_pago_garantia: Optional[str] = None,
    ) -> Contract:
        """Emite y formaliza un nuevo contrato de alquiler, entrega el vehículo y registra la garantía.

        Ejecuta todas las operaciones en una única transacción ACID:
        1. Valida reglas de negocio.
        2. Genera código correlativo (CTR-YYYYMM-XXXX).
        3. Inserta contrato y conductores adicionales en la BD.
        4. Si viene de una reserva, la marca como CONVERTIDA_A_CONTRATO.
        5. Actualiza el vehículo a estado ALQUILADO y fija km/combustible de salida.
        6. Registra el depósito en garantía en la tabla de pagos (si el monto es > 0).
        """
        self.validate_contract_rules(contract, is_update=False)

        # Asignar usuario logueado en sesión
        if not contract.id_usuario:
            current_user = session.current_user
            contract.id_usuario = current_user.id_usuario if current_user and current_user.id_usuario else 1

        # Generar código correlativo si no fue fijado
        if not contract.codigo_contrato:
            contract.codigo_contrato = self._generate_contract_code()

        contract.estado = ContractStatus.ACTIVO
        contract.fecha_hora_salida_real = contract.fecha_hora_salida_real or datetime.now()

        with self.run_in_transaction() as conn:
            # 1. Crear el contrato
            created_contract = self.contract_repo.create(contract, conn=conn)

            # 2. Si proviene de reserva, actualizar estado de la reserva
            if created_contract.id_reserva:
                reserva = self.reservation_repo.get_by_id(created_contract.id_reserva, conn=conn)
                if reserva and reserva.estado in (ReservationStatus.CONFIRMADA, ReservationStatus.PENDIENTE):
                    self.reservation_repo.update_status(
                        created_contract.id_reserva,
                        ReservationStatus.CONVERTIDA_A_CONTRATO,
                        conn=conn,
                    )
                    self.logger.info(
                        "Reserva ID %s vinculada al contrato %s marcada como CONVERTIDA_A_CONTRATO",
                        created_contract.id_reserva,
                        created_contract.codigo_contrato,
                    )

            # 3. Actualizar estado y parámetros del vehículo a ALQUILADO
            self.vehicle_repo.update_delivery_state(
                id_vehiculo=created_contract.id_vehiculo,
                kilometraje=created_contract.kilometraje_salida,
                combustible=created_contract.combustible_salida,
                new_status=VehicleStatus.ALQUILADO,
                conn=conn,
            )

            # 4. Si se especificó monto de garantía, registrar el pago del depósito
            if created_contract.monto_garantia > Decimal("0.00"):
                payment_trx = self._generate_payment_code(prefix="TRX-GAR")
                guarantee_payment = Payment(
                    codigo_transaccion=payment_trx,
                    id_contrato=created_contract.id_contrato,
                    id_reserva=created_contract.id_reserva,
                    tipo_movimiento=PaymentType.DEPOSITO_GARANTIA,
                    metodo_pago=metodo_pago_garantia,
                    monto=created_contract.monto_garantia,
                    referencia=(referencia_pago_garantia or f"Depósito Garantía {created_contract.codigo_contrato}")[:60],
                    id_usuario=created_contract.id_usuario,
                )
                self.payment_repo.create(guarantee_payment, conn=conn)
                created_contract.pagos.append(guarantee_payment)

        self.logger.info(
            "Contrato '%s' formalizado exitosamente para cliente ID %s y vehículo ID %s.",
            created_contract.codigo_contrato,
            created_contract.id_cliente,
            created_contract.id_vehiculo,
        )
        return created_contract

    def cancel_contract(self, id_contrato: int, motivo: Optional[str] = None) -> None:
        """Anula un contrato activo recién emitido y restaura el estado del vehículo a DISPONIBLE."""
        contract = self.get_contract(id_contrato)
        if contract.estado != ContractStatus.ACTIVO:
            raise InvalidStateTransitionError(
                f"Solo se pueden anular contratos en estado 'ACTIVO'. Estado actual: '{contract.estado.value}'.",
                code="CANNOT_CANCEL_NON_ACTIVE_CONTRACT",
            )

        with self.run_in_transaction() as conn:
            # 1. Cambiar estado a ANULADO
            self.contract_repo.update_status(id_contrato, ContractStatus.ANULADO, conn=conn)

            # 2. Restaurar vehículo a DISPONIBLE
            self.vehicle_repo.update_status(contract.id_vehiculo, VehicleStatus.DISPONIBLE, conn=conn)

            # 3. Si hubo depósito en garantía, generar el registro de reembolso
            for p in contract.pagos:
                if p.tipo_movimiento == PaymentType.DEPOSITO_GARANTIA:
                    refund_trx = self._generate_payment_code(prefix="TRX-REF")
                    refund_payment = Payment(
                        codigo_transaccion=refund_trx,
                        id_contrato=id_contrato,
                        tipo_movimiento=PaymentType.REEMBOLSO_GARANTIA,
                        metodo_pago=p.metodo_pago,
                        monto=p.monto,
                        referencia=f"Reembolso {contract.codigo_contrato}: {motivo or 'N/A'}"[:60],
                        id_usuario=session.current_user.id_usuario if session.current_user else 1,
                    )
                    self.payment_repo.create(refund_payment, conn=conn)

        self.logger.info(
            "Contrato ID %s (%s) anulado. Vehículo ID %s liberado. Motivo: %s",
            id_contrato,
            contract.codigo_contrato,
            contract.id_vehiculo,
            motivo or "Sin motivo especificado",
        )

    def get_contract(self, id_contrato: int) -> Contract:
        """Obtiene un contrato por su ID primario o lanza RecordNotFoundError."""
        contract = self.contract_repo.get_by_id(id_contrato)
        if not contract:
            raise RecordNotFoundError(f"No se encontró el contrato con ID {id_contrato}.", code="CONTRACT_NOT_FOUND")
        return contract

    def get_contract_by_codigo(self, codigo_contrato: str) -> Contract:
        """Obtiene un contrato por su código alfanumérico o lanza RecordNotFoundError."""
        contract = self.contract_repo.get_by_codigo(codigo_contrato)
        if not contract:
            raise RecordNotFoundError(f"No se encontró el contrato con código '{codigo_contrato}'.", code="CONTRACT_NOT_FOUND")
        return contract

    def list_contracts(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Contract]:
        """Consulta y lista contratos aplicando filtros de búsqueda textual y fechas."""
        return self.contract_repo.list_all(
            search=search,
            status=status,
            client_id=client_id,
            vehicle_id=vehicle_id,
            from_date=from_date,
            to_date=to_date,
        )

    def get_coverages(self) -> List[InsuranceCoverage]:
        """Retorna las coberturas y pólizas de seguro activas."""
        return self.coverage_repo.list_all()

    def get_coverage(self, id_cobertura: int) -> InsuranceCoverage:
        """Obtiene una cobertura específica por su ID."""
        coverage = self.coverage_repo.get_by_id(id_cobertura)
        if not coverage:
            raise RecordNotFoundError(f"Cobertura con ID {id_cobertura} no encontrada.", code="COVERAGE_NOT_FOUND")
        return coverage


# Instancia singleton del servicio de contratos
contract_service = ContractService()
