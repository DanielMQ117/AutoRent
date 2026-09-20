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
from src.ui.views.returns_view import ReturnsView
from src.ui.views.return_form_dialog import ReturnFormDialog
from src.ui.views.maintenances_view import MaintenancesView
from src.ui.views.maintenance_form_dialog import MaintenanceFormDialog
from src.ui.views.reports_view import ReportsView
from src.ui.views.users_view import UsersView
from src.ui.views.user_form_dialog import UserFormDialog
from src.ui.views.user_password_dialog import UserPasswordDialog

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
    "ReturnsView",
    "ReturnFormDialog",
    "MaintenancesView",
    "MaintenanceFormDialog",
    "MaintenanceCompleteDialog",
    "ReportsView",
    "UsersView",
    "UserFormDialog",
    "UserPasswordDialog",
]
