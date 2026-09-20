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
    assert dashboard.stacked_widget.count() == 9
    print(" -> PASO: DashboardView integrado con las 9 páginas (Dashboard, Clientes, Flota, Reservas, Contratos, Devoluciones, Mantenimientos, Reportes, Usuarios).")

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

    print("\n[CHECK 16] Inicializando ReportsView...")
    from src.ui.views.reports_view import ReportsView
    reports_view = ReportsView()
    assert reports_view.tabs.count() == 3
    assert reports_view.table_financial.columnCount() == 7
    assert reports_view.table_fleet.columnCount() == 10
    assert reports_view.table_clients.columnCount() == 10
    print(" -> PASO: ReportsView inicializada con 3 pestañas analíticas (Financiero, Flota, Clientes).")

    print("\n[CHECK 17] Inicializando UsersView (Fase 10)...")
    from src.ui.views.users_view import UsersView
    users_view = UsersView()
    assert users_view.tabs.count() == 3
    assert users_view.tbl_users.columnCount() == 7
    assert users_view.tbl_rbac.columnCount() == 9
    assert users_view.tbl_audit.columnCount() == 8
    print(" -> PASO: UsersView inicializada con 3 pestañas (Usuarios, Matriz RBAC, Auditoría RF-05).")

    print("\n[CHECK 18] Inicializando UserFormDialog (Modo Alta y Modo Edición)...")
    from src.ui.views.user_form_dialog import UserFormDialog
    from src.domain.models import User
    dlg_new_user = UserFormDialog()
    assert "Nuevo Usuario" in dlg_new_user.windowTitle()

    dummy_user = User(
        id_usuario=1,
        id_rol=1,
        username="admin",
        nombre_completo="Carlos Fonseca",
        email="admin@rentacar.com",
        activo=True,
    )
    dlg_edit_user = UserFormDialog(user=dummy_user)
    assert "Editar Usuario" in dlg_edit_user.windowTitle()
    assert not dlg_edit_user.txt_username.isEnabled()
    assert not dlg_edit_user.cmb_rol.isEnabled()
    print(" -> PASO: UserFormDialog verificado en modo alta y modo edición con protección de admin.")

    print("\n[CHECK 19] Inicializando UserPasswordDialog...")
    from src.ui.views.user_password_dialog import UserPasswordDialog
    dlg_pwd = UserPasswordDialog(user=dummy_user)
    assert "Restablecer Contraseña" in dlg_pwd.windowTitle()
    print(" -> PASO: UserPasswordDialog verificado correctamente.")

    print("\n" + "=" * 70)
    print("TODAS LAS VERIFICACIONES DE UI FINALIZARON CON EXITO [19/19]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_ui_checks()
