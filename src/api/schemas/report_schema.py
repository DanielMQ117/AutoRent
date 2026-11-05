"""Esquemas Pydantic v2 para reportes financieros, utilización de flota e historial de clientes."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FinancialReportItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_pago: Optional[int] = None
    codigo_transaccion: str = ""
    tipo_movimiento: str = ""
    concepto: str = ""
    metodo_pago: str = ""
    monto: Decimal = Decimal("0.00")
    fecha_hora: Optional[datetime] = None
    referencia: Optional[str] = None
    contrato_codigo: Optional[str] = None
    cliente_nombre: Optional[str] = None
    usuario_nombre: Optional[str] = None


class FinancialReportSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    total_facturado: Decimal = Decimal("0.00")
    ingresos_renta: Decimal = Decimal("0.00")
    ingresos_seguros: Decimal = Decimal("0.00")
    ingresos_penalizaciones: Decimal = Decimal("0.00")
    reembolsos_garantia: Decimal = Decimal("0.00")
    gastos_mantenimiento: Decimal = Decimal("0.00")
    ingreso_neto: Decimal = Decimal("0.00")
    total_transacciones: int = 0
    ticket_promedio: Decimal = Decimal("0.00")
    items: list[FinancialReportItemSchema] = Field(default_factory=list)


class FleetUtilizationItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_vehiculo: int = 0
    placa: str = ""
    marca_modelo: str = ""
    categoria: str = ""
    total_contratos: int = 0
    dias_alquilado: int = 0
    tasa_ocupacion_pct: float = 0.0
    ingresos_generados: Decimal = Decimal("0.00")
    dias_taller: int = 0
    gastos_taller: Decimal = Decimal("0.00")
    kilometraje_actual: int = 0
    estado_actual: str = ""


class FleetUtilizationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    dias_periodo: int = 1
    total_vehiculos: int = 0
    total_dias_alquilados: int = 0
    tasa_ocupacion_promedio: float = 0.0
    ingresos_totales_flota: Decimal = Decimal("0.00")
    gastos_totales_taller: Decimal = Decimal("0.00")
    vehiculo_mas_rentado: str = "—"
    items: list[FleetUtilizationItemSchema] = Field(default_factory=list)


class ClientHistoryItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cliente: int = 0
    identificacion: str = ""
    nombre_completo: str = ""
    telefono: str = ""
    email: str = ""
    estado_cliente: str = ""
    total_contratos: int = 0
    total_gastado: Decimal = Decimal("0.00")
    total_dias_alquilados: int = 0
    total_danos_reportados: int = 0
    total_cargos_penalizaciones: Decimal = Decimal("0.00")
    nivel_riesgo: str = "BAJO"


class ClientHistorySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_clientes_analizados: int = 0
    clientes_frecuentes: int = 0
    clientes_con_siniestros: int = 0
    clientes_alto_riesgo: int = 0
    items: list[ClientHistoryItemSchema] = Field(default_factory=list)
