"""Servicio de lógica de negocio para Mantenimiento de Flota y Taller Mecánico (BLL)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.core.exceptions import (
    BusinessRuleViolationError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import get_logger
from src.core.session import session
from src.domain.enums import MaintenanceStatus, MaintenanceType, VehicleStatus
from src.domain.models import Maintenance, Vehicle
from src.repositories.maintenance_repository import MaintenanceRepository
from src.repositories.vehicle_repository import VehicleRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


def _to_naive_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Normaliza un objeto datetime eliminando información de zona horaria para comparaciones seguras."""
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class MaintenanceService(BaseService):
    """Orquesta el ciclo de vida de las órdenes de servicio en taller mecánico (RF-31, RF-32, RF-33)."""

    def __init__(
        self,
        maintenance_repo: Optional[MaintenanceRepository] = None,
        vehicle_repo: Optional[VehicleRepository] = None,
    ) -> None:
        super().__init__()
        self.maintenance_repo = maintenance_repo or MaintenanceRepository()
        self.vehicle_repo = vehicle_repo or VehicleRepository()

    def validate_new_maintenance(
        self,
        vehicle: Vehicle,
        maintenance: Maintenance,
    ) -> None:
        """Valida que el vehículo y los datos de la orden cumplan las restricciones operativas (RF-31, RF-32)."""
        # 1. Vehículo activo y no de baja
        if not vehicle.activo or vehicle.estado == VehicleStatus.DE_BAJA:
            raise BusinessRuleViolationError(
                f"El vehículo '{vehicle.placa}' se encuentra dado de baja o inactivo en el sistema.",
                code="VEHICLE_DECOMMISSIONED",
            )

        # 2. Vehículo no alquilado (RF-32)
        if vehicle.estado == VehicleStatus.ALQUILADO:
            raise BusinessRuleViolationError(
                f"El vehículo '{vehicle.placa}' está actualmente ALQUILADO en un contrato activo. "
                "Debe recepcionarse formalmente antes de remitirlo a taller.",
                code="VEHICLE_CURRENTLY_RENTED",
            )

        # 3. No duplicar órdenes activas simultáneas en taller para el mismo vehículo
        active_order = self.maintenance_repo.get_active_by_vehicle(vehicle.id_vehiculo)
        if active_order:
            raise BusinessRuleViolationError(
                f"El vehículo '{vehicle.placa}' ya tiene una orden abierta en taller (ID #{active_order.id_mantenimiento}). "
                "Debe finalizar o cancelar la orden existente antes de generar una nueva.",
                code="MAINTENANCE_ALREADY_ACTIVE",
            )

        # 4. Validación de kilometraje de ingreso
        if maintenance.kilometraje_entrada < vehicle.kilometraje_actual:
            raise ValidationError(
                f"El kilometraje de entrada al taller ({maintenance.kilometraje_entrada:,} km) no puede ser inferior "
                f"al odómetro registrado del vehículo ({vehicle.kilometraje_actual:,} km).",
                code="ODOMETER_ROLLBACK_ATTEMPT",
            )

        # 5. Validación de taller y descripción
        if not maintenance.taller_servicio or not maintenance.taller_servicio.strip():
            raise ValidationError(
                "Debe especificar el nombre o razón social del taller mecánico / proveedor de servicio.",
                code="WORKSHOP_REQUIRED",
            )

        if not maintenance.descripcion_trabajo or not maintenance.descripcion_trabajo.strip():
            raise ValidationError(
                "Debe ingresar el detalle del diagnóstico o trabajo requerido en el vehículo.",
                code="WORK_DESCRIPTION_REQUIRED",
            )

        # 6. Validación de costo estimado inicial
        if maintenance.costo_total < Decimal("0.00"):
            raise ValidationError(
                "El costo estimado del mantenimiento no puede ser negativo.",
                code="NEGATIVE_COST",
            )

        # 7. Validación de fecha estimada de salida
        f_ingreso = maintenance.fecha_ingreso or datetime.now()
        f_salida = maintenance.fecha_salida_estimada or date.today()
        if f_salida < f_ingreso.date():
            raise ValidationError(
                f"La fecha estimada de salida ({f_salida}) no puede ser anterior a la fecha de ingreso ({f_ingreso.date()}).",
                code="INVALID_EXIT_DATE",
            )

    def create_maintenance_order(self, maintenance: Maintenance) -> Maintenance:
        """Registra una nueva orden de servicio y bloquea el vehículo en estado EN_MANTENIMIENTO (RF-31, RF-32)."""
        vehicle = self.vehicle_repo.get_by_id(maintenance.id_vehiculo)
        if not vehicle:
            raise RecordNotFoundError(
                f"No se encontró ningún vehículo con ID {maintenance.id_vehiculo}.",
                code="VEHICLE_NOT_FOUND",
            )

        # Validaciones de reglas de negocio
        self.validate_new_maintenance(vehicle, maintenance)

        # Normalización y asignación de usuario
        maintenance.taller_servicio = maintenance.taller_servicio.strip()
        maintenance.descripcion_trabajo = maintenance.descripcion_trabajo.strip()
        maintenance.estado = MaintenanceStatus.EN_TALLER
        if not maintenance.fecha_ingreso:
            maintenance.fecha_ingreso = datetime.now()

        # Asignar usuario de sesión activa si no viene asignado
        if not maintenance.id_usuario:
            current_user = session.current_user
            if current_user and current_user.id_usuario:
                maintenance.id_usuario = current_user.id_usuario
            else:
                maintenance.id_usuario = 1  # Fallback a usuario administrador inicial

        with self.run_in_transaction() as conn:
            # 1. Crear registro de mantenimiento
            created = self.maintenance_repo.create(maintenance, conn=conn)

            # 2. Bloquear vehículo actualizando su estado a EN_MANTENIMIENTO (RF-32)
            self.vehicle_repo.update_status(vehicle.id_vehiculo, VehicleStatus.EN_MANTENIMIENTO, conn=conn)

        logger.info(
            "Vehículo %s (ID %s) enviado a taller con Orden #%s bajo tipo %s",
            vehicle.placa,
            vehicle.id_vehiculo,
            created.id_mantenimiento,
            created.tipo_mantenimiento.value,
        )

        return self.get_maintenance(created.id_mantenimiento)

    def complete_maintenance(
        self,
        id_mantenimiento: int,
        fecha_salida_real: Optional[datetime] = None,
        costo_total: Optional[Decimal] = None,
        nuevo_km_proximo_mantenimiento: Optional[int] = None,
        notas_cierre: Optional[str] = None,
    ) -> Maintenance:
        """Finaliza una orden de mantenimiento, consolida costos y reactiva el vehículo a DISPONIBLE (RF-33)."""
        maintenance = self.get_maintenance(id_mantenimiento)

        if maintenance.estado != MaintenanceStatus.EN_TALLER:
            raise InvalidStateTransitionError(
                f"La orden #{id_mantenimiento} no está activa en taller (estado actual: '{maintenance.estado.value}'). "
                "Solo las órdenes 'EN_TALLER' pueden finalizarse.",
                code="MAINTENANCE_NOT_IN_WORKSHOP",
            )

        # Normalización y validación de fecha real
        fecha_salida = fecha_salida_real or datetime.now()
        f_ingreso_naive = _to_naive_datetime(maintenance.fecha_ingreso)
        f_salida_naive = _to_naive_datetime(fecha_salida)

        if f_ingreso_naive and f_salida_naive and f_salida_naive < f_ingreso_naive:
            raise ValidationError(
                f"La fecha de salida real ({fecha_salida}) no puede ser anterior a la fecha de ingreso ({maintenance.fecha_ingreso}).",
                code="INVALID_REAL_EXIT_DATE",
            )

        # Costo total auditado
        costo = costo_total if costo_total is not None else maintenance.costo_total
        if costo < Decimal("0.00"):
            raise ValidationError(
                "El costo total del mantenimiento no puede ser negativo.",
                code="NEGATIVE_TOTAL_COST",
            )

        vehicle = self.vehicle_repo.get_by_id(maintenance.id_vehiculo)
        if not vehicle:
            raise RecordNotFoundError(
                f"No se encontró el vehículo asociado ID {maintenance.id_vehiculo}.",
                code="VEHICLE_NOT_FOUND",
            )

        # Reprogramación de odómetro para el próximo mantenimiento (RF-33)
        if nuevo_km_proximo_mantenimiento is not None:
            if nuevo_km_proximo_mantenimiento <= vehicle.kilometraje_actual:
                raise ValidationError(
                    f"El nuevo kilometraje para el próximo servicio ({nuevo_km_proximo_mantenimiento:,} km) "
                    f"debe ser superior al odómetro actual ({vehicle.kilometraje_actual:,} km).",
                    code="INVALID_NEXT_MAINTENANCE_KM",
                )
        else:
            # Si no se especifica y es PREVENTIVO, se reprograma automáticamente +5,000 km
            if maintenance.tipo_mantenimiento == MaintenanceType.PREVENTIVO:
                nuevo_km_proximo_mantenimiento = vehicle.kilometraje_actual + 5000

        with self.run_in_transaction() as conn:
            # 1. Marcar orden como FINALIZADO
            self.maintenance_repo.complete(
                id_mantenimiento=id_mantenimiento,
                fecha_salida_real=fecha_salida,
                costo_total=costo,
                descripcion_adicional=notas_cierre,
                conn=conn,
            )

            # 2. Reactivar vehículo a DISPONIBLE y actualizar km_proximo_mantenimiento (RF-33)
            self.vehicle_repo.update_maintenance_release(
                id_vehiculo=maintenance.id_vehiculo,
                nuevo_km_proximo_mantenimiento=nuevo_km_proximo_mantenimiento,
                conn=conn,
            )

        logger.info(
            "Orden de mantenimiento #%s finalizada con éxito. Vehículo ID %s restaurado a DISPONIBLE (Nuevo km próx: %s).",
            id_mantenimiento,
            maintenance.id_vehiculo,
            nuevo_km_proximo_mantenimiento,
        )

        return self.get_maintenance(id_mantenimiento)

    def cancel_maintenance(
        self,
        id_mantenimiento: int,
        motivo: Optional[str] = None,
    ) -> Maintenance:
        """Cancela una orden de mantenimiento y reactiva el vehículo a DISPONIBLE si no tiene otras órdenes pendientes."""
        maintenance = self.get_maintenance(id_mantenimiento)

        if maintenance.estado != MaintenanceStatus.EN_TALLER:
            raise InvalidStateTransitionError(
                f"La orden #{id_mantenimiento} no se encuentra activa en taller (estado: '{maintenance.estado.value}'). "
                "Solo las órdenes 'EN_TALLER' pueden cancelarse.",
                code="MAINTENANCE_CANNOT_BE_CANCELLED",
            )

        with self.run_in_transaction() as conn:
            # 1. Cancelar la orden
            self.maintenance_repo.cancel(
                id_mantenimiento=id_mantenimiento,
                motivo=motivo,
                conn=conn,
            )

            # 2. Reactivar vehículo si no hay otras órdenes abiertas
            active_other = self.maintenance_repo.get_active_by_vehicle(maintenance.id_vehiculo, conn=conn)
            if not active_other:
                self.vehicle_repo.update_status(maintenance.id_vehiculo, VehicleStatus.DISPONIBLE, conn=conn)

        logger.info(
            "Orden de mantenimiento #%s cancelada. Vehículo ID %s restaurado a DISPONIBLE.",
            id_mantenimiento,
            maintenance.id_vehiculo,
        )

        return self.get_maintenance(id_mantenimiento)

    def get_maintenance(self, id_mantenimiento: int) -> Maintenance:
        """Recupera una orden de mantenimiento completa por su ID."""
        order = self.maintenance_repo.get_by_id(id_mantenimiento)
        if not order:
            raise RecordNotFoundError(
                f"No se encontró ninguna orden de mantenimiento con ID {id_mantenimiento}.",
                code="MAINTENANCE_NOT_FOUND",
            )
        return order

    def list_maintenances(
        self,
        search: str = "",
        status: Optional[str] = None,
        maintenance_type: Optional[str] = None,
        vehicle_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Maintenance]:
        """Consulta el histórico o lista activa de órdenes de mantenimiento con filtros."""
        return self.maintenance_repo.list_all(
            search=search,
            status=status,
            maintenance_type=maintenance_type,
            vehicle_id=vehicle_id,
            limit=limit,
        )

    def get_active_maintenance_for_vehicle(self, id_vehiculo: int) -> Optional[Maintenance]:
        """Obtiene la orden activa en taller de un vehículo específico si existe."""
        return self.maintenance_repo.get_active_by_vehicle(id_vehiculo)

    def get_maintenance_kpis(self) -> Dict[str, Any]:
        """Genera métricas consolidadas del módulo de taller y mantenimiento para KPIs."""
        total_ordenes = self.maintenance_repo.count_maintenances()
        en_taller = self.maintenance_repo.count_maintenances(status="EN_TALLER")
        finalizadas = self.maintenance_repo.count_maintenances(status="FINALIZADO")
        gasto_total = self.maintenance_repo.get_total_expenses()

        return {
            "total_ordenes": total_ordenes,
            "en_taller": en_taller,
            "finalizadas": finalizadas,
            "gasto_total": gasto_total,
        }

    def get_eligible_vehicles_for_maintenance(self) -> List[Vehicle]:
        """Retorna vehículos que pueden ser ingresados a taller (no alquilados, no de baja)."""
        all_vehicles = self.vehicle_repo.list_all(active_only=True)
        return [
            v for v in all_vehicles
            if v.estado not in (VehicleStatus.ALQUILADO, VehicleStatus.DE_BAJA)
        ]


# Instancia singleton para uso en controladores y vistas
maintenance_service = MaintenanceService()
