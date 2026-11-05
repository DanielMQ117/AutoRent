"""Paquete de repositorios basados en SQLAlchemy 2.0 ORM con soporte Multi-Tenant RLS."""

from src.repositories.orm.audit_orm_repository import AuditORMRepository
from src.repositories.orm.base_orm_repository import BaseORMRepository
from src.repositories.orm.client_orm_repository import ClientORMRepository
from src.repositories.orm.contract_orm_repository import (
    ContractORMRepository,
    CoverageORMRepository,
    PaymentORMRepository,
)
from src.repositories.orm.maintenance_orm_repository import MaintenanceORMRepository
from src.repositories.orm.report_orm_repository import ReportORMRepository
from src.repositories.orm.reservation_orm_repository import ReservationORMRepository
from src.repositories.orm.return_orm_repository import ReturnORMRepository
from src.repositories.orm.settlement_orm_repository import SettlementORMRepository
from src.repositories.orm.user_orm_repository import UserORMRepository
from src.repositories.orm.vehicle_orm_repository import VehicleORMRepository

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
