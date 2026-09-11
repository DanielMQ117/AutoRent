"""Prueba de inicialización y renderizado de componentes de interfaz gráfica (Fase 3)."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from src.core.logger import setup_logging
from src.services.auth_service import auth_service
from src.ui.views.client_form_dialog import ClientFormDialog
from src.ui.views.clients_view import ClientsView
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.vehicle_form_dialog import VehicleFormDialog
from src.ui.views.vehicle_status_dialog import VehicleStatusDialog
from src.ui.views.vehicles_view import VehiclesView
from src.services.vehicle_service import vehicle_service
from src.services.client_service import client_service


def run_ui_checks():
    setup_logging()
    print("\n" + "=" * 70)
    print("VERIFICANDO COMPONENTES Y VISTAS DE PYSIDE6 (FASE 3)")
    print("=" * 70)

    # Autenticar como admin para tener acceso a todos los módulos
    auth_service.login("admin", "Admin123*")

    # Iniciar QApplication headless si no existe
    app = QApplication.instance()
    if not app:
        app = QApplication(["--platform", "offscreen"])

    print("\n[CHECK 1] Inicializando ClientsView...")
    clients_view = ClientsView()
    assert clients_view.table.columnCount() == 9
    print(" -> PASO: ClientsView inicializada con 9 columnas.")

    print("\n[CHECK 2] Inicializando VehiclesView...")
    vehicles_view = VehiclesView()
    assert vehicles_view.table.columnCount() == 11
    print(" -> PASO: VehiclesView inicializada con 11 columnas.")

    print("\n[CHECK 3] Inicializando ClientFormDialog (Modo Alta y Modo Edición)...")
    create_client_dlg = ClientFormDialog(client=None)
    assert not create_client_dlg.is_edit_mode

    test_client = client_service.get_client(2)  # Lucia Valle
    edit_client_dlg = ClientFormDialog(client=test_client)
    assert edit_client_dlg.is_edit_mode
    assert edit_client_dlg.nombres_input.text() == "Lucia"
    print(" -> PASO: ClientFormDialog verificado en modo alta y modo edición.")

    print("\n[CHECK 4] Inicializando VehicleFormDialog (Modo Alta y Modo Edición)...")
    create_veh_dlg = VehicleFormDialog(vehicle=None)
    assert not create_veh_dlg.is_edit_mode

    test_veh = vehicle_service.get_vehicle(1)  # Yaris
    edit_veh_dlg = VehicleFormDialog(vehicle=test_veh)
    assert edit_veh_dlg.is_edit_mode
    assert edit_veh_dlg.placa_input.text() == test_veh.placa
    print(" -> PASO: VehicleFormDialog verificado en modo alta y modo edición.")

    print("\n[CHECK 5] Inicializando VehicleStatusDialog...")
    status_dlg = VehicleStatusDialog(vehicle=test_veh)
    assert status_dlg.vehicle.placa == test_veh.placa
    print(" -> PASO: VehicleStatusDialog verificado.")

    print("\n[CHECK 6] Inicializando DashboardView integrado...")
    dashboard = DashboardView()
    assert dashboard.stacked_widget.count() == 3
    print(" -> PASO: DashboardView integrado con las 3 páginas (Dashboard, Clientes, Flota).")

    print("\n" + "=" * 70)
    print("TODAS LAS VERIFICACIONES DE UI FINALIZARON CON EXITO [6/6]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_ui_checks()
