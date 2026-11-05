"""Router FastAPI para Administración de Usuarios, Roles RBAC y Bitácora de Auditoría."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.user_schema import (
    AuditLogResponse,
    RoleResponse,
    UserCreateRequest,
    UserPasswordResetRequest,
    UserResponse,
    UserUpdateRequest,
)
from src.domain.models import User
from src.services.user_service import user_service

router = APIRouter(prefix="/api/v1/users", tags=["Usuarios, Roles y Auditoría"])


@router.get("/roles", response_model=List[RoleResponse])
def list_roles(
    current_user: User = Depends(require_module_permission("usuarios")),
) -> List[RoleResponse]:
    """Lista los roles del sistema para control de acceso RBAC."""
    roles = user_service.list_roles()
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/kpis")
def get_user_kpis(
    current_user: User = Depends(require_module_permission("usuarios")),
) -> Dict[str, int]:
    """Retorna métricas cuantitativas de usuarios en la agencia activa."""
    return user_service.get_kpis()


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=150, ge=1, le=500, description="Límite de eventos"),
    accion: Optional[str] = Query(default=None, description="Filtrar por código de acción"),
    username: Optional[str] = Query(default=None, description="Filtrar por nombre de usuario"),
    tabla_afectada: Optional[str] = Query(default=None, description="Filtrar por tabla afectada"),
    current_user: User = Depends(require_module_permission("usuarios")),
) -> List[AuditLogResponse]:
    """Consulta la bitácora de auditoría de la agencia activa."""
    logs = user_service.get_audit_logs(
        limit=limit,
        accion=accion,
        username=username,
        tabla_afectada=tabla_afectada,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("", response_model=List[UserResponse])
def list_users(
    search: Optional[str] = Query(default=None, description="Búsqueda por username, nombre o correo"),
    id_rol: Optional[int] = Query(default=None, description="Filtrar por ID de rol"),
    activo: Optional[bool] = Query(default=None, description="Filtrar por estado activo/inactivo"),
    current_user: User = Depends(require_module_permission("usuarios")),
) -> List[UserResponse]:
    """Lista los usuarios registrados en la agencia activa."""
    users = user_service.list_users(search=search, id_rol=id_rol, activo=activo)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{id_usuario}", response_model=UserResponse)
def get_user(
    id_usuario: int,
    current_user: User = Depends(require_module_permission("usuarios")),
) -> UserResponse:
    """Obtiene los datos de un usuario por su ID."""
    user = user_service.get_user_by_id(id_usuario)
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreateRequest,
    current_user: User = Depends(require_module_permission("usuarios")),
) -> UserResponse:
    """Crea una nueva cuenta de usuario en la agencia activa."""
    created = user_service.create_user(
        username=req.username,
        password=req.password,
        nombre_completo=req.nombre_completo,
        email=req.email,
        id_rol=req.id_rol,
        activo=req.activo,
    )
    return UserResponse.model_validate(created)


@router.put("/{id_usuario}", response_model=UserResponse)
def update_user(
    id_usuario: int,
    req: UserUpdateRequest,
    current_user: User = Depends(require_module_permission("usuarios")),
) -> UserResponse:
    """Actualiza el perfil, rol y estado de un usuario existente."""
    updated = user_service.update_user(
        id_usuario=id_usuario,
        nombre_completo=req.nombre_completo,
        email=req.email,
        id_rol=req.id_rol,
        activo=req.activo,
    )
    return UserResponse.model_validate(updated)


@router.post("/{id_usuario}/reset-password")
def reset_user_password(
    id_usuario: int,
    req: UserPasswordResetRequest,
    current_user: User = Depends(require_module_permission("usuarios")),
) -> dict:
    """Restablece la contraseña de acceso de un usuario."""
    user_service.reset_password(id_usuario, req.new_password)
    return {"status": "ok", "id_usuario": id_usuario}
