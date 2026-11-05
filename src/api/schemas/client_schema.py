"""Esquemas Pydantic v2 para gestión de clientes y licencias de conducir."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import ClientStatus, ClientType


class DriverLicenseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_licencia: Optional[int] = None
    tenant_id: Optional[int] = None
    id_cliente: Optional[int] = 0
    numero_licencia: str = Field(..., max_length=40)
    categoria_licencia: str = Field(..., max_length=30)
    fecha_emision: date
    fecha_vencimiento: date
    pais_emision: str = Field("Nicaragua", max_length=50)


class ClientCreateRequest(BaseModel):
    tipo_persona: ClientType = ClientType.NATURAL
    identificacion: str = Field(..., max_length=30)
    nombres: str = Field(..., max_length=80)
    apellidos: str = Field(..., max_length=80)
    telefono: str = Field(..., max_length=25)
    email: str = Field(..., max_length=100)
    direccion: str
    estado_cliente: ClientStatus = ClientStatus.ACTIVO
    licencia: Optional[DriverLicenseSchema] = None


class ClientUpdateRequest(BaseModel):
    tipo_persona: ClientType = ClientType.NATURAL
    identificacion: str = Field(..., max_length=30)
    nombres: str = Field(..., max_length=80)
    apellidos: str = Field(..., max_length=80)
    telefono: str = Field(..., max_length=25)
    email: str = Field(..., max_length=100)
    direccion: str
    estado_cliente: ClientStatus = ClientStatus.ACTIVO
    licencia: Optional[DriverLicenseSchema] = None


class ClientStatusUpdateRequest(BaseModel):
    estado_cliente: ClientStatus


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cliente: int
    tenant_id: int
    tipo_persona: ClientType
    identificacion: str
    nombres: str
    apellidos: str
    nombre_completo: Optional[str] = None
    telefono: str
    email: str
    direccion: str
    estado_cliente: ClientStatus
    fecha_registro: Optional[datetime] = None
    licencia: Optional[DriverLicenseSchema] = None
