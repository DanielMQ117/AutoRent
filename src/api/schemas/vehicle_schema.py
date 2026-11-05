"""Esquemas Pydantic v2 para gestión de flota vehicular, marcas, modelos y categorías."""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from src.domain.enums import VehicleStatus


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_marca: int
    nombre: str


class VehicleModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_modelo: int
    id_marca: int
    nombre: str
    anio: int
    tipo_transmision: str
    capacidad_pasajeros: int
    marca_nombre: Optional[str] = None


class VehicleCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: int
    tenant_id: int
    nombre: str
    descripcion: Optional[str] = None
    deposito_garantia_sugerido: Decimal
    tarifa_base_diaria: Decimal


class VehicleCreateRequest(BaseModel):
    id_modelo: int
    id_categoria: int
    placa: str
    vin: str
    color: str
    kilometraje_actual: int = 0
    nivel_combustible_actual: Decimal = Decimal("1.00")
    estado: VehicleStatus = VehicleStatus.DISPONIBLE
    km_proximo_mantenimiento: int = 5000
    activo: bool = True


class VehicleUpdateRequest(BaseModel):
    id_modelo: int
    id_categoria: int
    placa: str
    vin: str
    color: str
    kilometraje_actual: int = 0
    nivel_combustible_actual: Decimal = Decimal("1.00")
    estado: VehicleStatus = VehicleStatus.DISPONIBLE
    km_proximo_mantenimiento: int = 5000
    activo: bool = True


class VehicleStatusUpdateRequest(BaseModel):
    estado: VehicleStatus


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_vehiculo: int
    tenant_id: int
    id_modelo: int
    id_categoria: int
    placa: str
    vin: str
    color: str
    kilometraje_actual: int
    nivel_combustible_actual: Decimal
    estado: VehicleStatus
    km_proximo_mantenimiento: int
    activo: bool
    modelo_nombre: Optional[str] = None
    categoria_nombre: Optional[str] = None
    marca_nombre: Optional[str] = None
    anio: Optional[int] = None
    tarifa_base_diaria: Optional[Decimal] = None
