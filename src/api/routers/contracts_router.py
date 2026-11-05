"""Router FastAPI para Contratos de Arrendamiento, Despacho y Garantías."""

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.contract_schema import (
    ContractCancelRequest,
    ContractCreateRequest,
    ContractResponse,
    InsuranceCoverageResponse,
)
from src.domain.models import AdditionalDriver, Contract, User
from src.services.contract_service import contract_service

router = APIRouter(prefix="/api/v1/contracts", tags=["Contratos y Despacho"])


@router.get("/coverages", response_model=List[InsuranceCoverageResponse])
def list_coverages(
    current_user: User = Depends(require_module_permission("contratos")),
) -> List[InsuranceCoverageResponse]:
    """Retorna el catálogo de pólizas y coberturas de seguro de la agencia activa."""
    coverages = contract_service.get_coverages()
    return [InsuranceCoverageResponse.model_validate(c) for c in coverages]


@router.get("", response_model=List[ContractResponse])
def list_contracts(
    search: Optional[str] = Query(default=None, description="Búsqueda por código, cliente o placa"),
    status: Optional[str] = Query(default=None, description="Filtro por estado del contrato"),
    client_id: Optional[int] = Query(default=None, description="Filtro por ID de cliente"),
    vehicle_id: Optional[int] = Query(default=None, description="Filtro por ID de vehículo"),
    current_user: User = Depends(require_module_permission("contratos")),
) -> List[ContractResponse]:
    """Lista los contratos de alquiler de la agencia activa."""
    contracts = contract_service.list_contracts(
        search=search,
        status=status,
        client_id=client_id,
        vehicle_id=vehicle_id,
    )
    return [ContractResponse.model_validate(c) for c in contracts]


@router.get("/{id_contrato}", response_model=ContractResponse)
def get_contract(
    id_contrato: int,
    current_user: User = Depends(require_module_permission("contratos")),
) -> ContractResponse:
    """Obtiene los detalles de un contrato por su ID."""
    contract = contract_service.get_contract(id_contrato)
    return ContractResponse.model_validate(contract)


@router.get("/{id_contrato}/document-html")
def get_contract_document_html(
    id_contrato: int,
    current_user: User = Depends(require_module_permission("contratos")),
) -> dict:
    """Genera el documento legal del contrato en formato HTML listo para impresión."""
    html = contract_service.build_contract_document_html(id_contrato)
    return {"id_contrato": id_contrato, "html": html}


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract(
    req: ContractCreateRequest,
    current_user: User = Depends(require_module_permission("contratos")),
) -> ContractResponse:
    """Formaliza un nuevo contrato de arrendamiento, despacha el vehículo y registra la garantía."""
    drivers = [
        AdditionalDriver(
            nombre_completo=d.nombre_completo,
            identificacion=d.identificacion,
            numero_licencia=d.numero_licencia,
            fecha_vencimiento_licencia=d.fecha_vencimiento_licencia,
        )
        for d in req.conductores_adicionales
    ]
    contract = Contract(
        id_reserva=req.id_reserva,
        id_cliente=req.id_cliente,
        id_vehiculo=req.id_vehiculo,
        id_cobertura=req.id_cobertura,
        fecha_hora_inicio_pactada=req.fecha_hora_inicio_pactada,
        fecha_hora_fin_pactada=req.fecha_hora_fin_pactada,
        fecha_hora_salida_real=req.fecha_hora_salida_real,
        kilometraje_salida=req.kilometraje_salida,
        combustible_salida=req.combustible_salida,
        tarifa_diaria_aplicada=req.tarifa_diaria_aplicada,
        monto_garantia=req.monto_garantia,
        kilometraje_ilimitado=req.kilometraje_ilimitado,
        limite_km_diario=req.limite_km_diario,
        costo_km_excedente=req.costo_km_excedente,
        id_usuario=current_user.id_usuario or 0,
        conductores_adicionales=drivers,
    )
    created = contract_service.create_contract(
        contract,
        metodo_pago_garantia=req.metodo_pago_garantia,
        referencia_pago_garantia=req.referencia_pago_garantia,
    )
    return ContractResponse.model_validate(created)


@router.post("/{id_contrato}/cancel", response_model=ContractResponse)
def cancel_contract(
    id_contrato: int,
    req: Optional[ContractCancelRequest] = Body(default=None),
    current_user: User = Depends(require_module_permission("contratos")),
) -> ContractResponse:
    """Anula un contrato activo, libera el vehículo y registra el reembolso de garantía."""
    contract_service.cancel_contract(id_contrato, motivo=req.motivo if req else None)
    updated = contract_service.get_contract(id_contrato)
    return ContractResponse.model_validate(updated)
