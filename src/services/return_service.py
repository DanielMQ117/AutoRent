"""Servicio de lógica de negocio para Devoluciones, Inspección de Retorno y Liquidaciones (BLL)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.core.exceptions import (
    AppException,
    BusinessRuleViolationError,
    InvalidStateTransitionError,
    RecordNotFoundError,
)
from src.core.logger import get_logger
from src.core.session import session
from src.domain.enums import (
    ContractStatus,
    DamageSeverity,
    PaymentMethod,
    PaymentType,
    SettlementStatus,
    VehicleStatus,
)
from src.domain.models import Damage, Payment, ReturnInspection, Settlement
from src.repositories.contract_repository import ContractRepository
from src.repositories.payment_repository import PaymentRepository
from src.repositories.return_repository import ReturnRepository
from src.repositories.settlement_repository import SettlementRepository
from src.repositories.vehicle_repository import VehicleRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


def _to_naive_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Normaliza un objeto datetime eliminando información de zona horaria para comparaciones seguras."""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class ReturnService(BaseService):
    """Orquesta el ciclo de recepción de vehículos, acta de daños, cálculo de penalizaciones y liquidación final."""

    def __init__(
        self,
        return_repo: Optional[ReturnRepository] = None,
        settlement_repo: Optional[SettlementRepository] = None,
        contract_repo: Optional[ContractRepository] = None,
        vehicle_repo: Optional[VehicleRepository] = None,
        payment_repo: Optional[PaymentRepository] = None,
    ) -> None:
        super().__init__()
        self.return_repo = return_repo or ReturnRepository()
        self.settlement_repo = settlement_repo or SettlementRepository()
        self.contract_repo = contract_repo or ContractRepository()
        self.vehicle_repo = vehicle_repo or VehicleRepository()
        self.payment_repo = payment_repo or PaymentRepository()

    def _generate_payment_code(self, prefix: str = "TRX-LIQ") -> str:
        """Genera un código de transacción único para movimientos de liquidación."""
        total = self.payment_repo.count_payments() + 1
        now_str = datetime.now().strftime("%Y%m")
        return f"{prefix}-{now_str}-{total:04d}"[:30]

    def validate_return_rules(
        self,
        contract: Any,
        return_data: ReturnInspection,
    ) -> None:
        """Valida que el contrato sea elegible para retorno y que los datos físicos sean coherentes."""
        # 1. Estado del contrato
        if contract.estado not in (ContractStatus.ACTIVO, ContractStatus.EN_INSPECCION):
            raise InvalidStateTransitionError(
                f"Solo se pueden recibir vehículos de contratos en estado 'ACTIVO' o 'EN_INSPECCION'. "
                f"Estado actual del contrato '{contract.codigo_contrato}': '{contract.estado.value}'.",
                code="INVALID_CONTRACT_STATUS_FOR_RETURN",
            )

        # 2. Coherencia temporal
        fecha_retorno = _to_naive_datetime(return_data.fecha_hora_retorno_real or datetime.now())
        fecha_salida = _to_naive_datetime(contract.fecha_hora_salida_real or contract.fecha_hora_inicio_pactada)
        if fecha_salida and fecha_retorno < fecha_salida:
            raise BusinessRuleViolationError(
                f"La fecha/hora de retorno ({fecha_retorno.strftime('%d/%m/%Y %H:%M')}) no puede ser anterior "
                f"a la fecha de salida del contrato ({fecha_salida.strftime('%d/%m/%Y %H:%M')}).",
                code="RETURN_BEFORE_DEPARTURE",
            )

        # 3. Coherencia física del odómetro
        if return_data.kilometraje_retorno < contract.kilometraje_salida:
            raise BusinessRuleViolationError(
                f"Incoherencia de odómetro: El kilometraje de retorno ({return_data.kilometraje_retorno} km) "
                f"no puede ser menor al kilometraje de salida registrado ({contract.kilometraje_salida} km).",
                code="INVALID_RETURN_ODOMETER",
            )

        # 4. Coherencia de nivel de combustible
        if return_data.combustible_retorno < Decimal("0.00") or return_data.combustible_retorno > Decimal("1.00"):
            raise BusinessRuleViolationError(
                f"Nivel de combustible inválido: {return_data.combustible_retorno}. Debe situarse entre 0.00 y 1.00.",
                code="INVALID_FUEL_LEVEL",
            )

        # 5. Validación de averías
        for d in return_data.danios:
            if d.costo_reparacion < Decimal("0.00"):
                raise BusinessRuleViolationError(
                    f"El costo de reparación del daño en '{d.zona_carroceria}' no puede ser negativo.",
                    code="NEGATIVE_DAMAGE_COST",
                )

    def calculate_penalties(
        self,
        contract: Any,
        return_data: ReturnInspection,
    ) -> Dict[str, Any]:
        """Calcula el balance preliminar de la liquidación (días facturados, penalizaciones, daños y saldos)."""
        fecha_retorno = _to_naive_datetime(return_data.fecha_hora_retorno_real or datetime.now())
        fecha_salida = _to_naive_datetime(contract.fecha_hora_salida_real or contract.fecha_hora_inicio_pactada or fecha_retorno)
        fecha_fin = _to_naive_datetime(contract.fecha_hora_fin_pactada)

        # 1. Días facturables de renta
        delta = fecha_retorno - fecha_salida
        dias_efectivos = delta.days
        # Tolerancia de gracia de 60 minutos: si excede 1 hora, se redondea a un día adicional
        if delta.seconds > 3600:
            dias_efectivos += 1
        dias_facturados = max(1, dias_efectivos)

        # Subtotal renta pactada + seguro
        tarifa_dia = contract.tarifa_diaria_aplicada
        seguro_dia = contract.cobertura_costo_diario or Decimal("0.00")
        subtotal_renta = (tarifa_dia + seguro_dia) * Decimal(dias_facturados)

        # 2. Penalización por retraso (horas extra sobre fecha_hora_fin_pactada)
        horas_retraso = 0
        cargos_retraso = Decimal("0.00")
        if fecha_fin and fecha_retorno > fecha_fin:
            diff_retraso = fecha_retorno - fecha_fin
            total_segundos = diff_retraso.total_seconds()
            horas = int(total_segundos // 3600)
            if (total_segundos % 3600) > 1800:
                horas += 1
            horas_retraso = max(0, horas)
            # Tarifa estándar de penalización: $10.00 por hora de retraso
            cargos_retraso = Decimal(horas_retraso) * Decimal("10.00")

        # 3. Penalización por faltante de combustible
        # Si devuelve menos combustible que en la salida: $25.00 por cada 1/4 de tanque ($100.00 tanque lleno)
        combustible_salida = contract.combustible_salida or Decimal("1.00")
        combustible_faltante = max(Decimal("0.00"), combustible_salida - return_data.combustible_retorno)
        cargos_combustible = (combustible_faltante * Decimal("100.00")).quantize(Decimal("0.01"))

        # 4. Penalización por exceso de kilometraje (si aplica política)
        cargos_km_excedente = Decimal("0.00")
        if not contract.kilometraje_ilimitado and contract.limite_km_diario and contract.limite_km_diario > 0:
            max_km_permitido = contract.limite_km_diario * dias_facturados
            km_recorridos = return_data.kilometraje_retorno - contract.kilometraje_salida
            if km_recorridos > max_km_permitido:
                excedente = km_recorridos - max_km_permitido
                cargos_km_excedente = Decimal(excedente) * contract.costo_km_excedente

        # 5. Cargos por daños físicos evaluados
        cargos_danios = return_data.costo_total_danios

        # 6. Total Bruto
        total_bruto = (
            subtotal_renta
            + cargos_retraso
            + cargos_combustible
            + cargos_km_excedente
            + cargos_danios
        ).quantize(Decimal("0.01"))

        # 7. Balance contra Depósito de Garantía
        garantia_inicial = contract.monto_garantia or Decimal("0.00")
        monto_garantia_aplicado = min(total_bruto, garantia_inicial).quantize(Decimal("0.01"))
        saldo_cliente = (total_bruto - garantia_inicial).quantize(Decimal("0.01"))

        return {
            "dias_facturados": dias_facturados,
            "subtotal_renta": subtotal_renta,
            "horas_retraso": horas_retraso,
            "cargos_retraso": cargos_retraso,
            "combustible_faltante": combustible_faltante,
            "cargos_combustible": cargos_combustible,
            "cargos_km_excedente": cargos_km_excedente,
            "cargos_danios": cargos_danios,
            "total_bruto": total_bruto,
            "monto_garantia_inicial": garantia_inicial,
            "monto_garantia_aplicado": monto_garantia_aplicado,
            "saldo_cliente": saldo_cliente,
        }

    def process_return_and_settlement(
        self,
        id_contrato: int,
        return_data: ReturnInspection,
        metodo_pago: PaymentMethod = PaymentMethod.EFECTIVO,
        referencia_pago: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ejecuta de forma atómica e indivisible (ACID) la recepción del vehículo, liquidación y cierre."""
        contract = self.contract_repo.get_by_id(id_contrato)
        if not contract:
            raise RecordNotFoundError(f"No se encontró el contrato con ID {id_contrato}.", code="CONTRACT_NOT_FOUND")

        # Comprobar que no haya sido ya devuelto
        existing_return = self.return_repo.get_by_contract_id(id_contrato)
        if existing_return:
            raise BusinessRuleViolationError(
                f"El contrato '{contract.codigo_contrato}' ya cuenta con una devolución registrada (ID: {existing_return.id_devolucion}).",
                code="CONTRACT_ALREADY_RETURNED",
            )

        # 1. Validar reglas de negocio
        self.validate_return_rules(contract, return_data)

        # 2. Calcular liquidación
        calc = self.calculate_penalties(contract, return_data)
        return_data.horas_retraso = calc["horas_retraso"]
        return_data.id_contrato = id_contrato

        # Asignar usuario logueado en sesión
        current_user = session.current_user
        user_id = current_user.id_usuario if current_user and current_user.id_usuario else 1
        return_data.id_usuario = user_id

        with self.run_in_transaction() as conn:
            # 3. Crear el acta de devolución física y sus daños
            # Nota: El trigger 'trg_despues_devolucion' en PostgreSQL actualiza odómetro y combustible del vehículo
            # y transiciona el contrato a 'EN_LIQUIDACION'
            created_return = self.return_repo.create(return_data, conn=conn)

            # 4. Crear la Liquidación Financiera
            settlement = Settlement(
                id_contrato=id_contrato,
                id_devolucion=created_return.id_devolucion,
                fecha_liquidacion=datetime.now(),
                dias_facturados=calc["dias_facturados"],
                subtotal_renta=calc["subtotal_renta"],
                cargos_retraso=calc["cargos_retraso"],
                cargos_combustible=calc["cargos_combustible"],
                cargos_km_excedente=calc["cargos_km_excedente"],
                cargos_danios=calc["cargos_danios"],
                total_bruto=calc["total_bruto"],
                monto_garantia_aplicado=calc["monto_garantia_aplicado"],
                saldo_cliente=calc["saldo_cliente"],
                estado_liquidacion=SettlementStatus.CERRADA,
                id_usuario=user_id,
            )
            created_settlement = self.settlement_repo.create(settlement, conn=conn)

            # 5. Asentar el movimiento de pago o reembolso en tabla pagos
            created_payment = None
            saldo = calc["saldo_cliente"]
            if saldo > Decimal("0.00"):
                # Cobro adicional al cliente
                pay_trx = self._generate_payment_code(prefix="TRX-LIQ")
                pago = Payment(
                    codigo_transaccion=pay_trx,
                    id_contrato=id_contrato,
                    id_liquidacion=created_settlement.id_liquidacion,
                    tipo_movimiento=PaymentType.COBRO_LIQUIDACION,
                    metodo_pago=metodo_pago,
                    monto=saldo,
                    referencia=(referencia_pago or f"Cobro Liquidación {contract.codigo_contrato}")[:60],
                    id_usuario=user_id,
                )
                created_payment = self.payment_repo.create(pago, conn=conn)
                created_settlement.pagos.append(created_payment)
            elif saldo < Decimal("0.00"):
                # Reembolso de garantía al cliente
                refund_trx = self._generate_payment_code(prefix="TRX-REF")
                reembolso = Payment(
                    codigo_transaccion=refund_trx,
                    id_contrato=id_contrato,
                    id_liquidacion=created_settlement.id_liquidacion,
                    tipo_movimiento=PaymentType.REEMBOLSO_GARANTIA,
                    metodo_pago=metodo_pago,
                    monto=abs(saldo),
                    referencia=(referencia_pago or f"Reembolso Liquidación {contract.codigo_contrato}")[:60],
                    id_usuario=user_id,
                )
                created_payment = self.payment_repo.create(reembolso, conn=conn)
                created_settlement.pagos.append(created_payment)

            # 6. Actualizar contrato a estado LIQUIDADO
            self.contract_repo.update_status(id_contrato, ContractStatus.LIQUIDADO, conn=conn)

            # 7. Evaluar destino del vehículo
            # Si tiene averías graves o superó el umbral de próximo mantenimiento preventivo -> EN_MANTENIMIENTO
            # Caso contrario -> DISPONIBLE
            vehiculo = self.vehicle_repo.get_by_id(contract.id_vehiculo, conn=conn)
            km_proximo_mant = vehiculo.km_proximo_mantenimiento if vehiculo else 999999999

            if return_data.tiene_danio_grave or return_data.kilometraje_retorno >= km_proximo_mant:
                self.vehicle_repo.update_status(contract.id_vehiculo, VehicleStatus.EN_MANTENIMIENTO, conn=conn)
                logger.warning(
                    "Vehículo ID %s derivado a EN_MANTENIMIENTO tras liquidación (Daño grave: %s, Km actual: %s, Próximo mant: %s).",
                    contract.id_vehiculo,
                    return_data.tiene_danio_grave,
                    return_data.kilometraje_retorno,
                    km_proximo_mant,
                )
            else:
                self.vehicle_repo.update_status(contract.id_vehiculo, VehicleStatus.DISPONIBLE, conn=conn)
                logger.info(
                    "Vehículo ID %s restituido satisfactoriamente a estado DISPONIBLE.",
                    contract.id_vehiculo,
                )

        logger.info(
            "Ciclo de devolución y liquidación completado para contrato %s (Liquidación ID: %s).",
            contract.codigo_contrato,
            created_settlement.id_liquidacion,
        )

        return {
            "return_inspection": created_return,
            "settlement": created_settlement,
            "payment": created_payment,
        }

    def get_return(self, id_devolucion: int) -> ReturnInspection:
        """Obtiene un acta de devolución por su ID primario o lanza RecordNotFoundError."""
        ret = self.return_repo.get_by_id(id_devolucion)
        if not ret:
            raise RecordNotFoundError(f"No se encontró la devolución con ID {id_devolucion}.", code="RETURN_NOT_FOUND")
        return ret

    def get_return_by_contract(self, id_contrato: int) -> Optional[ReturnInspection]:
        """Obtiene la devolución asociada a un contrato específico si existe."""
        return self.return_repo.get_by_contract_id(id_contrato)

    def get_settlement_by_contract(self, id_contrato: int) -> Optional[Settlement]:
        """Obtiene la liquidación asociada a un contrato específico si existe."""
        return self.settlement_repo.get_by_contract_id(id_contrato)

    def list_returns(self, search: str = "", limit: int = 100) -> List[ReturnInspection]:
        """Lista las devoluciones registradas con soporte de filtros."""
        return self.return_repo.list_all(search=search, limit=limit)

    def list_settlements(self, search: str = "", limit: int = 100) -> List[Settlement]:
        """Lista las liquidaciones registradas con soporte de filtros."""
        return self.settlement_repo.list_all(search=search, limit=limit)


# Instancia singleton para inyección en controladores y vistas
return_service = ReturnService()
