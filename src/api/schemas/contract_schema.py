"""Esquemas Pydantic v2 para contratos de alquiler, seguros, pagos y conductores adicionales."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import ContractStatus, PaymentMethod, PaymentType


class InsuranceCoverageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cobertura: int
    tenant_id: int
    nombre: str
    descripcion: str
    costo_diario: Decimal
    porcentaje_deducible: Decimal


class AdditionalDriverSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_conductor: Optional[int] = None
    tenant_id: Optional[int] = None
    id_contrato: Optional[int] = None
    nombre_completo: str
    identificacion: str
    numero_licencia: str
    fecha_vencimiento_licencia: date


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_pago: Optional[int] = None
    tenant_id: Optional[int] = None
    codigo_transaccion: str
    id_contrato: Optional[int] = None
    id_reserva: Optional[int] = None
    id_liquidacion: Optional[int] = None
    tipo_movimiento: PaymentType
    metodo_pago: PaymentMethod
    monto: Decimal
    fecha_hora: Optional[datetime] = None
    referencia: Optional[str] = None
    id_usuario: int
    usuario_nombre: Optional[str] = None


class ContractCreateRequest(BaseModel):
    id_reserva: Optional[int] = None
    id_cliente: int
    id_vehiculo: int
    id_cobertura: int
    fecha_hora_inicio_pactada: datetime
    fecha_hora_fin_pactada: datetime
    kilometraje_salida: int
    combustible_salida: Decimal = Decimal("1.00")
    tarifa_diaria_aplicada: Decimal
    monto_garantia: Decimal = Decimal("300.00")
    kilometraje_ilimitado: bool = True
    limite_km_diario: Optional[int] = None
    costo_km_excedente: Decimal = Decimal("0.00")
    metodo_pago_garantia: PaymentMethod = PaymentMethod.EFECTIVO
    referencia_pago_garantia: Optional[str] = None
    conductores_adicionales: list[AdditionalDriverSchema] = Field(default_factory=list)


class ContractCancelRequest(BaseModel):
    motivo: Optional[str] = None


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_contrato: int
    tenant_id: int
    codigo_contrato: str
    id_reserva: Optional[int] = None
    id_cliente: int
    id_vehiculo: int
    id_cobertura: int
    fecha_hora_inicio_pactada: datetime
    fecha_hora_fin_pactada: datetime
    fecha_hora_salida_real: Optional[datetime] = None
    kilometraje_salida: int
    combustible_salida: Decimal
    tarifa_diaria_aplicada: Decimal
    monto_garantia: Decimal
    kilometraje_ilimitado: bool
    limite_km_diario: Optional[int] = None
    costo_km_excedente: Decimal
    estado: ContractStatus
    id_usuario: int
    fecha_creacion: Optional[datetime] = None
    cliente_nombre: Optional[str] = None
    cliente_identificacion: Optional[str] = None
    cliente_telefono: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    vehiculo_categoria: Optional[str] = None
    cobertura_nombre: Optional[str] = None
    cobertura_costo_diario: Optional[Decimal] = None
    usuario_nombre: Optional[str] = None
    reserva_codigo: Optional[str] = None
    duracion_dias: Optional[int] = None
    costo_cobertura_total: Optional[Decimal] = None
    subtotal_renta_pactado: Optional[Decimal] = None
    total_estimado: Optional[Decimal] = None
    conductores_adicionales: list[AdditionalDriverSchema] = Field(default_factory=list)
    pagos: list[PaymentResponse] = Field(default_factory=list)
