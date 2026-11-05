"""Router FastAPI para Gestión de Flota, Vehículos, Categorías, Marcas y Modelos."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.vehicle_schema import (
    BrandResponse,
    VehicleCategoryResponse,
    VehicleCreateRequest,
    VehicleModelResponse,
    VehicleResponse,
    VehicleStatusUpdateRequest,
    VehicleUpdateRequest,
)
from src.domain.models import User, Vehicle
from src.services.vehicle_service import vehicle_service

router = APIRouter(prefix="/api/v1/vehicles", tags=["Flota y Vehículos"])


@router.get("/brands", response_model=List[BrandResponse])
def list_brands(
    current_user: User = Depends(require_module_permission("flota")),
) -> List[BrandResponse]:
    """Retorna el catálogo de marcas de vehículos."""
    brands = vehicle_service.get_brands()
    return [BrandResponse.model_validate(b) for b in brands]


@router.get("/models", response_model=List[VehicleModelResponse])
def list_models(
    id_marca: Optional[int] = Query(default=None, description="Filtrar modelos por ID de marca"),
    current_user: User = Depends(require_module_permission("flota")),
) -> List[VehicleModelResponse]:
    """Retorna el catálogo de modelos de vehículos."""
    models = vehicle_service.get_models(id_marca=id_marca)
    return [VehicleModelResponse.model_validate(m) for m in models]


@router.get("/categories", response_model=List[VehicleCategoryResponse])
def list_categories(
    current_user: User = Depends(require_module_permission("flota")),
) -> List[VehicleCategoryResponse]:
    """Retorna las categorías tarifarias de vehículos de la agencia activa."""
    categories = vehicle_service.get_categories()
    return [VehicleCategoryResponse.model_validate(c) for c in categories]


@router.get("", response_model=List[VehicleResponse])
def list_vehicles(
    search: Optional[str] = Query(default=None, description="Búsqueda por placa, VIN, marca o modelo"),
    status: Optional[str] = Query(default=None, description="Filtro por estado operativo"),
    category_id: Optional[int] = Query(default=None, description="Filtro por categoría"),
    active_only: bool = Query(default=False, description="Solo vehículos activos"),
    current_user: User = Depends(require_module_permission("flota")),
) -> List[VehicleResponse]:
    """Lista la flota de vehículos de la agencia activa."""
    vehicles = vehicle_service.list_vehicles(
        search=search,
        status=status,
        category_id=category_id,
        active_only=active_only,
    )
    return [VehicleResponse.model_validate(v) for v in vehicles]


@router.get("/{id_vehiculo}", response_model=VehicleResponse)
def get_vehicle(
    id_vehiculo: int,
    current_user: User = Depends(require_module_permission("flota")),
) -> VehicleResponse:
    """Obtiene la ficha técnica de un vehículo por su ID."""
    vehicle = vehicle_service.get_vehicle(id_vehiculo)
    return VehicleResponse.model_validate(vehicle)


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    req: VehicleCreateRequest,
    current_user: User = Depends(require_module_permission("flota")),
) -> VehicleResponse:
    """Registra una nueva unidad vehicular en la flota de la agencia."""
    vehicle = Vehicle(
        id_modelo=req.id_modelo,
        id_categoria=req.id_categoria,
        placa=req.placa,
        vin=req.vin,
        color=req.color,
        kilometraje_actual=req.kilometraje_actual,
        nivel_combustible_actual=req.nivel_combustible_actual,
        estado=req.estado,
        km_proximo_mantenimiento=req.km_proximo_mantenimiento,
        activo=req.activo,
    )
    created = vehicle_service.create_vehicle(vehicle)
    return VehicleResponse.model_validate(created)


@router.put("/{id_vehiculo}", response_model=VehicleResponse)
def update_vehicle(
    id_vehiculo: int,
    req: VehicleUpdateRequest,
    current_user: User = Depends(require_module_permission("flota")),
) -> VehicleResponse:
    """Actualiza los datos técnicos y operativos de un vehículo."""
    vehicle = Vehicle(
        id_vehiculo=id_vehiculo,
        id_modelo=req.id_modelo,
        id_categoria=req.id_categoria,
        placa=req.placa,
        vin=req.vin,
        color=req.color,
        kilometraje_actual=req.kilometraje_actual,
        nivel_combustible_actual=req.nivel_combustible_actual,
        estado=req.estado,
        km_proximo_mantenimiento=req.km_proximo_mantenimiento,
        activo=req.activo,
    )
    updated = vehicle_service.update_vehicle(vehicle)
    return VehicleResponse.model_validate(updated)


@router.patch("/{id_vehiculo}/status", response_model=VehicleResponse)
def change_vehicle_status(
    id_vehiculo: int,
    req: VehicleStatusUpdateRequest,
    current_user: User = Depends(require_module_permission("flota")),
) -> VehicleResponse:
    """Cambia el estado operativo de un vehículo validando las reglas de transición."""
    vehicle_service.change_status(id_vehiculo, req.estado)
    updated = vehicle_service.get_vehicle(id_vehiculo)
    return VehicleResponse.model_validate(updated)


@router.delete("/{id_vehiculo}")
def delete_vehicle(
    id_vehiculo: int,
    current_user: User = Depends(require_module_permission("flota")),
) -> dict:
    """Da de baja lógica o elimina un vehículo sin compromisos activos."""
    vehicle_service.delete_vehicle(id_vehiculo)
    return {"status": "ok", "id_vehiculo": id_vehiculo}
