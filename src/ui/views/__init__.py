"""Vistas y ventanas del sistema."""

from src.ui.views.login_view import LoginView
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.clients_view import ClientsView
from src.ui.views.client_form_dialog import ClientFormDialog
from src.ui.views.vehicles_view import VehiclesView
from src.ui.views.vehicle_form_dialog import VehicleFormDialog
from src.ui.views.vehicle_status_dialog import VehicleStatusDialog
from src.ui.views.reservations_view import ReservationsView
from src.ui.views.reservation_form_dialog import ReservationFormDialog
from src.ui.views.contracts_view import ContractsView
from src.ui.views.contract_form_dialog import ContractFormDialog

__all__ = [
    "LoginView",
    "DashboardView",
    "ClientsView",
    "ClientFormDialog",
    "VehiclesView",
    "VehicleFormDialog",
    "VehicleStatusDialog",
    "ReservationsView",
    "ReservationFormDialog",
    "ContractsView",
    "ContractFormDialog",
]
