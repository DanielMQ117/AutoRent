"""Componentes visuales reutilizables de etiquetas y badges de estado."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

from src.domain.enums import ClientStatus, ReservationStatus, VehicleStatus


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

