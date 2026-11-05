"""Router FastAPI para Autenticación, Sesión JWT y Catálogo de Agencias (Inquilinos / Tenants)."""

from typing import List

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import create_access_token, get_current_api_user
from src.api.schemas.auth_schema import (
    AgencyResponse,
    LoginRequest,
    LoginResponse,
    UserSessionInfo,
)
from src.domain.models import User
from src.services.auth_service import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación y Agencias"])


@router.get("/agencies", response_model=List[AgencyResponse])
def list_agencies(
    only_active: bool = Query(default=True, description="Filtrar solo agencias habilitadas"),
) -> List[AgencyResponse]:
    """Lista las sucursales/agencias arrendadoras disponibles para iniciar sesión."""
    agencies = auth_service.list_agencies(only_active=only_active)
    return [AgencyResponse.model_validate(a) for a in agencies]


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    """Autentica las credenciales del usuario en la agencia seleccionada y emite un token JWT."""
    user = auth_service.login(
        username=req.username,
        password=req.password,
        tenant_id=req.tenant_id,
    )
    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        user=UserSessionInfo.model_validate(user),
    )


@router.get("/me", response_model=UserSessionInfo)
def get_me(current_user: User = Depends(get_current_api_user)) -> UserSessionInfo:
    """Retorna la identidad y contexto de agencia (tenant) del usuario autenticado."""
    return UserSessionInfo.model_validate(current_user)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_api_user)) -> dict:
    """Registra el cierre de sesión en la bitácora de auditoría."""
    auth_service.logout()
    return {"status": "ok", "message": "Sesión finalizada correctamente."}
