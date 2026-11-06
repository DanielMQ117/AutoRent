"""Esquemas Pydantic v2 para inspección de devoluciones, daños y liquidaciones financieras."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.contract_schema import PaymentResponse
from src.domain.enums import (
    DamageSeverity,
    DamageType,
    PaymentMethod,
    SettlementStatus,
)


class DamageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_danio: Optional[int] = None
    tenant_id: Optional[int] = None
    id_devolucion: Optional[int] = None
    zona_carroceria: str
    tipo_danio: DamageType = DamageType.RAYON
    gravedad: DamageSeverity = DamageSeverity.LEVE
    descripcion: str
    costo_reparacion: Decimal = Decimal("0.00")


class ReturnCreateRequest(BaseModel):
    id_contrato: int
    fecha_hora_retorno_real: Optional[datetime] = None
    kilometraje_retorno: int
    combustible_retorno: Decimal = Decimal("1.00")
    limpieza_aprobada: bool = True
    accesorios_completos: bool = True
    observaciones: Optional[str] = None
    metodo_pago: PaymentMethod = PaymentMethod.EFECTIVO
    referencia_pago: Optional[str] = None
    danios: list[DamageSchema] = Field(default_factory=list)


class ReturnInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_devolucion: int
    tenant_id: int
    id_contrato: int
    fecha_hora_retorno_real: Optional[datetime] = None
    kilometraje_retorno: int
    combustible_retorno: Decimal
    horas_retraso: int
    limpieza_aprobada: bool
    accesorios_completos: bool
    observaciones: Optional[str] = None
    id_usuario: int
    contrato_codigo: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_identificacion: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    usuario_nombre: Optional[str] = None
    kilometraje_salida: Optional[int] = 0
    combustible_salida: Optional[Decimal] = Decimal("1.00")
    fecha_hora_fin_pactada: Optional[datetime] = None
    tarifa_diaria: Optional[Decimal] = Decimal("0.00")
    danios: list[DamageSchema] = Field(default_factory=list)


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_liquidacion: int
    tenant_id: int
    id_contrato: int
    id_devolucion: int
    fecha_liquidacion: Optional[datetime] = None
    dias_facturados: int
    subtotal_renta: Decimal
    cargos_retraso: Decimal
    cargos_combustible: Decimal
    cargos_km_excedente: Decimal
    cargos_danios: Decimal
    total_bruto: Decimal
    monto_garantia_aplicado: Decimal
    saldo_cliente: Decimal
    estado_liquidacion: SettlementStatus
    id_usuario: int
    contrato_codigo: Optional[str] = None
    cliente_nombre: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    usuario_nombre: Optional[str] = None
    monto_garantia_inicial: Optional[Decimal] = Decimal("0.00")
    pagos: list[PaymentResponse] = Field(default_factory=list)


class ReturnProcessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    return_inspection: ReturnInspectionResponse
    settlement: SettlementResponse
    payment: Optional[PaymentResponse] = None
