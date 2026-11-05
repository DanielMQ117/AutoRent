"""Router FastAPI para Gestión de Reservas y Disponibilidad Temporal."""

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.reservation_schema import (
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationResponse,
    ReservationUpdateRequest,
)
from src.api.schemas.vehicle_schema import VehicleResponse
from src.domain.models import Reservation, User
from src.services.reservation_service import reservation_service

router = APIRouter(prefix="/api/v1/reservations", tags=["Reservas"])


@router.get("/availability/check")
def check_availability(
    id_categoria: int = Query(..., description="ID de la categoría solicitada"),
    start_dt: datetime = Query(..., description="Fecha y hora de inicio"),
    end_dt: datetime = Query(..., description="Fecha y hora de fin"),
    id_vehiculo: Optional[int] = Query(default=None, description="ID de vehículo opcional"),
    exclude_reservation_id: Optional[int] = Query(default=None, description="ID de reserva a excluir en edición"),
    current_user: User = Depends(require_module_permission("reservas")),
) -> dict[str, Any]:
    """Verifica la disponibilidad temporal de flota para un rango de fechas."""
    is_avail, vehicles, msg = reservation_service.check_availability(
        id_categoria=id_categoria,
        start_dt=start_dt,
        end_dt=end_dt,
        id_vehiculo=id_vehiculo,
        exclude_reservation_id=exclude_reservation_id,
    )
    return {
        "available": is_avail,
        "vehicles": [VehicleResponse.model_validate(v).model_dump(mode="json") for v in vehicles],
        "message": msg,
    }


@router.get("", response_model=List[ReservationResponse])
def list_reservations(
    search: Optional[str] = Query(default=None, description="Búsqueda por código, cliente o placa"),
    status: Optional[str] = Query(default=None, description="Filtro por estado de reserva"),
    client_id: Optional[int] = Query(default=None, description="Filtro por ID de cliente"),
    category_id: Optional[int] = Query(default=None, description="Filtro por ID de categoría"),
    current_user: User = Depends(require_module_permission("reservas")),
) -> List[ReservationResponse]:
    """Lista las reservas registradas en la agencia activa."""
    reservations = reservation_service.list_reservations(
        search=search,
        status=status,
        client_id=client_id,
        category_id=category_id,
    )
    return [ReservationResponse.model_validate(r) for r in reservations]


@router.get("/{id_reserva}", response_model=ReservationResponse)
def get_reservation(
    id_reserva: int,
    current_user: User = Depends(require_module_permission("reservas")),
) -> ReservationResponse:
    """Obtiene el detalle de una reserva por su ID."""
    res = reservation_service.get_reservation(id_reserva)
    return ReservationResponse.model_validate(res)


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    req: ReservationCreateRequest,
    current_user: User = Depends(require_module_permission("reservas")),
) -> ReservationResponse:
    """Crea una nueva reserva verificando elegibilidad del cliente y disponibilidad de flota."""
    res = Reservation(
        id_cliente=req.id_cliente,
        id_categoria=req.id_categoria,
        id_vehiculo=req.id_vehiculo,
        fecha_hora_inicio=req.fecha_hora_inicio,
        fecha_hora_fin=req.fecha_hora_fin,
        monto_anticipo=req.monto_anticipo,
        estado=req.estado,
        id_usuario=current_user.id_usuario or 0,
    )
    created = reservation_service.create_reservation(res)
    return ReservationResponse.model_validate(created)


@router.put("/{id_reserva}", response_model=ReservationResponse)
def update_reservation(
    id_reserva: int,
    req: ReservationUpdateRequest,
    current_user: User = Depends(require_module_permission("reservas")),
) -> ReservationResponse:
    """Actualiza los términos de una reserva existente."""
    res = Reservation(
        id_reserva=id_reserva,
        id_cliente=req.id_cliente,
        id_categoria=req.id_categoria,
        id_vehiculo=req.id_vehiculo,
        fecha_hora_inicio=req.fecha_hora_inicio,
        fecha_hora_fin=req.fecha_hora_fin,
        monto_anticipo=req.monto_anticipo,
        estado=req.estado,
        id_usuario=current_user.id_usuario or 0,
    )
    updated = reservation_service.update_reservation(res)
    return ReservationResponse.model_validate(updated)


@router.post("/{id_reserva}/confirm", response_model=ReservationResponse)
def confirm_reservation(
    id_reserva: int,
    current_user: User = Depends(require_module_permission("reservas")),
) -> ReservationResponse:
    """Confirma una reserva que se encontraba en estado PENDIENTE."""
    reservation_service.confirm_reservation(id_reserva)
    updated = reservation_service.get_reservation(id_reserva)
    return ReservationResponse.model_validate(updated)


@router.post("/{id_reserva}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    id_reserva: int,
    req: Optional[ReservationCancelRequest] = Body(default=None),
    current_user: User = Depends(require_module_permission("reservas")),
) -> ReservationResponse:
    """Cancela una reserva activa (PENDIENTE o CONFIRMADA)."""
    reservation_service.cancel_reservation(id_reserva, motivo=req.motivo if req else None)
    updated = reservation_service.get_reservation(id_reserva)
    return ReservationResponse.model_validate(updated)
