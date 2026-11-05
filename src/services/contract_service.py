"""Servicio de lógica de negocio para Contratos, Formalización y Entrega de Vehículos (BLL)."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from src.api_client import ApiClientError, api_client
from src.core.exceptions import (
    AuthenticationError,
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
from src.repositories.orm.client_orm_repository import ClientORMRepository
from src.repositories.orm.contract_orm_repository import (
    ContractORMRepository,
    CoverageORMRepository,
    PaymentORMRepository,
)
from src.repositories.orm.reservation_orm_repository import ReservationORMRepository
from src.repositories.orm.user_orm_repository import UserORMRepository
from src.repositories.orm.vehicle_orm_repository import VehicleORMRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


class ContractService(BaseService):
    """Servicio empresarial que orquesta la formalización de alquileres, contratos y entrega física."""

    def __init__(
        self,
        contract_repo: Optional[ContractORMRepository] = None,
        coverage_repo: Optional[CoverageORMRepository] = None,
        payment_repo: Optional[PaymentORMRepository] = None,
        vehicle_repo: Optional[VehicleORMRepository] = None,
        client_repo: Optional[ClientORMRepository] = None,
        reservation_repo: Optional[ReservationORMRepository] = None,
    ) -> None:
        super().__init__()
        self.contract_repo = contract_repo or ContractORMRepository(self.db)
        self.coverage_repo = coverage_repo or CoverageORMRepository(self.db)
        self.payment_repo = payment_repo or PaymentORMRepository(self.db)
        self.vehicle_repo = vehicle_repo or VehicleORMRepository(self.db)
        self.client_repo = client_repo or ClientORMRepository(self.db)
        self.reservation_repo = reservation_repo or ReservationORMRepository(self.db)
        self.user_repo = UserORMRepository(self.db)

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

        if api_client.remote_mode:
            try:
                vehicle = api_client.to_vehicle(api_client.get_vehicle(id_vehiculo))
                categories = [api_client.to_vehicle_category(c) for c in api_client.list_categories()]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc
            category = next((c for c in categories if c.id_categoria == vehicle.id_categoria), None)
            if not category:
                raise RecordNotFoundError("No se encontró la categoría del vehículo seleccionado.")
            coverage = self.get_coverage(id_cobertura)
        else:
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
        if api_client.remote_mode:
            self.validate_positive("Cliente", contract.id_cliente)
            self.validate_positive("Vehículo", contract.id_vehiculo)
            self.validate_positive("Cobertura de Seguro", contract.id_cobertura)
            self.validate_required("Fecha de Inicio Pactada", contract.fecha_hora_inicio_pactada)
            self.validate_required("Fecha de Fin Pactada", contract.fecha_hora_fin_pactada)

            drivers_payload = []
            for idx, d in enumerate(contract.conductores_adicionales, start=1):
                if not d.nombre_completo.strip():
                    raise ValidationError(f"El conductor adicional #{idx} no tiene nombre completo.", code="MISSING_DRIVER_NAME")
                if not d.numero_licencia.strip():
                    raise ValidationError(f"El conductor adicional #{idx} no tiene número de licencia.", code="MISSING_DRIVER_LICENSE")
                if not d.fecha_vencimiento_licencia:
                    raise ValidationError(f"El conductor adicional #{idx} no tiene fecha de vencimiento de licencia.", code="MISSING_DRIVER_LICENSE_EXPIRY")
                drivers_payload.append(
                    {
                        "nombre_completo": d.nombre_completo.strip(),
                        "identificacion": d.identificacion.strip(),
                        "numero_licencia": d.numero_licencia.strip(),
                        "fecha_vencimiento_licencia": d.fecha_vencimiento_licencia.isoformat(),
                    }
                )

            payload: dict[str, Any] = {
                "id_reserva": contract.id_reserva,
                "id_cliente": int(contract.id_cliente),
                "id_vehiculo": int(contract.id_vehiculo),
                "id_cobertura": int(contract.id_cobertura),
                "fecha_hora_inicio_pactada": contract.fecha_hora_inicio_pactada.isoformat() if contract.fecha_hora_inicio_pactada else None,
                "fecha_hora_fin_pactada": contract.fecha_hora_fin_pactada.isoformat() if contract.fecha_hora_fin_pactada else None,
                "fecha_hora_salida_real": contract.fecha_hora_salida_real.isoformat() if contract.fecha_hora_salida_real else None,
                "kilometraje_salida": int(contract.kilometraje_salida),
                "combustible_salida": str(contract.combustible_salida),
                "tarifa_diaria_aplicada": str(contract.tarifa_diaria_aplicada),
                "monto_garantia": str(contract.monto_garantia),
                "kilometraje_ilimitado": bool(contract.kilometraje_ilimitado),
                "limite_km_diario": contract.limite_km_diario,
                "costo_km_excedente": str(contract.costo_km_excedente),
                "metodo_pago_garantia": metodo_pago_garantia.value if isinstance(metodo_pago_garantia, PaymentMethod) else str(metodo_pago_garantia),
                "referencia_pago_garantia": referencia_pago_garantia,
                "conductores_adicionales": drivers_payload,
            }
            try:
                data = api_client.create_contract(payload)
                return api_client.to_contract(data)
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        self.validate_contract_rules(contract, is_update=False)

        # Asignar usuario logueado en sesión (Fail-Fast si no hay sesión)
        if not contract.id_usuario:
            current_user = session.current_user
            if not current_user or not current_user.id_usuario:
                raise AuthenticationError(
                    "Debe iniciar sesión para formalizar un contrato.",
                    code="AUTHENTICATION_REQUIRED",
                )
            contract.id_usuario = current_user.id_usuario

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
        if api_client.remote_mode:
            try:
                api_client.cancel_contract(id_contrato, motivo=motivo)
                return
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

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
            current_user = session.current_user
            refund_user_id = current_user.id_usuario if current_user and current_user.id_usuario else contract.id_usuario
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
                        id_usuario=refund_user_id,
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
        if api_client.remote_mode:
            try:
                data = api_client.get_contract(id_contrato)
                return api_client.to_contract(data)
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        contract = self.contract_repo.get_by_id(id_contrato)
        if not contract:
            raise RecordNotFoundError(f"No se encontró el contrato con ID {id_contrato}.", code="CONTRACT_NOT_FOUND")
        return contract

    def get_contract_by_codigo(self, codigo_contrato: str) -> Contract:
        """Obtiene un contrato por su código alfanumérico o lanza RecordNotFoundError."""
        if api_client.remote_mode:
            contracts = self.list_contracts(search=codigo_contrato)
            for c in contracts:
                if c.codigo_contrato == codigo_contrato:
                    return c
            raise RecordNotFoundError(f"No se encontró el contrato con código '{codigo_contrato}'.", code="CONTRACT_NOT_FOUND")

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
        if api_client.remote_mode:
            try:
                rows = api_client.list_contracts(
                    search=search,
                    status=status,
                    client_id=client_id,
                    vehicle_id=vehicle_id,
                )
                return [api_client.to_contract(r) for r in rows]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

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
        if api_client.remote_mode:
            try:
                rows = api_client.list_coverages()
                return [api_client.to_insurance_coverage(r) for r in rows]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc
        return self.coverage_repo.list_all()

    def get_coverage(self, id_cobertura: int) -> InsuranceCoverage:
        """Obtiene una cobertura específica por su ID."""
        if api_client.remote_mode:
            for cov in self.get_coverages():
                if cov.id_cobertura == id_cobertura:
                    return cov
            raise RecordNotFoundError(f"Cobertura con ID {id_cobertura} no encontrada.", code="COVERAGE_NOT_FOUND")

        coverage = self.coverage_repo.get_by_id(id_cobertura)
        if not coverage:
            raise RecordNotFoundError(f"Cobertura con ID {id_cobertura} no encontrada.", code="COVERAGE_NOT_FOUND")
        return coverage

    # ------------------------------------------------------------------------
    # Generación de Documento Legal de Contrato (HTML Imprimible y PDF)
    # ------------------------------------------------------------------------

    def build_contract_document_html(self, id_contrato: int) -> str:
        """Construye el documento legal del contrato en formato HTML/CSS listo para impresión o exportación a PDF."""
        if api_client.remote_mode:
            try:
                data = api_client.get_contract_document_html(id_contrato)
                return str(data.get("html", ""))
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        contract = self.get_contract(id_contrato)
        client = self.client_repo.get_by_id(contract.id_cliente)
        vehicle = self.vehicle_repo.get_by_id(contract.id_vehiculo)
        coverage = self.coverage_repo.get_by_id(contract.id_cobertura)
        target_tid = contract.tenant_id or session.tenant_id
        agency = self.user_repo.get_agency_by_id(target_tid)

        # Datos de la Agencia Arrendadora
        ag_nombre = agency.nombre_comercial if agency else session.agency_name
        ag_codigo = agency.codigo_agencia if agency else session.agency_code
        ag_ruc = agency.ruc_nit if agency else "J0310000000000"
        ag_tel = agency.telefono if agency else "+505-2200-0000"
        ag_email = (agency.email if agency and agency.email else "contacto@autorentpro.com.ni")
        ag_dir = agency.direccion if agency else "Managua, Nicaragua"

        # Datos del Cliente y Licencia
        cli_nombre = client.nombre_completo if client else (contract.cliente_nombre or f"ID #{contract.id_cliente}")
        cli_ident = client.identificacion if client else (contract.cliente_identificacion or "—")
        cli_tipo = client.tipo_persona.value if client else "NATURAL"
        cli_tel = client.telefono if client else (contract.cliente_telefono or "—")
        cli_email = client.email if client else "—"
        cli_dir = client.direccion if client else "—"

        if client and client.licencia:
            lic_num = client.licencia.numero_licencia
            lic_cat = client.licencia.categoria_licencia
            lic_pais = client.licencia.pais_emision
            lic_venc = (
                client.licencia.fecha_vencimiento.strftime("%d/%m/%Y")
                if client.licencia.fecha_vencimiento
                else "—"
            )
        else:
            lic_num, lic_cat, lic_pais, lic_venc = "Registrada en expediente", "—", "Nicaragua", "—"

        # Datos del Vehículo
        veh_placa = vehicle.placa if vehicle else (contract.vehiculo_placa or "—")
        veh_marca_modelo = (
            f"{vehicle.marca_nombre or ''} {vehicle.modelo_nombre or ''} ({vehicle.anio or ''})".strip()
            if vehicle
            else (contract.vehiculo_modelo or "—")
        )
        veh_cat = vehicle.categoria_nombre if vehicle else (contract.vehiculo_categoria or "—")
        veh_vin = vehicle.vin if vehicle else "—"
        veh_color = vehicle.color if vehicle else "—"
        fuel_pct = int((contract.combustible_salida or Decimal("1.00")) * 100)
        km_regimen = (
            "ILIMITADO"
            if contract.kilometraje_ilimitado
            else f"Límite: {contract.limite_km_diario or 0} km/día (${contract.costo_km_excedente:.2f}/km extra)"
        )

        # Fechas
        f_inicio = (
            contract.fecha_hora_inicio_pactada.strftime("%d/%m/%Y %H:%M")
            if contract.fecha_hora_inicio_pactada
            else "—"
        )
        f_fin = (
            contract.fecha_hora_fin_pactada.strftime("%d/%m/%Y %H:%M")
            if contract.fecha_hora_fin_pactada
            else "—"
        )
        f_salida_real = (
            contract.fecha_hora_salida_real.strftime("%d/%m/%Y %H:%M")
            if contract.fecha_hora_salida_real
            else f_inicio
        )
        f_emision = (
            contract.fecha_creacion.strftime("%d/%m/%Y %H:%M")
            if contract.fecha_creacion
            else datetime.now().strftime("%d/%m/%Y %H:%M")
        )

        # Cobertura y Costos
        cov_nombre = coverage.nombre if coverage else (contract.cobertura_nombre or "Básica")
        cov_costo_dia = coverage.costo_diario if coverage else (contract.cobertura_costo_diario or Decimal("0.00"))
        cov_deducible = coverage.porcentaje_deducible if coverage else Decimal("10.00")

        dias = contract.duracion_dias
        subtotal_renta = contract.tarifa_diaria_aplicada * Decimal(dias)
        subtotal_seguro = cov_costo_dia * Decimal(dias)
        total_alquiler = subtotal_renta + subtotal_seguro
        total_con_garantia = total_alquiler + contract.monto_garantia

        agente_emisor = contract.usuario_nombre or (
            session.current_user.nombre_completo if session.current_user else "Agente Autorizado"
        )

        # Conductores adicionales HTML
        if contract.conductores_adicionales:
            drivers_rows = ""
            for idx, d in enumerate(contract.conductores_adicionales, start=1):
                venc_d = (
                    d.fecha_vencimiento_licencia.strftime("%d/%m/%Y")
                    if d.fecha_vencimiento_licencia
                    else "—"
                )
                drivers_rows += f"""
                <tr>
                    <td style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: center;">{idx}</td>
                    <td style="padding: 5px 8px; border: 1px solid #cbd5e1;">{d.nombre_completo}</td>
                    <td style="padding: 5px 8px; border: 1px solid #cbd5e1;">{d.identificacion}</td>
                    <td style="padding: 5px 8px; border: 1px solid #cbd5e1;">{d.numero_licencia}</td>
                    <td style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: center;">{venc_d}</td>
                </tr>
                """
            drivers_html = f"""
            <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; margin-top: 6px; font-size: 9pt;">
                <thead>
                    <tr style="background-color: #f1f5f9; color: #1e293b;">
                        <th style="padding: 5px 8px; border: 1px solid #cbd5e1; width: 35px;">#</th>
                        <th style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: left;">Nombre Completo</th>
                        <th style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: left;">Identificación</th>
                        <th style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: left;">Nº Licencia</th>
                        <th style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: center;">Vencimiento</th>
                    </tr>
                </thead>
                <tbody>
                    {drivers_rows}
                </tbody>
            </table>
            """
        else:
            drivers_html = (
                '<div style="font-size: 8.5pt; color: #475569; padding: 4px 0;">'
                "No se registraron conductores adicionales autorizados. Únicamente el arrendatario titular está facultado para conducir el vehículo."
                "</div>"
            )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Contrato de Arrendamiento — {contract.codigo_contrato}</title>
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; font-size: 9.5pt; line-height: 1.35; margin: 0; padding: 0;">

    <!-- ENCABEZADO INSTITUCIONAL -->
    <table width="100%" cellspacing="0" cellpadding="0" style="border-bottom: 2px solid #0284c7; padding-bottom: 10px; margin-bottom: 12px;">
        <tr>
            <td width="62%" valign="top">
                <div style="font-size: 15pt; font-weight: bold; color: #0284c7;">{ag_nombre}</div>
                <div style="font-size: 8.5pt; color: #334155; margin-top: 2px;">
                    <b>Sucursal:</b> {ag_codigo} &nbsp;|&nbsp; <b>RUC/NIT:</b> {ag_ruc}
                </div>
                <div style="font-size: 8.5pt; color: #475569;">
                    <b>Dirección:</b> {ag_dir}
                </div>
                <div style="font-size: 8.5pt; color: #475569;">
                    <b>Teléfono:</b> {ag_tel} &nbsp;|&nbsp; <b>Email:</b> {ag_email}
                </div>
            </td>
            <td width="38%" valign="top" align="right">
                <div style="background-color: #0f172a; color: #ffffff; padding: 8px 12px; border-radius: 6px; text-align: right;">
                    <div style="font-size: 8pt; color: #94a3b8; text-transform: uppercase;">Contrato de Arrendamiento</div>
                    <div style="font-size: 13pt; font-weight: bold; color: #38bdf8;">{contract.codigo_contrato}</div>
                    <div style="font-size: 8pt; color: #e2e8f0; margin-top: 2px;">Estado: <b>{contract.estado.value}</b></div>
                    <div style="font-size: 8pt; color: #cbd5e1;">Emisión: {f_emision}</div>
                </div>
            </td>
        </tr>
    </table>

    <!-- SECCIÓN 1: DATOS DEL ARRENDATARIO Y CONDUCTORES -->
    <div style="background-color: #0f172a; color: #ffffff; font-weight: bold; font-size: 9.5pt; padding: 5px 10px; margin-bottom: 6px;">
        I. DATOS DEL ARRENDATARIO (CLIENTE TITULAR) Y LICENCIA DE CONDUCIR
    </div>
    <table width="100%" cellspacing="0" cellpadding="5" style="border-collapse: collapse; margin-bottom: 8px; font-size: 9pt;">
        <tr>
            <td width="50%" style="border: 1px solid #cbd5e1;"><b>Cliente / Razón Social:</b> {cli_nombre} ({cli_tipo})</td>
            <td width="50%" style="border: 1px solid #cbd5e1;"><b>Cédula / RUC / Pasaporte:</b> {cli_ident}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>Teléfono:</b> {cli_tel} &nbsp;|&nbsp; <b>Correo:</b> {cli_email}</td>
            <td style="border: 1px solid #cbd5e1;"><b>Dirección Domiciliar:</b> {cli_dir}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>Licencia de Conducir Nº:</b> {lic_num} ({lic_cat})</td>
            <td style="border: 1px solid #cbd5e1;"><b>País / Vencimiento Licencia:</b> {lic_pais} — Vence: <b>{lic_venc}</b></td>
        </tr>
    </table>

    <div style="font-weight: bold; font-size: 9pt; color: #1e293b; margin-top: 4px;">Conductores Adicionales Facultados:</div>
    {drivers_html}

    <!-- SECCIÓN 2: VEHÍCULO E INSPECCIÓN DE SALIDA -->
    <div style="background-color: #0f172a; color: #ffffff; font-weight: bold; font-size: 9.5pt; padding: 5px 10px; margin-top: 12px; margin-bottom: 6px;">
        II. IDENTIFICACIÓN DEL VEHÍCULO Y ACTA DE ENTREGA FÍSICA DE SALIDA
    </div>
    <table width="100%" cellspacing="0" cellpadding="5" style="border-collapse: collapse; margin-bottom: 10px; font-size: 9pt;">
        <tr>
            <td width="34%" style="border: 1px solid #cbd5e1;"><b>Placa:</b> <span style="font-size: 10pt; font-weight: bold; color: #0284c7;">{veh_placa}</span></td>
            <td width="33%" style="border: 1px solid #cbd5e1;"><b>Marca / Modelo:</b> {veh_marca_modelo}</td>
            <td width="33%" style="border: 1px solid #cbd5e1;"><b>Categoría / Color:</b> {veh_cat} / {veh_color}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>Chasis (VIN):</b> {veh_vin}</td>
            <td style="border: 1px solid #cbd5e1;"><b>Odómetro Salida:</b> <b>{contract.kilometraje_salida:,} km</b></td>
            <td style="border: 1px solid #cbd5e1;"><b>Combustible Salida:</b> <b>{fuel_pct}%</b> ({contract.combustible_salida})</td>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>Inicio Pactado:</b> {f_inicio}</td>
            <td style="border: 1px solid #cbd5e1;"><b>Fin Pactado:</b> <b>{f_fin}</b></td>
            <td style="border: 1px solid #cbd5e1;"><b>Entrega Física Real:</b> {f_salida_real}</td>
        </tr>
        <tr>
            <td colspan="2" style="border: 1px solid #cbd5e1;">
                <b>Inventario Entregado:</b> [✓] Llave encendido &nbsp; [✓] Llanta auxilio &nbsp; [✓] Gata y herramientas &nbsp; [✓] Circulación y Seguro
            </td>
            <td style="border: 1px solid #cbd5e1;"><b>Régimen Km:</b> {km_regimen}</td>
        </tr>
    </table>

    <!-- SECCIÓN 3: DESGLOSE ECONÓMICO Y GARANTÍA -->
    <div style="background-color: #0f172a; color: #ffffff; font-weight: bold; font-size: 9.5pt; padding: 5px 10px; margin-bottom: 6px;">
        III. DESGLOSE FINANCIERO, COBERTURA DE SEGURO Y DEPÓSITO EN GARANTÍA
    </div>
    <table width="100%" cellspacing="0" cellpadding="6" style="border-collapse: collapse; margin-bottom: 10px; font-size: 9pt;">
        <tr style="background-color: #f1f5f9;">
            <th align="left" style="border: 1px solid #cbd5e1;">Concepto Financiero</th>
            <th align="left" style="border: 1px solid #cbd5e1;">Detalle / Base de Cálculo</th>
            <th align="right" style="border: 1px solid #cbd5e1; width: 120px;">Importe (USD)</th>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>1. Arrendamiento Base de Vehículo</b></td>
            <td style="border: 1px solid #cbd5e1;">{dias} día(s) pactado(s) × ${contract.tarifa_diaria_aplicada:,.2f} / día</td>
            <td align="right" style="border: 1px solid #cbd5e1;"><b>${subtotal_renta:,.2f}</b></td>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>2. Póliza de Cobertura: {cov_nombre}</b></td>
            <td style="border: 1px solid #cbd5e1;">{dias} día(s) × ${cov_costo_dia:,.2f} / día (Deducible por siniestro: {cov_deducible}%)</td>
            <td align="right" style="border: 1px solid #cbd5e1;"><b>${subtotal_seguro:,.2f}</b></td>
        </tr>
        <tr style="background-color: #f8fafc;">
            <td colspan="2" align="right" style="border: 1px solid #cbd5e1;"><b>SUBTOTAL ESTIMADO DEL ALQUILER (RENTA + SEGURO):</b></td>
            <td align="right" style="border: 1px solid #cbd5e1; font-size: 10pt; color: #0284c7;"><b>${total_alquiler:,.2f}</b></td>
        </tr>
        <tr>
            <td style="border: 1px solid #cbd5e1;"><b>3. Depósito en Garantía Reembolsable</b></td>
            <td style="border: 1px solid #cbd5e1;">Custodia por daños, faltante de combustible, multas o mora en retorno</td>
            <td align="right" style="border: 1px solid #cbd5e1;"><b>${contract.monto_garantia:,.2f}</b></td>
        </tr>
        <tr style="background-color: #e0f2fe;">
            <td colspan="2" align="right" style="border: 1px solid #0284c7;"><b>TOTAL GENERAL FORMALIZADO EN APERTURA:</b></td>
            <td align="right" style="border: 1px solid #0284c7; font-size: 10.5pt; font-weight: bold; color: #0369a1;">${total_con_garantia:,.2f}</td>
        </tr>
    </table>

    <!-- SECCIÓN 4: CLÁUSULAS CONTRACTUALES -->
    <div style="background-color: #0f172a; color: #ffffff; font-weight: bold; font-size: 9.5pt; padding: 5px 10px; margin-bottom: 6px;">
        IV. TÉRMINOS, CLÁUSULAS Y CONDICIONES LEGALES DEL ARRENDAMIENTO
    </div>
    <div style="border: 1px solid #cbd5e1; padding: 8px 10px; font-size: 8pt; color: #334155; text-align: justify; margin-bottom: 18px;">
        <b>PRIMERA (Objeto y Estado del Vehículo):</b> EL ARRENDATARIO declara recibir el vehículo descrito en la Sección II en óptimas condiciones mecánicas, de carrocería y con el inventario completo detallado, obligándose a restituirlo en el mismo estado en la fecha y hora pactadas.<br>
        <b>SEGUNDA (Uso Autorizado y Prohibiciones):</b> Queda estrictamente prohibido: (a) permitir la conducción a personas no registradas en este contrato; (b) subarrendar el vehículo, utilizarlo para transporte remunerado, competencias o actividades ilícitas; (c) conducir bajo efectos del alcohol o estupefacientes; y (d) sacar el vehículo fuera del territorio nacional sin autorización escrita de LA AGENCIA.<br>
        <b>TERCERA (Retraso, Combustible y Siniestros):</b> La devolución posterior a la hora pactada generará el recargo horario establecido según la categoría del vehículo. Toda diferencia en el nivel de combustible respecto a la salida será liquidada en el acta de retorno. En caso de colisión, robo o daño físico, EL ARRENDATARIO deberá notificar de inmediato a LA AGENCIA y a la autoridad de tránsito, asumiendo el deducible correspondiente a la póliza contratada.<br>
        <b>CUARTA (Depósito en Garantía y Liquidación Final):</b> El depósito en garantía respalda cualquier saldo por días adicionales, daños físicos, limpieza extraordinaria, multas de tránsito o faltante de combustible. De no existir cargos pendientes al cierre de la inspección técnica de retorno, dicho depósito será reembolsado íntegramente a EL ARRENDATARIO.
    </div>

    <!-- SECCIÓN 5: BLOQUE DE FIRMAS -->
    <table width="100%" cellspacing="0" cellpadding="0" style="margin-top: 28px;">
        <tr>
            <td width="46%" align="center" valign="bottom">
                <div style="border-top: 1px solid #0f172a; width: 88%; padding-top: 6px; margin: 0 auto;">
                    <div style="font-weight: bold; font-size: 9.5pt;">FIRMA DEL ARRENDATARIO (CLIENTE)</div>
                    <div style="font-size: 8.5pt; color: #334155;">{cli_nombre}</div>
                    <div style="font-size: 8pt; color: #64748b;">Identificación: {cli_ident}</div>
                </div>
            </td>
            <td width="8%"></td>
            <td width="46%" align="center" valign="bottom">
                <div style="border-top: 1px solid #0f172a; width: 88%; padding-top: 6px; margin: 0 auto;">
                    <div style="font-weight: bold; font-size: 9.5pt;">POR LA AGENCIA ARRENDADORA</div>
                    <div style="font-size: 8.5pt; color: #334155;">{agente_emisor}</div>
                    <div style="font-size: 8pt; color: #64748b;">{ag_nombre} ({ag_codigo}) — Sello y Firma</div>
                </div>
            </td>
        </tr>
    </table>

    <div style="margin-top: 16px; border-top: 1px dashed #cbd5e1; padding-top: 6px; font-size: 7.5pt; color: #64748b; text-align: center;">
        Documento oficial generado por AutoRent Pro — Contrato Nº {contract.codigo_contrato} | Reserva vinculada: {contract.reserva_codigo or 'Directo en Mostrador'} | Impreso el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    </div>

</body>
</html>
"""

    def export_contract_pdf(self, id_contrato: int, filepath: str) -> str:
        """Renderiza y guarda el documento legal del contrato en un archivo PDF listo para descargar e imprimir."""
        if not filepath or not filepath.strip():
            raise ValidationError("Debe especificar una ruta válida para guardar el archivo PDF.", code="INVALID_PDF_PATH")

        clean_path = filepath.strip()
        if not clean_path.lower().endswith(".pdf"):
            clean_path += ".pdf"

        html_content = self.build_contract_document_html(id_contrato)

        try:
            from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
            from PySide6.QtPrintSupport import QPrinter
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if not app:
                app = QApplication(["--platform", "offscreen"])

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(clean_path)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)

            doc = QTextDocument()
            doc.setHtml(html_content)
            doc.print_(printer)

            self.logger.info(
                "Contrato ID %s exportado exitosamente a PDF en: %s",
                id_contrato,
                clean_path,
            )
            return clean_path
        except Exception as e:
            self.logger.exception("Error al generar el PDF del contrato ID %s en '%s'", id_contrato, clean_path)
            raise ValidationError(
                f"No se pudo generar el documento PDF del contrato: {e}",
                code="EXPORT_CONTRACT_PDF_ERROR",
            ) from e


# Instancia singleton del servicio de contratos
contract_service = ContractService()
