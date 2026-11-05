"""Esquemas Pydantic v2 para gestión de reservaciones de vehículos."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from src.domain.enums import ReservationStatus


class ReservationCreateRequest(BaseModel):
    id_cliente: int
    id_categoria: int
    id_vehiculo: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    monto_anticipo: Decimal = Decimal("0.00")
    estado: ReservationStatus = ReservationStatus.PENDIENTE


class ReservationUpdateRequest(BaseModel):
    id_cliente: int
    id_categoria: int
    id_vehiculo: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    monto_anticipo: Decimal = Decimal("0.00")
    estado: ReservationStatus = ReservationStatus.PENDIENTE


class ReservationCancelRequest(BaseModel):
    motivo: Optional[str] = None


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_reserva: int
    tenant_id: int
    codigo_reserva: str
    id_cliente: int
    id_categoria: int
    id_vehiculo: Optional[int] = None
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    monto_anticipo: Decimal
    estado: ReservationStatus
    id_usuario: int
    fecha_creacion: Optional[datetime] = None
    cliente_nombre: Optional[str] = None
    cliente_identificacion: Optional[str] = None
    categoria_nombre: Optional[str] = None
    tarifa_base_diaria: Optional[Decimal] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    usuario_nombre: Optional[str] = None
    duracion_dias: Optional[int] = None
    costo_estimado: Optional[Decimal] = None
