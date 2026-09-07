"""Enumeraciones del dominio que reflejan las restricciones del modelo relacional."""

from enum import Enum


class UserRole(str, Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    AGENTE_VENTAS = "AGENTE_VENTAS"
    INSPECTOR_TALLER = "INSPECTOR_TALLER"
    GERENTE = "GERENTE"


class VehicleStatus(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    RESERVADO = "RESERVADO"
    ALQUILADO = "ALQUILADO"
    EN_INSPECCION = "EN_INSPECCION"
    EN_MANTENIMIENTO = "EN_MANTENIMIENTO"
    DE_BAJA = "DE_BAJA"


class ClientType(str, Enum):
    NATURAL = "NATURAL"
    JURIDICA = "JURIDICA"


class ClientStatus(str, Enum):
    ACTIVO = "ACTIVO"
    MOROSO = "MOROSO"
    VETADO = "VETADO"


class ReservationStatus(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    VENCIDA = "VENCIDA"
    CONVERTIDA_A_CONTRATO = "CONVERTIDA_A_CONTRATO"


class ContractStatus(str, Enum):
    ACTIVO = "ACTIVO"
    EN_INSPECCION = "EN_INSPECCION"
    EN_LIQUIDACION = "EN_LIQUIDACION"
    LIQUIDADO = "LIQUIDADO"
    ANULADO = "ANULADO"


class DamageType(str, Enum):
    RAYON = "RAYON"
    GOLPE = "GOLPE"
    ROTURA = "ROTURA"
    FALTANTE_PIEZA = "FALTANTE_PIEZA"
    INTERIOR = "INTERIOR"


class DamageSeverity(str, Enum):
    LEVE = "LEVE"
    MODERADO = "MODERADO"
    GRAVE = "GRAVE"


class SettlementStatus(str, Enum):
    PENDIENTE_PAGO = "PENDIENTE_PAGO"
    CERRADA = "CERRADA"


class PaymentType(str, Enum):
    ANTICIPO_RESERVA = "ANTICIPO_RESERVA"
    DEPOSITO_GARANTIA = "DEPOSITO_GARANTIA"
    COBRO_LIQUIDACION = "COBRO_LIQUIDACION"
    REEMBOLSO_GARANTIA = "REEMBOLSO_GARANTIA"


class PaymentMethod(str, Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA_CREDITO = "TARJETA_CREDITO"
    TARJETA_DEBITO = "TARJETA_DEBITO"
    TRANSFERENCIA = "TRANSFERENCIA"


class MaintenanceType(str, Enum):
    PREVENTIVO = "PREVENTIVO"
    CORRECTIVO = "CORRECTIVO"


class MaintenanceStatus(str, Enum):
    EN_TALLER = "EN_TALLER"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"
