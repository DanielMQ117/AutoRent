"""Esquemas Pydantic v2 para autenticación y sesión de agencias/usuarios."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AgencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_agencia: Optional[int] = None
    codigo_agencia: str
    nombre_comercial: str
    ruc_nit: str
    telefono: str = ""
    email: Optional[str] = None
    direccion: str = ""
    activo: bool = True
    fecha_creacion: Optional[datetime] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    tenant_id: int


class UserSessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    tenant_id: int
    id_rol: int
    username: str
    nombre_completo: str
    email: str
    activo: bool
    rol_nombre: Optional[str] = None
    agencia_nombre: Optional[str] = None
    agencia_codigo: Optional[str] = None


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    user: UserSessionInfo
