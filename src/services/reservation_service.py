"""Servicio de lógica de negocio para la gestión de Reservas y Disponibilidad (BLL)."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from src.core.exceptions import (
    BusinessRuleViolationError,
    DuplicateRecordError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import get_logger
from src.core.session import session
from src.domain.enums import ClientStatus, ReservationStatus, VehicleStatus
from src.domain.models import Reservation, Vehicle
from src.repositories.client_repository import ClientRepository
from src.repositories.reservation_repository import ReservationRepository
from src.repositories.vehicle_repository import VehicleRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


class ReservationService(BaseService):
    """Servicio empresarial que orquesta la creación, validación temporal y disponibilidad de reservas."""

    def __init__(
        self,
        reservation_repo: Optional[ReservationRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        vehicle_repo: Optional[VehicleRepository] = None,
    ) -> None:
        super().__init__()
        self.reservation_repo = reservation_repo or ReservationRepository(self.db)
        self.client_repo = client_repo or ClientRepository(self.db)
        self.vehicle_repo = vehicle_repo or VehicleRepository(self.db)

    def _generate_reservation_code(self) -> str:
        """Genera un código correlativo único para la reserva con formato RES-YYYYMM-XXXX."""
        count = self.reservation_repo.count_reservations() + 1
        now = datetime.now()
        return f"RES-{now.strftime('%Y%m')}-{count:04d}"

    def calculate_duration_and_cost(
        self,
        id_categoria: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> tuple[int, Decimal, Decimal]:
        """Calcula los días facturables, la tarifa base diaria y el costo total proyectado.

        Returns:
            Tupla con (dias_computados, tarifa_base_diaria, costo_total_estimado)
        """
        if end_dt <= start_dt:
            raise ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio.",
                code="INVALID_DATE_RANGE",
            )

        categories = self.vehicle_repo.list_categories()
        category = next((c for c in categories if c.id_categoria == id_categoria), None)
        if not category:
            raise RecordNotFoundError(
                f"No se encontró la categoría de vehículo con ID {id_categoria}.",
                code="CATEGORY_NOT_FOUND",
            )

        delta = end_dt - start_dt
        dias = delta.days
        if delta.seconds > 3600:  # Excedente de 1 hora computa como día adicional
            dias += 1
        dias = max(1, dias)

        tarifa = category.tarifa_base_diaria
        total = tarifa * Decimal(dias)
        return dias, tarifa, total

    def check_availability(
        self,
        id_categoria: int,
        start_dt: datetime,
        end_dt: datetime,
        id_vehiculo: Optional[int] = None,
        exclude_reservation_id: Optional[int] = None,
    ) -> tuple[bool, List[Vehicle], str]:
        """Verifica la disponibilidad de vehículos para un rango de fechas.

        Returns:
            Tupla (disponible: bool, vehiculos_libres: List[Vehicle], mensaje: str)
        """
        if end_dt <= start_dt:
            return False, [], "La fecha de fin debe ser estrictamente posterior a la fecha de inicio."

        if id_vehiculo is not None:
            vehicle = self.vehicle_repo.get_by_id(id_vehiculo)
            if not vehicle:
                return False, [], f"El vehículo seleccionado con ID {id_vehiculo} no existe."

            if vehicle.estado == VehicleStatus.DE_BAJA:
                return False, [], f"El vehículo '{vehicle.placa}' está dado de baja."

            if vehicle.estado == VehicleStatus.EN_MANTENIMIENTO:
                return False, [], f"El vehículo '{vehicle.placa}' está en taller por mantenimiento."

            has_conflict = self.reservation_repo.check_vehicle_conflict(
                id_vehiculo=id_vehiculo,
                start_dt=start_dt,
                end_dt=end_dt,
                exclude_reservation_id=exclude_reservation_id,
            )

            if has_conflict:
                return False, [], f"El vehículo '{vehicle.placa}' ya se encuentra reservado o alquilado en ese intervalo."

            return True, [vehicle], f"Vehículo '{vehicle.placa}' disponible."

        # Verificación por categoría
        available_vehicles = self.reservation_repo.get_available_vehicles_for_period(
            id_categoria=id_categoria,
            start_dt=start_dt,
            end_dt=end_dt,
            exclude_reservation_id=exclude_reservation_id,
        )

        if not available_vehicles:
            return False, [], "No hay vehículos disponibles en la categoría seleccionada para el rango de fechas solicitado."

        return True, available_vehicles, f"{len(available_vehicles)} vehículo(s) disponible(s) en esta categoría."

    def validate_reservation_rules(
        self,
        reservation: Reservation,
        is_update: bool = False,
    ) -> None:
        """Aplica todas las reglas de negocio de la fase de reservas."""
        # 1. Validación de campos primarios
        self.validate_positive("Cliente", reservation.id_cliente)
        self.validate_positive("Categoría", reservation.id_categoria)
        self.validate_required("Fecha de Inicio", reservation.fecha_hora_inicio)
        self.validate_required("Fecha de Fin", reservation.fecha_hora_fin)

        start_dt = reservation.fecha_hora_inicio
        end_dt = reservation.fecha_hora_fin

        # 2. Coherencia de fechas
        if end_dt <= start_dt:
            raise ValidationError(
                "La fecha de finalización debe ser estrictamente posterior a la fecha de inicio.",
                code="INVALID_DATE_RANGE",
            )

        # Prevención de reservas en el pasado (con tolerancia de 15 minutos para carga operativa)
        now_with_tolerance = datetime.now() - timedelta(minutes=15)
        if start_dt < now_with_tolerance and not is_update:
            raise ValidationError(
                "No se pueden registrar reservas con fecha de inicio en el pasado.",
                code="PAST_DATE_NOT_ALLOWED",
            )

        # 3. Validación de elegibilidad del Cliente (RN-001, RN-002)
        client = self.client_repo.get_by_id(reservation.id_cliente)
        if not client:
            raise RecordNotFoundError(
                f"No se encontró ningún cliente registrado con el ID {reservation.id_cliente}.",
                code="CLIENT_NOT_FOUND",
            )

        if client.estado_cliente == ClientStatus.VETADO:
            raise BusinessRuleViolationError(
                f"Operación denegada: El cliente '{client.nombre_completo}' se encuentra VETADO en el sistema.",
                code="CLIENT_BANNED",
            )

        if client.estado_cliente == ClientStatus.MOROSO:
            raise BusinessRuleViolationError(
                f"Operación denegada: El cliente '{client.nombre_completo}' presenta saldo MOROSO pendiente de pago.",
                code="CLIENT_IN_DEBT",
            )

        # Verificación de vigencia de licencia de conducir
        if client.licencia:
            if client.licencia.fecha_vencimiento < end_dt.date():
                raise BusinessRuleViolationError(
                    f"Licencia no válida: La licencia del cliente ({client.licencia.numero_licencia}) "
                    f"vence el {client.licencia.fecha_vencimiento.strftime('%d/%m/%Y')}, "
                    f"antes de la culminación prevista de la reserva ({end_dt.strftime('%d/%m/%Y')}).",
                    code="EXPIRED_LICENSE_FOR_RESERVATION",
                )
        else:
            raise BusinessRuleViolationError(
                f"El cliente '{client.nombre_completo}' no cuenta con una licencia de conducir registrada.",
                code="CLIENT_NO_LICENSE",
            )

        # 4. Validación de Disponibilidad y Detección de Conflicto
        is_avail, avail_vehicles, msg = self.check_availability(
            id_categoria=reservation.id_categoria,
            start_dt=start_dt,
            end_dt=end_dt,
            id_vehiculo=reservation.id_vehiculo,
            exclude_reservation_id=reservation.id_reserva if is_update else None,
        )

        if not is_avail:
            raise BusinessRuleViolationError(msg, code="VEHICLE_AVAILABILITY_CONFLICT")

        # 5. Validación del monto de anticipo
        if reservation.monto_anticipo < Decimal("0.00"):
            raise ValidationError("El monto del anticipo no puede ser negativo.", code="NEGATIVE_DEPOSIT")

    def create_reservation(self, reservation: Reservation) -> Reservation:
        """Registra una nueva reserva validando disponibilidad y persistiendo en una transacción."""
        self.validate_reservation_rules(reservation, is_update=False)

        # Asignar usuario en sesión si no está establecido
        if not reservation.id_usuario:
            current_user = session.current_user
            reservation.id_usuario = current_user.id_usuario if current_user and current_user.id_usuario else 1

        # Generar código correlativo si no fue fijado
        if not reservation.codigo_reserva:
            reservation.codigo_reserva = self._generate_reservation_code()

        # Si cuenta con anticipo se asume CONFIRMADA; si es 0 permanece PENDIENTE (o el estado explícito si era válido)
        if reservation.monto_anticipo > Decimal("0.00") and reservation.estado == ReservationStatus.PENDIENTE:
            reservation.estado = ReservationStatus.CONFIRMADA
        elif reservation.estado not in (ReservationStatus.CONFIRMADA, ReservationStatus.PENDIENTE):
            reservation.estado = ReservationStatus.PENDIENTE

        with self.run_in_transaction() as conn:
            created = self.reservation_repo.create(reservation, conn=conn)

        self.logger.info(
            "Reserva '%s' creada exitosamente para cliente ID %s (Estado: %s)",
            created.codigo_reserva,
            created.id_cliente,
            created.estado.value,
        )
        return created

    def update_reservation(self, reservation: Reservation) -> Reservation:
        """Actualiza los términos de una reserva existente."""
        if not reservation.id_reserva:
            raise ValidationError("ID de reserva requerido para actualizar.", code="MISSING_RESERVATION_ID")

        current = self.reservation_repo.get_by_id(reservation.id_reserva)
        if not current:
            raise RecordNotFoundError(f"Reserva con ID {reservation.id_reserva} no encontrada.")

        if current.estado in (ReservationStatus.CANCELADA, ReservationStatus.VENCIDA, ReservationStatus.CONVERTIDA_A_CONTRATO):
            raise InvalidStateTransitionError(
                f"No se puede modificar una reserva en estado '{current.estado.value}'.",
                code="CANNOT_MODIFY_TERMINATED_RESERVATION",
            )

        self.validate_reservation_rules(reservation, is_update=True)

        with self.run_in_transaction() as conn:
            updated = self.reservation_repo.update(reservation, conn=conn)

        self.logger.info("Reserva ID %s actualizada satisfactoriamente.", updated.id_reserva)
        return updated

    def confirm_reservation(self, id_reserva: int) -> None:
        """Pasa una reserva de estado PENDIENTE a CONFIRMADA."""
        reservation = self.get_reservation(id_reserva)
        if reservation.estado != ReservationStatus.PENDIENTE:
            raise InvalidStateTransitionError(
                f"Solo las reservas en estado 'PENDIENTE' pueden ser confirmadas. Estado actual: '{reservation.estado.value}'.",
                code="INVALID_CONFIRMATION_STATE",
            )

        with self.run_in_transaction() as conn:
            self.reservation_repo.update_status(id_reserva, ReservationStatus.CONFIRMADA, conn=conn)

        self.logger.info("Reserva ID %s (%s) marcada como CONFIRMADA.", id_reserva, reservation.codigo_reserva)

    def cancel_reservation(self, id_reserva: int, motivo: Optional[str] = None) -> None:
        """Cancela una reserva activa (PENDIENTE o CONFIRMADA)."""
        reservation = self.get_reservation(id_reserva)
        if reservation.estado in (ReservationStatus.CANCELADA, ReservationStatus.VENCIDA, ReservationStatus.CONVERTIDA_A_CONTRATO):
            raise InvalidStateTransitionError(
                f"No se puede cancelar una reserva que ya se encuentra en estado '{reservation.estado.value}'.",
                code="CANNOT_CANCEL_RESERVATION",
            )

        with self.run_in_transaction() as conn:
            self.reservation_repo.update_status(id_reserva, ReservationStatus.CANCELADA, conn=conn)

        self.logger.info(
            "Reserva ID %s (%s) cancelada. Motivo: %s",
            id_reserva,
            reservation.codigo_reserva,
            motivo or "Sin motivo especificado",
        )

    def mark_converted_to_contract(self, id_reserva: int) -> None:
        """Marca la reserva como convertida a contrato al momento de formalizar la entrega (Fase 5)."""
        reservation = self.get_reservation(id_reserva)
        if reservation.estado not in (ReservationStatus.CONFIRMADA, ReservationStatus.PENDIENTE):
            raise InvalidStateTransitionError(
                f"La reserva debe estar 'CONFIRMADA' para formalizarse en un contrato. Estado actual: '{reservation.estado.value}'.",
                code="CANNOT_CONVERT_UNCONFIRMED_RESERVATION",
            )

        with self.run_in_transaction() as conn:
            self.reservation_repo.update_status(id_reserva, ReservationStatus.CONVERTIDA_A_CONTRATO, conn=conn)

        self.logger.info("Reserva ID %s convertida exitosamente a contrato.", id_reserva)

    def get_reservation(self, id_reserva: int) -> Reservation:
        """Obtiene una reserva por su ID o lanza RecordNotFoundError si no existe."""
        reservation = self.reservation_repo.get_by_id(id_reserva)
        if not reservation:
            raise RecordNotFoundError(
                f"No se encontró ninguna reserva con el ID {id_reserva}.",
                code="RESERVATION_NOT_FOUND",
            )
        return reservation

    def list_reservations(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        category_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Reservation]:
        """Consulta y lista reservas aplicando filtros de búsqueda y fechas."""
        return self.reservation_repo.list_all(
            search=search,
            status=status,
            client_id=client_id,
            category_id=category_id,
            from_date=from_date,
            to_date=to_date,
        )


# Instancia singleton del servicio
reservation_service = ReservationService()
