"""Router FastAPI para Gestión de Clientes y Licencias de Conducir."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.client_schema import (
    ClientCreateRequest,
    ClientResponse,
    ClientStatusUpdateRequest,
    ClientUpdateRequest,
)
from src.domain.models import Client, DriverLicense, User
from src.services.client_service import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["Clientes y Licencias"])


@router.get("", response_model=List[ClientResponse])
def list_clients(
    search: Optional[str] = Query(default=None, description="Búsqueda por nombre, cédula o correo"),
    status: Optional[str] = Query(default=None, description="Filtro por estado (ACTIVO, MOROSO, VETADO)"),
    current_user: User = Depends(require_module_permission("clientes")),
) -> List[ClientResponse]:
    """Lista los clientes registrados en la agencia activa."""
    clients = client_service.list_clients(search=search, status=status)
    return [ClientResponse.model_validate(c) for c in clients]


@router.get("/{id_cliente}", response_model=ClientResponse)
def get_client(
    id_cliente: int,
    current_user: User = Depends(require_module_permission("clientes")),
) -> ClientResponse:
    """Obtiene el expediente de un cliente y su licencia de conducir."""
    client = client_service.get_client(id_cliente)
    return ClientResponse.model_validate(client)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    req: ClientCreateRequest,
    current_user: User = Depends(require_module_permission("clientes")),
) -> ClientResponse:
    """Registra un nuevo cliente y opcionalmente su licencia de conducir."""
    client = Client(
        tipo_persona=req.tipo_persona,
        identificacion=req.identificacion,
        nombres=req.nombres,
        apellidos=req.apellidos,
        telefono=req.telefono,
        email=req.email,
        direccion=req.direccion,
        estado_cliente=req.estado_cliente,
    )
    license_obj = None
    if req.licencia is not None:
        license_obj = DriverLicense(
            numero_licencia=req.licencia.numero_licencia,
            categoria_licencia=req.licencia.categoria_licencia,
            fecha_emision=req.licencia.fecha_emision,
            fecha_vencimiento=req.licencia.fecha_vencimiento,
            pais_emision=req.licencia.pais_emision,
        )
    created = client_service.create_client(client, license_obj)
    return ClientResponse.model_validate(created)


@router.put("/{id_cliente}", response_model=ClientResponse)
def update_client(
    id_cliente: int,
    req: ClientUpdateRequest,
    current_user: User = Depends(require_module_permission("clientes")),
) -> ClientResponse:
    """Actualiza los datos de un cliente existente y su licencia de conducir."""
    client = Client(
        id_cliente=id_cliente,
        tipo_persona=req.tipo_persona,
        identificacion=req.identificacion,
        nombres=req.nombres,
        apellidos=req.apellidos,
        telefono=req.telefono,
        email=req.email,
        direccion=req.direccion,
        estado_cliente=req.estado_cliente,
    )
    license_obj = None
    if req.licencia is not None:
        license_obj = DriverLicense(
            id_cliente=id_cliente,
            numero_licencia=req.licencia.numero_licencia,
            categoria_licencia=req.licencia.categoria_licencia,
            fecha_emision=req.licencia.fecha_emision,
            fecha_vencimiento=req.licencia.fecha_vencimiento,
            pais_emision=req.licencia.pais_emision,
        )
    updated = client_service.update_client(client, license_obj)
    return ClientResponse.model_validate(updated)


@router.patch("/{id_cliente}/status", response_model=ClientResponse)
def change_client_status(
    id_cliente: int,
    req: ClientStatusUpdateRequest,
    current_user: User = Depends(require_module_permission("clientes")),
) -> ClientResponse:
    """Modifica el estado comercial de un cliente (ACTIVO, MOROSO, VETADO)."""
    client_service.change_status(id_cliente, req.estado_cliente)
    updated = client_service.get_client(id_cliente)
    return ClientResponse.model_validate(updated)


@router.delete("/{id_cliente}")
def delete_client(
    id_cliente: int,
    current_user: User = Depends(require_module_permission("clientes")),
) -> dict:
    """Elimina físicamente un cliente sin compromisos ni historial."""
    client_service.delete_client(id_cliente)
    return {"status": "ok", "id_cliente": id_cliente}
