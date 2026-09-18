"""Componentes y widgets reutilizables para la UI."""

from src.ui.components.badges import (
    create_badge,
    get_vehicle_status_badge,
    get_client_status_badge,
    get_reservation_status_badge,
    get_contract_status_badge,
    get_settlement_status_badge,
    get_damage_severity_badge,
)

__all__ = [
    "create_badge",
    "get_vehicle_status_badge",
    "get_client_status_badge",
    "get_reservation_status_badge",
    "get_contract_status_badge",
    "get_settlement_status_badge",
    "get_damage_severity_badge",
]
