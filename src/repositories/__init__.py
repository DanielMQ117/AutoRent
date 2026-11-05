"""Paquete de repositorios para acceso a datos (DAL) basado en SQLAlchemy 2.0 ORM."""

from src.repositories.orm import (
    AuditORMRepository,
    BaseORMRepository,
    ClientORMRepository,
    ContractORMRepository,
    CoverageORMRepository,
    MaintenanceORMRepository,
    PaymentORMRepository,
    ReportORMRepository,
    ReservationORMRepository,
    ReturnORMRepository,
    SettlementORMRepository,
    UserORMRepository,
    VehicleORMRepository,
)

__all__ = [
    "BaseORMRepository",
    "UserORMRepository",
    "AuditORMRepository",
    "ClientORMRepository",
    "VehicleORMRepository",
    "ReservationORMRepository",
    "CoverageORMRepository",
    "PaymentORMRepository",
    "ContractORMRepository",
    "ReturnORMRepository",
    "SettlementORMRepository",
    "MaintenanceORMRepository",
    "ReportORMRepository",
]
