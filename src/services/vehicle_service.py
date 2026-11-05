"""Servicio de lógica de negocio para la gestión de Flota y Vehículos (BLL)."""

from decimal import Decimal
from typing import Any, List, Optional
from src.api_client import ApiClientError, api_client
from src.core.exceptions import (
    BusinessRuleViolationError,
    DuplicateRecordError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import get_logger
from src.domain.enums import VehicleStatus
from src.domain.models import Brand, Vehicle, VehicleCategory, VehicleModel
from src.repositories.orm.vehicle_orm_repository import VehicleORMRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


class VehicleService(BaseService):
    """Servicio empresarial que orquesta validaciones, reglas de negocio y estados de la flota de vehículos."""

    def __init__(self, vehicle_repo: Optional[VehicleORMRepository] = None) -> None:
        super().__init__()
        self.vehicle_repo = vehicle_repo or VehicleORMRepository(self.db)

    @staticmethod
    def _build_remote_payload(vehicle: Vehicle) -> dict[str, Any]:
        """Construye el diccionario JSON de un vehículo para enviar a la API REST."""
        return {
            "id_modelo": int(vehicle.id_modelo or 0),
            "id_categoria": int(vehicle.id_categoria or 0),
            "placa": (vehicle.placa or "").strip().upper(),
            "vin": (vehicle.vin or "").strip().upper(),
            "color": (vehicle.color or "").strip().title(),
            "kilometraje_actual": int(vehicle.kilometraje_actual or 0),
            "nivel_combustible_actual": str(vehicle.nivel_combustible_actual),
            "estado": vehicle.estado.value if isinstance(vehicle.estado, VehicleStatus) else str(vehicle.estado),
            "km_proximo_mantenimiento": int(vehicle.km_proximo_mantenimiento or 5000),
            "activo": bool(vehicle.activo),
        }

    def _validate_vehicle_fields(
        self,
        vehicle: Vehicle,
        existing: Optional[Vehicle] = None,
        is_update: bool = False,
    ) -> None:
        """Aplica validaciones estrictas y reglas de integridad sobre los atributos del vehículo."""
        # 1. Campos obligatorios
        self.validate_positive("Modelo de Vehículo", vehicle.id_modelo)
        self.validate_positive("Categoría de Vehículo", vehicle.id_categoria)
        self.validate_required("Número de Placa", vehicle.placa)
        self.validate_required("Número de Chasis (VIN)", vehicle.vin)
        self.validate_required("Color", vehicle.color)

        clean_placa = vehicle.placa.strip().upper()
        clean_vin = vehicle.vin.strip().upper()

        # 2. Formato de VIN (estándar internacional de 17 caracteres alfanuméricos)
        if len(clean_vin) != 17 or not clean_vin.isalnum():
            raise ValidationError(
                f"El código VIN '{clean_vin}' debe contener exactamente 17 caracteres alfanuméricos.",
                code="INVALID_VIN_FORMAT",
            )

        # 3. Validación de Odómetro y Prevención de Adulteración
        if vehicle.kilometraje_actual < 0:
            raise ValidationError("El kilometraje actual no puede ser un valor negativo.", code="NEGATIVE_KILOMETERS")

        if is_update and existing and vehicle.kilometraje_actual < existing.kilometraje_actual:
            raise ValidationError(
                f"Fraude de odómetro detectado: El nuevo kilometraje ({vehicle.kilometraje_actual:,} km) "
                f"no puede ser menor que el registrado previamente ({existing.kilometraje_actual:,} km).",
                code="ODOMETER_ROLLBACK_ATTEMPT",
            )

        # 4. Nivel de combustible (debe estar entre 0.00 y 1.00)
        fuel = Decimal(str(vehicle.nivel_combustible_actual))
        if fuel < Decimal("0.00") or fuel > Decimal("1.00"):
            raise ValidationError(
                f"El nivel de combustible ({fuel}) debe estar comprendido entre 0.00 (Vacío) y 1.00 (Lleno).",
                code="INVALID_FUEL_LEVEL",
            )

        # 5. Mantenimiento programado
        if vehicle.km_proximo_mantenimiento <= 0:
            raise ValidationError(
                "El kilometraje del próximo mantenimiento debe ser un número entero positivo.",
                code="INVALID_MAINTENANCE_KM",
            )

        # 6. Unicidad de Placa
        found_by_placa = self.vehicle_repo.get_by_placa(clean_placa)
        if found_by_placa:
            if not is_update or found_by_placa.id_vehiculo != vehicle.id_vehiculo:
                raise DuplicateRecordError(
                    f"Ya existe un vehículo registrado con la placa '{clean_placa}'.",
                    code="DUPLICATE_LICENSE_PLATE",
                )

        # 7. Unicidad de VIN
        found_by_vin = self.vehicle_repo.get_by_vin(clean_vin)
        if found_by_vin:
            if not is_update or found_by_vin.id_vehiculo != vehicle.id_vehiculo:
                raise DuplicateRecordError(
                    f"Ya existe un vehículo registrado con el código VIN '{clean_vin}'.",
                    code="DUPLICATE_VIN",
                )

    def create_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """Registra un nuevo vehículo en la flota institucional dentro de una transacción."""
        vehicle.placa = vehicle.placa.strip().upper()
        vehicle.vin = vehicle.vin.strip().upper()
        vehicle.color = vehicle.color.strip().title()

        if api_client.remote_mode:
            payload = self._build_remote_payload(vehicle)
            try:
                data = api_client.create_vehicle(payload)
                return api_client.to_vehicle(data)
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        self._validate_vehicle_fields(vehicle, is_update=False)

        with self.run_in_transaction() as conn:
            created = self.vehicle_repo.create(vehicle, conn=conn)

        self.logger.info("Vehículo placa '%s' registrado exitosamente con ID %s", created.placa, created.id_vehiculo)
        return self.get_vehicle(created.id_vehiculo)

    def update_vehicle(self, vehicle: Vehicle) -> Vehicle:
        """Actualiza las especificaciones técnicas u operativas de un vehículo."""
        if not vehicle.id_vehiculo:
            raise ValidationError("El ID del vehículo es obligatorio para la actualización.", code="VEHICLE_ID_REQUIRED")

        if api_client.remote_mode:
            vehicle.placa = vehicle.placa.strip().upper()
            vehicle.vin = vehicle.vin.strip().upper()
            vehicle.color = vehicle.color.strip().title()
            payload = self._build_remote_payload(vehicle)
            try:
                data = api_client.update_vehicle(vehicle.id_vehiculo, payload)
                return api_client.to_vehicle(data)
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        existing = self.get_vehicle(vehicle.id_vehiculo)
        vehicle.placa = vehicle.placa.strip().upper()
        vehicle.vin = vehicle.vin.strip().upper()
        vehicle.color = vehicle.color.strip().title()

        self._validate_vehicle_fields(vehicle, existing=existing, is_update=True)

        with self.run_in_transaction() as conn:
            self.vehicle_repo.update(vehicle, conn=conn)

        self.logger.info("Vehículo ID %s actualizado con éxito.", vehicle.id_vehiculo)
        return self.get_vehicle(vehicle.id_vehiculo)

    def get_vehicle(self, id_vehiculo: int) -> Vehicle:
        """Recupera la ficha técnica completa de un vehículo por su ID."""
        if api_client.remote_mode:
            try:
                data = api_client.get_vehicle(id_vehiculo)
                return api_client.to_vehicle(data)
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        vehicle = self.vehicle_repo.get_by_id(id_vehiculo)
        if not vehicle:
            raise RecordNotFoundError(
                f"No se encontró ningún vehículo con el ID {id_vehiculo}.",
                code="VEHICLE_NOT_FOUND",
            )
        return vehicle

    def list_vehicles(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        active_only: bool = False,
    ) -> List[Vehicle]:
        """Obtiene la lista de vehículos filtrados según los criterios solicitados."""
        if api_client.remote_mode:
            try:
                rows = api_client.list_vehicles(
                    search=search,
                    status=status,
                    category_id=category_id,
                    active_only=active_only,
                )
                return [api_client.to_vehicle(r) for r in rows]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        return self.vehicle_repo.list_all(
            search=search,
            status=status,
            category_id=category_id,
            active_only=active_only,
        )

    def change_status(self, id_vehiculo: int, new_status: VehicleStatus) -> None:
        """Gestiona las transiciones de estado de un vehículo aplicando reglas de negocio estrictas.

        Estados soportados:
        - DISPONIBLE: Listo para asignación comercial o reserva.
        - ALQUILADO: En posesión del cliente bajo contrato activo.
        - EN_MANTENIMIENTO: En revisión preventiva o correctiva en taller.
        - DE_BAJA: Retirado de la flota activa.
        """
        if api_client.remote_mode:
            st_val = new_status.value if isinstance(new_status, VehicleStatus) else str(new_status)
            try:
                api_client.change_vehicle_status(id_vehiculo, st_val)
                return
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        vehicle = self.get_vehicle(id_vehiculo)
        current_status = vehicle.estado

        if current_status == new_status:
            self.logger.info("El vehículo ID %s ya se encuentra en estado '%s'.", id_vehiculo, new_status.value)
            return

        # Validación de transiciones según el estado actual
        if current_status == VehicleStatus.ALQUILADO:
            if self.vehicle_repo.has_active_commitments(id_vehiculo):
                raise InvalidStateTransitionError(
                    f"No se puede cambiar el estado de '{current_status.value}' a '{new_status.value}' manualmente "
                    "mientras exista un contrato de alquiler activo. Debe procesarse la devolución e inspección correspondiente.",
                    code="CANNOT_OVERRIDE_RENTED_STATUS",
                )

        if new_status == VehicleStatus.ALQUILADO:
            if current_status == VehicleStatus.EN_MANTENIMIENTO:
                raise InvalidStateTransitionError(
                    "Un vehículo en mantenimiento no puede ser marcado directamente como ALQUILADO sin antes ser liberado a DISPONIBLE.",
                    code="INVALID_TRANSITION_WORKSHOP_TO_RENTED",
                )

        with self.run_in_transaction() as conn:
            self.vehicle_repo.update_status(id_vehiculo, new_status, conn=conn)

        self.logger.info(
            "Estado del vehículo ID %s (%s) modificado de '%s' a '%s'",
            id_vehiculo,
            vehicle.placa,
            current_status.value,
            new_status.value,
        )

    def delete_vehicle(self, id_vehiculo: int, force_soft_delete: bool = True) -> None:
        """Elimina o da de baja un vehículo salvaguardando la integridad referencial."""
        if api_client.remote_mode:
            try:
                api_client.delete_vehicle(id_vehiculo)
                return
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc

        vehicle = self.get_vehicle(id_vehiculo)

        if self.vehicle_repo.has_active_commitments(id_vehiculo):
            raise BusinessRuleViolationError(
                f"El vehículo '{vehicle.placa}' se encuentra vinculado a contratos o reservas activas y no puede ser dado de baja.",
                code="VEHICLE_HAS_ACTIVE_COMMITMENTS",
            )

        with self.run_in_transaction() as conn:
            if force_soft_delete or self.vehicle_repo.has_any_history(id_vehiculo):
                # Desactivación lógica (activo = False y estado = DE_BAJA)
                self.vehicle_repo.soft_delete(id_vehiculo, conn=conn)
                self.logger.info("Vehículo ID %s dado de baja lógicamente (DE_BAJA).", id_vehiculo)
            else:
                # Eliminación física si no tiene ningún registro histórico
                self.vehicle_repo.delete(id_vehiculo, conn=conn)
                self.logger.info("Vehículo ID %s eliminado físicamente de la base de datos.", id_vehiculo)

    # ------------------------------------------------------------------------
    # Métodos de catálogo auxiliar para alimentar los formularios UI
    # ------------------------------------------------------------------------

    def get_brands(self) -> List[Brand]:
        """Retorna las marcas de vehículos disponibles."""
        if api_client.remote_mode:
            try:
                rows = api_client.list_brands()
                return [api_client.to_brand(r) for r in rows]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc
        return self.vehicle_repo.list_brands()

    def get_models(self, id_marca: Optional[int] = None) -> List[VehicleModel]:
        """Retorna los modelos de vehículos filtrados por marca si aplica."""
        if api_client.remote_mode:
            try:
                rows = api_client.list_models(id_marca=id_marca)
                return [api_client.to_vehicle_model(r) for r in rows]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc
        return self.vehicle_repo.list_models(id_marca)

    def get_categories(self) -> List[VehicleCategory]:
        """Retorna las categorías tarifarias de vehículos."""
        if api_client.remote_mode:
            try:
                rows = api_client.list_categories()
                return [api_client.to_vehicle_category(r) for r in rows]
            except ApiClientError as exc:
                raise exc.to_domain_exception() from exc
        return self.vehicle_repo.list_categories()


# Instancia singleton para uso en controladores y vistas
vehicle_service = VehicleService()
