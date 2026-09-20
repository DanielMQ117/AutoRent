"""Componentes visuales reutilizables de etiquetas y badges de estado."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

from src.domain.enums import (
    ClientStatus,
    ContractStatus,
    DamageSeverity,
    MaintenanceStatus,
    MaintenanceType,
    ReservationStatus,
    SettlementStatus,
    VehicleStatus,
)


def create_badge(text: str, bg_color: str, text_color: str, border_color: str) -> QLabel:
    """Genera un QLabel con aspecto de pastilla/badge estilizado."""
    badge = QLabel(f" {text} ")
    badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(f"""
        QLabel {{
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 4px;
            padding: 3px 8px;
        }}
    """)
    return badge


def get_vehicle_status_badge(status: VehicleStatus) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado del vehículo."""
    val = status.value if isinstance(status, VehicleStatus) else str(status)
    if val == VehicleStatus.DISPONIBLE.value:
        return create_badge("✓ DISPONIBLE", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    elif val == VehicleStatus.ALQUILADO.value:
        return create_badge("⚡ ALQUILADO", "rgba(14, 165, 233, 0.15)", "#38bdf8", "rgba(14, 165, 233, 0.4)")
    elif val == VehicleStatus.EN_MANTENIMIENTO.value:
        return create_badge("🔧 EN TALLER", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    elif val == VehicleStatus.RESERVADO.value:
        return create_badge("📅 RESERVADO", "rgba(168, 85, 247, 0.15)", "#c084fc", "rgba(168, 85, 247, 0.4)")
    elif val == VehicleStatus.DE_BAJA.value:
        return create_badge("✖ DE BAJA", "rgba(100, 116, 139, 0.2)", "#94a3b8", "rgba(100, 116, 139, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_client_status_badge(status: ClientStatus) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado del cliente."""
    val = status.value if isinstance(status, ClientStatus) else str(status)
    if val == ClientStatus.ACTIVO.value:
        return create_badge("✓ ACTIVO", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    elif val == ClientStatus.MOROSO.value:
        return create_badge("⚠ MOROSO", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    elif val == ClientStatus.VETADO.value:
        return create_badge("⛔ VETADO", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_reservation_status_badge(status: ReservationStatus) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado de la reserva."""
    val = status.value if isinstance(status, ReservationStatus) else str(status)
    if val == ReservationStatus.CONFIRMADA.value:
        return create_badge("✓ CONFIRMADA", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    elif val == ReservationStatus.PENDIENTE.value:
        return create_badge("⏳ PENDIENTE", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    elif val == ReservationStatus.CONVERTIDA_A_CONTRATO.value:
        return create_badge("📄 EN CONTRATO", "rgba(14, 165, 233, 0.15)", "#38bdf8", "rgba(14, 165, 233, 0.4)")
    elif val == ReservationStatus.CANCELADA.value:
        return create_badge("✖ CANCELADA", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
    elif val == ReservationStatus.VENCIDA.value:
        return create_badge("⌛ VENCIDA", "rgba(100, 116, 139, 0.2)", "#94a3b8", "rgba(100, 116, 139, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_contract_status_badge(status: ContractStatus) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado del contrato."""
    val = status.value if isinstance(status, ContractStatus) else str(status)
    if val == ContractStatus.ACTIVO.value:
        return create_badge("⚡ ACTIVO", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    elif val == ContractStatus.EN_INSPECCION.value:
        return create_badge("🔍 EN INSPECCIÓN", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    elif val == ContractStatus.EN_LIQUIDACION.value:
        return create_badge("💳 EN LIQUIDACIÓN", "rgba(249, 115, 22, 0.15)", "#fb923c", "rgba(249, 115, 22, 0.4)")
    elif val == ContractStatus.LIQUIDADO.value:
        return create_badge("✓ LIQUIDADO", "rgba(14, 165, 233, 0.15)", "#38bdf8", "rgba(14, 165, 233, 0.4)")
    elif val == ContractStatus.ANULADO.value:
        return create_badge("✖ ANULADO", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_settlement_status_badge(status: SettlementStatus) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado de la liquidación."""
    val = status.value if isinstance(status, SettlementStatus) else str(status)
    if val == SettlementStatus.CERRADA.value:
        return create_badge("✓ CERRADA", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    elif val == SettlementStatus.PENDIENTE_PAGO.value:
        return create_badge("⏳ PENDIENTE PAGO", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_damage_severity_badge(severity: DamageSeverity) -> QLabel:
    """Retorna un badge según la gravedad de la avería física."""
    val = severity.value if isinstance(severity, DamageSeverity) else str(severity)
    if val == DamageSeverity.LEVE.value:
        return create_badge("LEVE", "rgba(56, 189, 248, 0.15)", "#38bdf8", "rgba(56, 189, 248, 0.4)")
    elif val == DamageSeverity.MODERADO.value:
        return create_badge("MODERADO", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    elif val == DamageSeverity.GRAVE.value:
        return create_badge("⛔ GRAVE", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_maintenance_status_badge(status: MaintenanceStatus) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado de la orden de taller."""
    val = status.value if isinstance(status, MaintenanceStatus) else str(status)
    if val == MaintenanceStatus.EN_TALLER.value:
        return create_badge("🔧 EN TALLER", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
    elif val == MaintenanceStatus.FINALIZADO.value:
        return create_badge("✓ FINALIZADO", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    elif val == MaintenanceStatus.CANCELADO.value:
        return create_badge("✖ CANCELADO", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_maintenance_type_badge(m_type: MaintenanceType) -> QLabel:
    """Retorna un badge según si la orden es Preventiva o Correctiva."""
    val = m_type.value if isinstance(m_type, MaintenanceType) else str(m_type)
    if val == MaintenanceType.PREVENTIVO.value:
        return create_badge("🛡 PREVENTIVO", "rgba(14, 165, 233, 0.15)", "#38bdf8", "rgba(14, 165, 233, 0.4)")
    elif val == MaintenanceType.CORRECTIVO.value:
        return create_badge("⚠️ CORRECTIVO", "rgba(249, 115, 22, 0.15)", "#fb923c", "rgba(249, 115, 22, 0.4)")
    return create_badge(val, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")


def get_user_status_badge(activo: bool) -> QLabel:
    """Retorna un badge visualmente codificado por color según el estado del usuario."""
    if activo:
        return create_badge("✓ ACTIVO", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
    return create_badge("⛔ INACTIVO", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")


def get_user_role_badge(rol_nombre: str) -> QLabel:
    """Retorna un badge con la identidad visual del rol del sistema."""
    name = (rol_nombre or "SIN ROL").upper()
    if name == "ADMINISTRADOR":
        return create_badge("👑 ADMINISTRADOR", "rgba(168, 85, 247, 0.15)", "#c084fc", "rgba(168, 85, 247, 0.4)")
    elif name == "GERENTE":
        return create_badge("👔 GERENTE", "rgba(34, 197, 94, 0.15)", "#4ade80", "rgba(34, 197, 94, 0.4)")
    elif name == "AGENTE_VENTAS":
        return create_badge("💼 AGENTE VENTAS", "rgba(56, 189, 248, 0.15)", "#38bdf8", "rgba(56, 189, 248, 0.4)")
    elif name == "INSPECTOR_TALLER":
        return create_badge("🔧 INSPECTOR TALLER", "rgba(249, 115, 22, 0.15)", "#fb923c", "rgba(249, 115, 22, 0.4)")
    return create_badge(name, "rgba(148, 163, 184, 0.15)", "#cbd5e1", "rgba(148, 163, 184, 0.3)")

