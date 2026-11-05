"""Router FastAPI para Órdenes de Mantenimiento Preventivo y Correctivo en Taller."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.maintenance_schema import (
    MaintenanceCancelRequest,
    MaintenanceCompleteRequest,
    MaintenanceCreateRequest,
    MaintenanceResponse,
)
from src.domain.models import Maintenance, User
from src.services.maintenance_service import maintenance_service

router = APIRouter(prefix="/api/v1/maintenances", tags=["Mantenimiento y Taller"])


@router.get("/kpis")
def get_maintenance_kpis(
    current_user: User = Depends(require_module_permission("mantenimientos")),
) -> Dict[str, Any]:
    """Obtiene los indicadores clave (KPIs) de mantenimiento y taller mecánico."""
    return maintenance_service.get_maintenance_kpis()


@router.get("", response_model=List[MaintenanceResponse])
def list_maintenances(
    search: str = Query(default="", description="Búsqueda por placa, taller o descripción"),
    status: Optional[str] = Query(default=None, description="Filtro por estado (EN_TALLER, FINALIZADO, CANCELADO)"),
    maintenance_type: Optional[str] = Query(default=None, description="Filtro por tipo (PREVENTIVO, CORRECTIVO)"),
    vehicle_id: Optional[int] = Query(default=None, description="Filtro por ID de vehículo"),
    current_user: User = Depends(require_module_permission("mantenimientos")),
) -> List[MaintenanceResponse]:
    """Lista las órdenes de mantenimiento de la agencia activa."""
    orders = maintenance_service.list_maintenances(
        search=search,
        status=status,
        maintenance_type=maintenance_type,
        vehicle_id=vehicle_id,
    )
    return [MaintenanceResponse.model_validate(o) for o in orders]


@router.get("/{id_mantenimiento}", response_model=MaintenanceResponse)
def get_maintenance(
    id_mantenimiento: int,
    current_user: User = Depends(require_module_permission("mantenimientos")),
) -> MaintenanceResponse:
    """Obtiene el detalle de una orden de mantenimiento por su ID."""
    order = maintenance_service.get_maintenance(id_mantenimiento)
    return MaintenanceResponse.model_validate(order)


@router.post("", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance(
    req: MaintenanceCreateRequest,
    current_user: User = Depends(require_module_permission("mantenimientos")),
) -> MaintenanceResponse:
    """Crea una orden de servicio en taller y bloquea el vehículo en estado EN_MANTENIMIENTO."""
    maint = Maintenance(
        id_vehiculo=req.id_vehiculo,
        tipo_mantenimiento=req.tipo_mantenimiento,
        fecha_ingreso=req.fecha_ingreso,
        fecha_salida_estimada=req.fecha_salida_estimada,
        kilometraje_entrada=req.kilometraje_entrada,
        taller_servicio=req.taller_servicio,
        descripcion_trabajo=req.descripcion_trabajo,
        costo_total=req.costo_total,
        id_usuario=current_user.id_usuario or 0,
    )
    created = maintenance_service.create_maintenance_order(maint)
    return MaintenanceResponse.model_validate(created)


@router.post("/{id_mantenimiento}/complete", response_model=MaintenanceResponse)
def complete_maintenance(
    id_mantenimiento: int,
    req: MaintenanceCompleteRequest,
    current_user: User = Depends(require_module_permission("mantenimientos")),
) -> MaintenanceResponse:
    """Finaliza una orden en taller, registra el costo real y libera el vehículo a DISPONIBLE."""
    completed = maintenance_service.complete_maintenance(
        id_mantenimiento,
        fecha_salida_real=req.fecha_salida_real,
        costo_total=req.costo_total,
        nuevo_km_proximo_mantenimiento=req.nuevo_km_proximo_mantenimiento,
        notas_cierre=req.notas_cierre,
    )
    return MaintenanceResponse.model_validate(completed)


@router.post("/{id_mantenimiento}/cancel", response_model=MaintenanceResponse)
def cancel_maintenance(
    id_mantenimiento: int,
    req: Optional[MaintenanceCancelRequest] = Body(default=None),
    current_user: User = Depends(require_module_permission("mantenimientos")),
) -> MaintenanceResponse:
    """Cancela una orden en taller y libera el vehículo a DISPONIBLE."""
    cancelled = maintenance_service.cancel_maintenance(
        id_mantenimiento,
        motivo=req.motivo if req else None,
    )
    return MaintenanceResponse.model_validate(cancelled)
