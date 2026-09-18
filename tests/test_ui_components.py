"""Prueba de inicialización y renderizado de componentes de interfaz gráfica (Fase 3)."""

from decimal import Decimal
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

    print("\n[CHECK 6] Inicializando ReservationsView...")
    from src.ui.views.reservations_view import ReservationsView
    reservations_view = ReservationsView()
    assert reservations_view.table.columnCount() == 10
    print(" -> PASO: ReservationsView inicializada con 10 columnas.")

    print("\n[CHECK 7] Inicializando ReservationFormDialog...")
    from src.ui.views.reservation_form_dialog import ReservationFormDialog
    res_dlg = ReservationFormDialog()
    assert "Nueva Reserva de Vehículo" in res_dlg.windowTitle()
    print(" -> PASO: ReservationFormDialog inicializado correctamente.")

    print("\n[CHECK 8] Inicializando ContractsView...")
    from src.ui.views.contracts_view import ContractsView
    contracts_view = ContractsView()
    assert contracts_view.table.columnCount() == 11
    print(" -> PASO: ContractsView inicializada con 11 columnas.")

    print("\n[CHECK 9] Inicializando ContractFormDialog...")
    from src.ui.views.contract_form_dialog import ContractFormDialog
    contract_dlg = ContractFormDialog()
    assert "Apertura de Contrato" in contract_dlg.windowTitle()
    print(" -> PASO: ContractFormDialog inicializado correctamente.")

    print("\n[CHECK 10] Inicializando DashboardView integrado...")
    dashboard = DashboardView()
    assert dashboard.stacked_widget.count() == 7
    print(" -> PASO: DashboardView integrado con las 7 páginas (Dashboard, Clientes, Flota, Reservas, Contratos, Devoluciones, Mantenimientos).")

    print("\n[CHECK 11] Inicializando ReturnsView...")
    from src.ui.views.returns_view import ReturnsView
    returns_view = ReturnsView()
    assert returns_view.table.columnCount() == 10
    print(" -> PASO: ReturnsView inicializada con 10 columnas.")

    print("\n[CHECK 12] Inicializando ReturnFormDialog...")
    from src.ui.views.return_form_dialog import ReturnFormDialog
    from src.domain.models import Contract
    dummy_contract = Contract(
        id_contrato=1,
        codigo_contrato="CTR-202609-0001",
        cliente_nombre="Cliente Prueba",
        vehiculo_placa="M-TEST-01",
        kilometraje_salida=10000,
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=Decimal("50.00"),
        monto_garantia=Decimal("300.00"),
    )
    return_dlg = ReturnFormDialog(contract=dummy_contract)
    assert "Recepción e Inspección de Retorno" in return_dlg.windowTitle()
    print(" -> PASO: ReturnFormDialog inicializado correctamente.")

    print("\n[CHECK 13] Inicializando MaintenancesView...")
    from src.ui.views.maintenances_view import MaintenancesView
    maintenances_view = MaintenancesView()
    assert maintenances_view.table.columnCount() == 9
    print(" -> PASO: MaintenancesView inicializada con 9 columnas.")

    print("\n[CHECK 14] Inicializando MaintenanceFormDialog...")
    from src.ui.views.maintenance_form_dialog import MaintenanceFormDialog
    maint_form_dlg = MaintenanceFormDialog()
    assert "Nueva Orden de Mantenimiento" in maint_form_dlg.windowTitle()
    print(" -> PASO: MaintenanceFormDialog inicializado correctamente.")

    print("\n[CHECK 15] Inicializando MaintenanceCompleteDialog...")
    from src.domain.models import Maintenance
    from src.ui.views.maintenance_complete_dialog import MaintenanceCompleteDialog
    dummy_maint = Maintenance(
        id_mantenimiento=1,
        id_vehiculo=1,
        vehiculo_placa="TEST-01",
        vehiculo_modelo="Toyota Yaris",
        taller_servicio="Taller Central",
        kilometraje_entrada=20000,
        costo_total=Decimal("150.00"),
    )
    complete_dlg = MaintenanceCompleteDialog(maintenance=dummy_maint)
    assert "Finalizar Orden de Mantenimiento" in complete_dlg.windowTitle()
    print(" -> PASO: MaintenanceCompleteDialog inicializado correctamente.")

    print("\n" + "=" * 70)
    print("TODAS LAS VERIFICACIONES DE UI FINALIZARON CON EXITO [15/15]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_ui_checks()
