"""Exportación centralizada de los routers REST de AutoRent Pro API."""

from src.api.routers.auth_router import router as auth_router
from src.api.routers.clients_router import router as clients_router
from src.api.routers.contracts_router import router as contracts_router
from src.api.routers.maintenances_router import router as maintenances_router
from src.api.routers.reports_router import router as reports_router
from src.api.routers.reservations_router import router as reservations_router
from src.api.routers.returns_router import router as returns_router
from src.api.routers.users_router import router as users_router
from src.api.routers.vehicles_router import router as vehicles_router

__all__ = [
    "auth_router",
    "clients_router",
    "vehicles_router",
    "reservations_router",
    "contracts_router",
    "returns_router",
    "maintenances_router",
    "reports_router",
    "users_router",
]
