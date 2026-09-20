"""Paquete de repositorios para acceso a datos (DAL)."""

from src.repositories.audit_repository import AuditRepository
from src.repositories.base_repository import BaseRepository
from src.repositories.client_repository import ClientRepository
from src.repositories.contract_repository import ContractRepository
from src.repositories.coverage_repository import CoverageRepository
from src.repositories.maintenance_repository import MaintenanceRepository
from src.repositories.payment_repository import PaymentRepository
from src.repositories.report_repository import ReportRepository
from src.repositories.reservation_repository import ReservationRepository
from src.repositories.return_repository import ReturnRepository
from src.repositories.settlement_repository import SettlementRepository
from src.repositories.user_repository import UserRepository
from src.repositories.vehicle_repository import VehicleRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "ClientRepository",
    "ContractRepository",
    "CoverageRepository",
    "MaintenanceRepository",
    "PaymentRepository",
    "ReportRepository",
    "ReservationRepository",
    "ReturnRepository",
    "SettlementRepository",
    "UserRepository",
    "VehicleRepository",
]
