"""Esquemas Pydantic v2 para administración de usuarios, roles y bitácora de auditoría."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_rol: int
    nombre: str
    descripcion: str = ""


class UserCreateRequest(BaseModel):
    username: str
    password: str
    nombre_completo: str
    email: str
    id_rol: int
    activo: bool = True


class UserUpdateRequest(BaseModel):
    nombre_completo: str
    email: str
    id_rol: int
    activo: bool = True


class UserPasswordResetRequest(BaseModel):
    new_password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    tenant_id: int
    id_rol: int
    username: str
    nombre_completo: str
    email: str
    activo: bool
    fecha_creacion: Optional[datetime] = None
    rol_nombre: Optional[str] = None
    agencia_nombre: Optional[str] = None
    agencia_codigo: Optional[str] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_auditoria: int
    tenant_id: int
    id_usuario: Optional[int] = None
    username: str
    accion: str
    tabla_afectada: str
    id_registro: Optional[int] = None
    detalles: Optional[str] = None
    ip_origen: str = "127.0.0.1"
    fecha_registro: Optional[datetime] = None
