"""Modelos de dominio puro (Data Classes) para la transferencia desacoplada de datos."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from src.domain.enums import (
    ClientStatus,
    ClientType,
    ContractStatus,
    DamageSeverity,
    DamageType,
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
class AuditLog:
    id_auditoria: Optional[int] = None
    id_usuario: Optional[int] = None
    username: str = ""
    accion: str = ""
    tabla_afectada: str = ""
    id_registro: Optional[int] = None
    detalles: Optional[str] = None
    ip_origen: str = "127.0.0.1"
    fecha_registro: Optional[datetime] = None


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
    marca_nombre: Optional[str] = None
    anio: Optional[int] = None
    tarifa_base_diaria: Optional[Decimal] = None


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

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()


@dataclass
class InsuranceCoverage:
    id_cobertura: Optional[int] = None
    nombre: str = ""
    descripcion: str = ""
    costo_diario: Decimal = Decimal("0.00")
    porcentaje_deducible: Decimal = Decimal("10.00")


@dataclass
class Reservation:
    id_reserva: Optional[int] = None
    codigo_reserva: str = ""
    id_cliente: int = 0
    id_categoria: int = 0
    id_vehiculo: Optional[int] = None
    fecha_hora_inicio: Optional[datetime] = None
    fecha_hora_fin: Optional[datetime] = None
    monto_anticipo: Decimal = Decimal("0.00")
    estado: ReservationStatus = ReservationStatus.PENDIENTE
    id_usuario: int = 0
    fecha_creacion: Optional[datetime] = None
    # Atributos auxiliares provenientes de JOINs para presentación
    cliente_nombre: Optional[str] = None
    cliente_identificacion: Optional[str] = None
    categoria_nombre: Optional[str] = None
    tarifa_base_diaria: Optional[Decimal] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    usuario_nombre: Optional[str] = None

    @property
    def duracion_dias(self) -> int:
        """Calcula la duración en días calendario de la reserva (mínimo 1 día)."""
        if not self.fecha_hora_inicio or not self.fecha_hora_fin:
            return 1
        delta = self.fecha_hora_fin - self.fecha_hora_inicio
        dias = delta.days
        # Si sobran más de 60 minutos se computa como fracción o día adicional
        if delta.seconds > 3600:
            dias += 1
        return max(1, dias)

    @property
    def costo_estimado(self) -> Decimal:
        """Calcula el costo total estimado de renta para el período reservado."""
        if not self.tarifa_base_diaria:
            return Decimal("0.00")
        return self.tarifa_base_diaria * Decimal(self.duracion_dias)


@dataclass
class AdditionalDriver:
    id_conductor: Optional[int] = None
    id_contrato: Optional[int] = None
    nombre_completo: str = ""
    identificacion: str = ""
    numero_licencia: str = ""
    fecha_vencimiento_licencia: Optional[date] = None


@dataclass
class Payment:
    id_pago: Optional[int] = None
    codigo_transaccion: str = ""
    id_contrato: Optional[int] = None
    id_reserva: Optional[int] = None
    id_liquidacion: Optional[int] = None
    tipo_movimiento: PaymentType = PaymentType.DEPOSITO_GARANTIA
    metodo_pago: PaymentMethod = PaymentMethod.EFECTIVO
    monto: Decimal = Decimal("0.00")
    fecha_hora: Optional[datetime] = None
    referencia: Optional[str] = None
    id_usuario: int = 0
    usuario_nombre: Optional[str] = None


@dataclass
class Contract:
    id_contrato: Optional[int] = None
    codigo_contrato: str = ""
    id_reserva: Optional[int] = None
    id_cliente: int = 0
    id_vehiculo: int = 0
    id_cobertura: int = 0
    fecha_hora_inicio_pactada: Optional[datetime] = None
    fecha_hora_fin_pactada: Optional[datetime] = None
    fecha_hora_salida_real: Optional[datetime] = None
    kilometraje_salida: int = 0
    combustible_salida: Decimal = Decimal("1.00")
    tarifa_diaria_aplicada: Decimal = Decimal("0.00")
    monto_garantia: Decimal = Decimal("300.00")
    kilometraje_ilimitado: bool = True
    limite_km_diario: Optional[int] = None
    costo_km_excedente: Decimal = Decimal("0.00")
    estado: ContractStatus = ContractStatus.ACTIVO
    id_usuario: int = 0
    fecha_creacion: Optional[datetime] = None

    # Atributos auxiliares de presentación / JOINs
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

    # Sub-entidades
    conductores_adicionales: list[AdditionalDriver] = field(
        default_factory=list)
    pagos: list[Payment] = field(default_factory=list)

    @property
    def duracion_dias(self) -> int:
        """Calcula la duración pactada en días calendario (mínimo 1 día)."""
        if not self.fecha_hora_inicio_pactada or not self.fecha_hora_fin_pactada:
            return 1
        delta = self.fecha_hora_fin_pactada - self.fecha_hora_inicio_pactada
        dias = delta.days
        if delta.seconds > 3600:
            dias += 1
        return max(1, dias)

    @property
    def costo_cobertura_total(self) -> Decimal:
        """Costo total del seguro durante el período contratado."""
        daily_cost = self.cobertura_costo_diario or Decimal("0.00")
        return daily_cost * Decimal(self.duracion_dias)

    @property
    def subtotal_renta_pactado(self) -> Decimal:
        """Subtotal pactado de la tarifa diaria del automóvil."""
        return self.tarifa_diaria_aplicada * Decimal(self.duracion_dias)

    @property
    def total_estimado(self) -> Decimal:
        """Total estimado del alquiler (renta + seguro contratado)."""
        return self.subtotal_renta_pactado + self.costo_cobertura_total


@dataclass
class Damage:
    """Representa un daño físico registrado durante la inspección de retorno."""
    id_danio: Optional[int] = None
    id_devolucion: Optional[int] = None
    zona_carroceria: str = ""
    tipo_danio: DamageType = DamageType.RAYON
    gravedad: DamageSeverity = DamageSeverity.LEVE
    descripcion: str = ""
    costo_reparacion: Decimal = Decimal("0.00")


@dataclass
class ReturnInspection:
    """Representa el acta de devolución física e inspección técnica de un vehículo."""
    id_devolucion: Optional[int] = None
    id_contrato: int = 0
    fecha_hora_retorno_real: Optional[datetime] = None
    kilometraje_retorno: int = 0
    combustible_retorno: Decimal = Decimal("1.00")
    horas_retraso: int = 0
    limpieza_aprobada: bool = True
    accesorios_completos: bool = True
    observaciones: Optional[str] = None
    id_usuario: int = 0

    # Atributos informativos cargados por JOINs
    contrato_codigo: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_identificacion: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    usuario_nombre: Optional[str] = None
    kilometraje_salida: int = 0
    combustible_salida: Decimal = Decimal("1.00")
    fecha_hora_fin_pactada: Optional[datetime] = None
    tarifa_diaria: Decimal = Decimal("0.00")

    # Lista de averías detectadas
    danios: list[Damage] = field(default_factory=list)

    @property
    def km_recorridos(self) -> int:
        """Calcula los kilómetros transitados durante el período del contrato."""
        return max(0, self.kilometraje_retorno - self.kilometraje_salida)

    @property
    def combustible_faltante(self) -> Decimal:
        """Fracción faltante de combustible respecto al nivel de entrega."""
        return max(Decimal("0.00"), self.combustible_salida - self.combustible_retorno)

    @property
    def costo_total_danios(self) -> Decimal:
        """Monto acumulado por concepto de reparación de averías."""
        return sum((d.costo_reparacion for d in self.danios), Decimal("0.00"))

    @property
    def tiene_danio_grave(self) -> bool:
        """Indica si existe alguna avería de gravedad alta que inhabilite el vehículo."""
        return any(d.gravedad == DamageSeverity.GRAVE for d in self.danios)


@dataclass
class Settlement:
    """Representa la liquidación financiera final y balance contable de un contrato."""
    id_liquidacion: Optional[int] = None
    id_contrato: int = 0
    id_devolucion: int = 0
    fecha_liquidacion: Optional[datetime] = None
    dias_facturados: int = 1
    subtotal_renta: Decimal = Decimal("0.00")
    cargos_retraso: Decimal = Decimal("0.00")
    cargos_combustible: Decimal = Decimal("0.00")
    cargos_km_excedente: Decimal = Decimal("0.00")
    cargos_danios: Decimal = Decimal("0.00")
    total_bruto: Decimal = Decimal("0.00")
    monto_garantia_aplicado: Decimal = Decimal("0.00")
    saldo_cliente: Decimal = Decimal("0.00")
    estado_liquidacion: SettlementStatus = SettlementStatus.CERRADA
    id_usuario: int = 0

    # Atributos auxiliares informativos
    contrato_codigo: Optional[str] = None
    cliente_nombre: Optional[str] = None
    vehiculo_placa: Optional[str] = None
    usuario_nombre: Optional[str] = None
    monto_garantia_inicial: Decimal = Decimal("0.00")
    pagos: list[Payment] = field(default_factory=list)


@dataclass
class Maintenance:
    """Representa una orden de servicio en taller mecánico (preventivo o correctivo)."""
    id_mantenimiento: Optional[int] = None
    id_vehiculo: int = 0
    tipo_mantenimiento: MaintenanceType = MaintenanceType.PREVENTIVO
    fecha_ingreso: Optional[datetime] = None
    fecha_salida_estimada: Optional[date] = None
    fecha_salida_real: Optional[datetime] = None
    kilometraje_entrada: int = 0
    taller_servicio: str = ""
    descripcion_trabajo: str = ""
    costo_total: Decimal = Decimal("0.00")
    estado: MaintenanceStatus = MaintenanceStatus.EN_TALLER
    id_usuario: int = 0

    # Atributos auxiliares de presentación cargados vía JOINs
    vehiculo_placa: Optional[str] = None
    vehiculo_modelo: Optional[str] = None
    vehiculo_categoria: Optional[str] = None
    vehiculo_kilometraje_actual: int = 0
    km_proximo_mantenimiento_actual: int = 0
    usuario_nombre: Optional[str] = None

    @property
    def duracion_dias(self) -> int:
        """Calcula los días transcurridos o estimados en taller."""
        if not self.fecha_ingreso:
            return 1
        fin = self.fecha_salida_real.date() if self.fecha_salida_real else (self.fecha_salida_estimada or date.today())
        inicio = self.fecha_ingreso.date()
        return max(1, (fin - inicio).days)

    @property
    def esta_completado(self) -> bool:
        return self.estado == MaintenanceStatus.FINALIZADO


# ============================================================================
# MODELOS DE DOMINIO PARA REPORTES, ESTADÍSTICAS Y ANALÍTICA (FASE 9)
# ============================================================================

@dataclass
class FinancialReportItem:
    """Ítem detallado de transacción financiera o movimiento de caja."""
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


@dataclass
class FinancialReportSummary:
    """Resumen consolidado financiero y de recaudación (RF-34)."""
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
    items: list[FinancialReportItem] = field(default_factory=list)


@dataclass
class FleetUtilizationItem:
    """Métricas de productividad y demanda por unidad vehicular (RF-35)."""
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


@dataclass
class FleetUtilizationSummary:
    """Resumen analítico de utilización de la flota completa (RF-35)."""
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    dias_periodo: int = 1
    total_vehiculos: int = 0
    total_dias_alquilados: int = 0
    tasa_ocupacion_promedio: float = 0.0
    ingresos_totales_flota: Decimal = Decimal("0.00")
    gastos_totales_taller: Decimal = Decimal("0.00")
    vehiculo_mas_rentado: str = "—"
    items: list[FleetUtilizationItem] = field(default_factory=list)


@dataclass
class ClientHistoryItem:
    """Ficha de siniestralidad, recurrencia y comportamiento crediticio de cliente (RF-36)."""
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
    nivel_riesgo: str = "BAJO"  # "BAJO", "MEDIO", "ALTO"


@dataclass
class ClientHistorySummary:
    """Resumen de comportamiento y segmentación de clientes (RF-36)."""
    total_clientes_analizados: int = 0
    clientes_frecuentes: int = 0
    clientes_con_siniestros: int = 0
    clientes_alto_riesgo: int = 0
    items: list[ClientHistoryItem] = field(default_factory=list)
