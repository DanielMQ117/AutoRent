"""Modelos de dominio puro (Data Classes) para la transferencia desacoplada de datos."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from src.domain.enums import (
    ClientStatus,
    ClientType,
    ContractStatus,
    MaintenanceStatus,
    MaintenanceType,
    PaymentMethod,
    PaymentType,
    ReservationStatus,
    SettlementStatus,
    UserRole,
    VehicleStatus,
)


@dataclass
class Role:
    id_rol: Optional[int] = None
    nombre: str = ""
    descripcion: str = ""


@dataclass
class User:
    id_usuario: Optional[int] = None
    id_rol: int = 0
    username: str = ""
    password_hash: str = ""
    nombre_completo: str = ""
    email: str = ""
    activo: bool = True
    fecha_creacion: Optional[datetime] = None
    rol_nombre: Optional[str] = None  # Atributo informativo cargado por join


@dataclass
class VehicleCategory:
    id_categoria: Optional[int] = None
    nombre: str = ""
    descripcion: Optional[str] = None
    deposito_garantia_sugerido: Decimal = Decimal("300.00")
    tarifa_base_diaria: Decimal = Decimal("35.00")


@dataclass
class Brand:
    id_marca: Optional[int] = None
    nombre: str = ""


@dataclass
class VehicleModel:
    id_modelo: Optional[int] = None
    id_marca: int = 0
    nombre: str = ""
    anio: int = 2024
    tipo_transmision: str = "MANUAL"
    capacidad_pasajeros: int = 5
    marca_nombre: Optional[str] = None


@dataclass
class Vehicle:
    id_vehiculo: Optional[int] = None
    id_modelo: int = 0
    id_categoria: int = 0
    placa: str = ""
    vin: str = ""
    color: str = ""
    kilometraje_actual: int = 0
    nivel_combustible_actual: Decimal = Decimal("1.00")
    estado: VehicleStatus = VehicleStatus.DISPONIBLE
    km_proximo_mantenimiento: int = 5000
    activo: bool = True
    modelo_nombre: Optional[str] = None
    categoria_nombre: Optional[str] = None


@dataclass
class DriverLicense:
    id_licencia: Optional[int] = None
    id_cliente: int = 0
    numero_licencia: str = ""
    categoria_licencia: str = ""
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    pais_emision: str = "Nicaragua"


@dataclass
class Client:
    id_cliente: Optional[int] = None
    tipo_persona: ClientType = ClientType.NATURAL
    identificacion: str = ""
    nombres: str = ""
    apellidos: str = ""
    telefono: str = ""
    email: str = ""
    direccion: str = ""
    estado_cliente: ClientStatus = ClientStatus.ACTIVO
    fecha_registro: Optional[datetime] = None
    licencia: Optional[DriverLicense] = None


@dataclass
class InsuranceCoverage:
    id_cobertura: Optional[int] = None
    nombre: str = ""
    descripcion: str = ""
    costo_diario: Decimal = Decimal("0.00")
    porcentaje_deducible: Decimal = Decimal("10.00")
