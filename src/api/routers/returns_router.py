"""Router FastAPI para Recepción Física, Inspección de Devoluciones y Liquidación Financiera."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import require_module_permission
from src.api.schemas.return_schema import (
    ReturnCreateRequest,
    ReturnInspectionResponse,
    ReturnProcessResponse,
    SettlementResponse,
)
from src.domain.models import Damage, ReturnInspection, User
from src.services.return_service import return_service

router = APIRouter(prefix="/api/v1/returns", tags=["Devoluciones y Liquidaciones"])


@router.get("", response_model=List[ReturnInspectionResponse])
def list_returns(
    search: str = Query(default="", description="Búsqueda por contrato, cliente o placa"),
    limit: int = Query(default=100, ge=1, le=500, description="Límite de registros"),
    current_user: User = Depends(require_module_permission("devoluciones")),
) -> List[ReturnInspectionResponse]:
    """Lista las actas de devolución física registradas en la agencia activa."""
    returns = return_service.list_returns(search=search, limit=limit)
    return [ReturnInspectionResponse.model_validate(r) for r in returns]


@router.get("/settlements", response_model=List[SettlementResponse])
def list_settlements(
    search: str = Query(default="", description="Búsqueda por contrato, cliente o placa"),
    limit: int = Query(default=100, ge=1, le=500, description="Límite de registros"),
    current_user: User = Depends(require_module_permission("devoluciones")),
) -> List[SettlementResponse]:
    """Lista las liquidaciones financieras finales registradas en la agencia activa."""
    settlements = return_service.list_settlements(search=search, limit=limit)
    return [SettlementResponse.model_validate(s) for s in settlements]


@router.get("/by-contract/{id_contrato}", response_model=Optional[ReturnInspectionResponse])
def get_return_by_contract(
    id_contrato: int,
    current_user: User = Depends(require_module_permission("devoluciones")),
) -> Optional[ReturnInspectionResponse]:
    """Obtiene la devolución asociada a un contrato específico si existe."""
    ret = return_service.get_return_by_contract(id_contrato)
    return ReturnInspectionResponse.model_validate(ret) if ret else None


@router.get("/settlements/by-contract/{id_contrato}", response_model=Optional[SettlementResponse])
def get_settlement_by_contract(
    id_contrato: int,
    current_user: User = Depends(require_module_permission("devoluciones")),
) -> Optional[SettlementResponse]:
    """Obtiene la liquidación asociada a un contrato específico si existe."""
    st = return_service.get_settlement_by_contract(id_contrato)
    return SettlementResponse.model_validate(st) if st else None


@router.get("/{id_devolucion}", response_model=ReturnInspectionResponse)
def get_return(
    id_devolucion: int,
    current_user: User = Depends(require_module_permission("devoluciones")),
) -> ReturnInspectionResponse:
    """Obtiene el detalle de un acta de devolución e inspección física."""
    ret = return_service.get_return(id_devolucion)
    return ReturnInspectionResponse.model_validate(ret)


@router.post("", response_model=ReturnProcessResponse, status_code=status.HTTP_201_CREATED)
def process_return_and_settlement(
    req: ReturnCreateRequest,
    current_user: User = Depends(require_module_permission("devoluciones")),
) -> ReturnProcessResponse:
    """Procesa de forma atómica el retorno del vehículo, acta de daños y liquidación financiera."""
    danios = [
        Damage(
            zona_carroceria=d.zona_carroceria,
            tipo_danio=d.tipo_danio,
            gravedad=d.gravedad,
            descripcion=d.descripcion,
            costo_reparacion=d.costo_reparacion,
        )
        for d in req.danios
    ]
    ret_data = ReturnInspection(
        id_contrato=req.id_contrato,
        fecha_hora_retorno_real=req.fecha_hora_retorno_real,
        kilometraje_retorno=req.kilometraje_retorno,
        combustible_retorno=req.combustible_retorno,
        limpieza_aprobada=req.limpieza_aprobada,
        accesorios_completos=req.accesorios_completos,
        observaciones=req.observaciones,
        id_usuario=current_user.id_usuario or 0,
        danios=danios,
    )
    result = return_service.process_return_and_settlement(
        req.id_contrato,
        ret_data,
        metodo_pago=req.metodo_pago,
        referencia_pago=req.referencia_pago,
    )
    return ReturnProcessResponse.model_validate(result)
