"""Router FastAPI para Reportes Financieros, Utilización de Flota e Historial de Clientes."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import require_module_permission
from src.api.schemas.report_schema import (
    ClientHistorySummaryResponse,
    FinancialReportSummaryResponse,
    FleetUtilizationSummaryResponse,
)
from src.domain.models import User
from src.services.report_service import report_service

router = APIRouter(prefix="/api/v1/reports", tags=["Reportes y Analítica"])


@router.get("/financial", response_model=FinancialReportSummaryResponse)
def get_financial_report(
    fecha_inicio: Optional[date] = Query(default=None, description="Fecha inicial del periodo"),
    fecha_fin: Optional[date] = Query(default=None, description="Fecha final del periodo"),
    metodo_pago: Optional[str] = Query(default=None, description="Filtro por método de pago"),
    concepto: Optional[str] = Query(default=None, description="Filtro por tipo de movimiento / concepto"),
    current_user: User = Depends(require_module_permission("reportes")),
) -> FinancialReportSummaryResponse:
    """Genera el reporte consolidado de ingresos financieros y recaudación de la agencia activa."""
    summary = report_service.get_financial_report(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        metodo_pago=metodo_pago,
        concepto=concepto,
    )
    return FinancialReportSummaryResponse.model_validate(summary)


@router.get("/fleet", response_model=FleetUtilizationSummaryResponse)
def get_fleet_utilization_report(
    fecha_inicio: Optional[date] = Query(default=None, description="Fecha inicial del periodo"),
    fecha_fin: Optional[date] = Query(default=None, description="Fecha final del periodo"),
    id_categoria: Optional[int] = Query(default=None, description="Filtro por ID de categoría"),
    search: Optional[str] = Query(default=None, description="Búsqueda por placa o modelo"),
    current_user: User = Depends(require_module_permission("reportes")),
) -> FleetUtilizationSummaryResponse:
    """Genera el reporte de utilización, tasa de ocupación y rendimiento de la flota."""
    summary = report_service.get_fleet_utilization_report(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        id_categoria=id_categoria,
        search=search,
    )
    return FleetUtilizationSummaryResponse.model_validate(summary)


@router.get("/clients", response_model=ClientHistorySummaryResponse)
def get_client_history_report(
    filtro_criterio: str = Query(default="TODOS", description="Criterio de segmentación (TODOS, FRECUENTES, CON_SINIESTROS, MOROSOS_VETADOS)"),
    fecha_inicio: Optional[date] = Query(default=None, description="Fecha inicial del periodo"),
    fecha_fin: Optional[date] = Query(default=None, description="Fecha final del periodo"),
    search: Optional[str] = Query(default=None, description="Búsqueda por nombre o identificación"),
    current_user: User = Depends(require_module_permission("reportes")),
) -> ClientHistorySummaryResponse:
    """Genera el reporte de comportamiento, siniestralidad y nivel de riesgo de clientes."""
    summary = report_service.get_client_history_report(
        filtro_criterio=filtro_criterio,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        search=search,
    )
    return ClientHistorySummaryResponse.model_validate(summary)
