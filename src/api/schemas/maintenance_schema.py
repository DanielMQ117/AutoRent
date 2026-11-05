"""Esquemas Pydantic v2 para órdenes de mantenimiento preventivo y correctivo."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import MaintenanceStatus, MaintenanceType


class MaintenanceCreateRequest(BaseModel):
    id_vehiculo: int
    tipo_mantenimiento: MaintenanceType = MaintenanceType.PREVENTIVO
    fecha_ingreso: Optional[datetime] = None
    fecha_salida_estimada: Optional[date] = None
    kilometraje_entrada: int
    taller_servicio: str = Field(..., max_length=100)
    descripcion_trabajo: str
    costo_total: Decimal = Decimal("0.00")


class MaintenanceCompleteRequest(BaseModel):
    fecha_salida_real: Optional[datetime] = None
    costo_total: Optional[Decimal] = None
    nuevo_km_proximo_mantenimiento: Optional[int] = None
    notas_cierre: Optional[str] = None


class MaintenanceCancelRequest(BaseModel):
    motivo: Optional[str] = None


class MaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mantenimiento: int
    tenant_id: int
    id_vehiculo: int
    tipo_mantenimiento: MaintenanceType
    fecha_ingreso: Optional[datetime] = None
    fecha_salida_estimada: Optional[date] = None
    fecha_salida_real: Optional[datetime] = None
    kilometraje_entrada: int
    taller_servicio: str
    descripcion_trabajo: str
    costo_total: Decimal
    estado: MaintenanceStatus
    id_usuario: int
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    vehiculo_categoria: Optional[str] = None
    vehiculo_kilometraje_actual: Optional[int] = 0
    km_proximo_mantenimiento_actual: Optional[int] = 0
    usuario_nombre: Optional[str] = None
    duracion_dias: Optional[int] = None
    esta_completado: Optional[bool] = None
