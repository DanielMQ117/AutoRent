"""Suite de pruebas de integración para la Capa de Persistencia SQLAlchemy 2.0 ORM y Multi-Tenant RLS.

Verifica programáticamente contra PostgreSQL:
1. Conexión del Engine SQLAlchemy 2.0, apertura de sesión con ``get_orm_session()``, registro de los
   19 modelos declarativos y sincronización automática de ``app.current_tenant_id`` (PostgreSQL RLS).
2. Principio Fail-Fast (``NO_ACTIVE_TENANT``) al invocar repositorios ORM multi-tenant sin sesión activa.
3. Consultas de catálogos globales (agencias, roles, marcas, modelos) y búsqueda de usuarios por agencia.
4. Paridad de modelos de dominio (Data Classes) y lecturas operativas en Sede Central (``tenant_id=1``)
   a través de todos los repositorios de ``src/repositories/orm/``.
5. Operaciones CRUD transaccionales con SQLAlchemy ORM y aislamiento estricto Multi-Tenant + RLS entre
   Agencia 1 y Agencia 2 (invisibilidad cruzada por ID y en listados).
6. Auditoría de calidad documental (Docstrings ``\"\"\"...\"\"\"``) en todas las clases y métodos públicos
   de la capa ``src/repositories/orm/``.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import inspect
from pathlib import Path
import sys
from typing import List, Optional, Type

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text

from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.logger import setup_logging
from src.core.session import session
from src.database.orm_base import Base, engine, get_orm_session
import src.database.orm_models as orm_models  # noqa: F401 - Registra los 19 modelos en Base.metadata
from src.domain.enums import ClientStatus, ClientType
from src.domain.models import (
    Agency,
    AuditLog,
    Brand,
    Client,
    ClientHistorySummary,
    Contract,
    DriverLicense,
    FinancialReportSummary,
    FleetUtilizationSummary,
    InsuranceCoverage,
    Maintenance,
    Payment,
    Reservation,
    ReturnInspection,
    Role,
    Settlement,
    User,
    Vehicle,
    VehicleCategory,
    VehicleModel,
)
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

TEMP_AGENCY_CODE = "AUT-ORM-T2"
TEMP_CLIENT_CEDULA = "001-990999-9999Z"


def _clear_active_session() -> None:
    """Limpia por completo la sesión de usuario y cualquier tenant por defecto en memoria."""
    if hasattr(session, "clear") and callable(getattr(session, "clear")):
        session.clear()
    session.logout()


def _activate_agency_session(tenant_id: int = 1, username: str = "admin") -> User:
    """Establece en sesión el usuario indicado de la agencia especificada para pruebas operativas.

    Args:
        tenant_id (int): ID de la agencia a activar en la sesión.
        username (str): Nombre de usuario a cargar desde ``UserORMRepository``.

    Returns:
        User: Entidad de dominio del usuario autenticado en sesión.
    """
    user_repo = UserORMRepository()
    user = user_repo.get_by_username(username, tenant_id=tenant_id)
    if user is None:
        user = User(
            id_usuario=1,
            tenant_id=tenant_id,
            id_rol=1,
            username=username,
            password_hash="",
            nombre_completo=f"Admin Tenant {tenant_id}",
            email=f"admin.t{tenant_id}@autorent.com",
            activo=True,
            rol_nombre="ADMINISTRADOR",
            agencia_nombre=f"Agencia {tenant_id}",
            agencia_codigo=f"AUT-0{tenant_id}",
        )
    session.login(user)
    return user


def test_1_engine_session_and_rls_sync() -> None:
    """[TEST 1] Verifica conexión del Engine SQLAlchemy 2.0, get_orm_session() y sincronización RLS."""
    print("\n[TEST 1] Verificando Engine SQLAlchemy 2.0, metadatos de 19 tablas y contexto RLS...")

    # 1.1 Verificar que las 19 tablas del esquema están registradas en Base.metadata
    expected_tables = {
        "agencias",
        "roles",
        "usuarios",
        "auditoria",
        "marcas",
        "modelos",
        "categorias_vehiculo",
        "vehiculos",
        "clientes",
        "licencias_conducir",
        "coberturas_seguro",
        "reservas",
        "contratos",
        "conductores_adicionales",
        "devoluciones",
        "danios",
        "liquidaciones",
        "pagos",
        "mantenimientos",
    }
    registered_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - registered_tables
    assert not missing, f"Tablas faltantes en Base.metadata: {missing}"
    print(f" -> Subprueba 1.1: {len(expected_tables)}/19 tablas declarativas registradas en Base.metadata.")

    # 1.2 Verificar sincronización automática de app.current_tenant_id con sesión limpia
    _clear_active_session()
    with get_orm_session() as orm_session:
        current_tid = orm_session.execute(text("SHOW app.current_tenant_id;")).scalar()
        assert (current_tid or "") == "", f"Se esperaba tenant vacío sin sesión, se obtuvo '{current_tid}'"
    print(" -> Subprueba 1.2: Sin sesión activa, SHOW app.current_tenant_id retorna cadena vacía ''.")

    # 1.3 Verificar sincronización automática para Agencia 1 y Agencia 2
    with session.tenant_context(1):
        with get_orm_session() as orm_session:
            current_tid_1 = orm_session.execute(text("SHOW app.current_tenant_id;")).scalar()
            assert str(current_tid_1) == "1", f"Se esperaba '1', se obtuvo '{current_tid_1}'"
    print(" -> Subprueba 1.3: Con tenant_context(1), SHOW app.current_tenant_id refleja '1'.")

    with session.tenant_context(2):
        with get_orm_session() as orm_session:
            current_tid_2 = orm_session.execute(text("SHOW app.current_tenant_id;")).scalar()
            assert str(current_tid_2) == "2", f"Se esperaba '2', se obtuvo '{current_tid_2}'"
    print(" -> Subprueba 1.4: Con tenant_context(2), SHOW app.current_tenant_id refleja '2'.")

    print("✓ TEST 1 PASÓ: Engine SQLAlchemy 2.0, get_orm_session() y sincronización RLS verificados.")


def test_2_fail_fast_without_active_tenant() -> None:
    """[TEST 2] Verifica protección Fail-Fast (NO_ACTIVE_TENANT) al invocar repositorios ORM sin sesión."""
    print("\n[TEST 2] Verificando protección Fail-Fast (NO_ACTIVE_TENANT) en repositorios ORM...")
    _clear_active_session()
    assert session.active_tenant_id_or_none is None

    repos_to_check = [
        ("ClientORMRepository.list_all", lambda: ClientORMRepository().list_all()),
        ("VehicleORMRepository.list_all", lambda: VehicleORMRepository().list_all()),
        ("ReservationORMRepository.list_all", lambda: ReservationORMRepository().list_all()),
        ("ContractORMRepository.list_all", lambda: ContractORMRepository().list_all()),
    ]

    for label, action in repos_to_check:
        try:
            action()
            assert False, f"{label} debió lanzar excepción por falta de tenant activo (NO_ACTIVE_TENANT)"
        except (AuthorizationError, AuthenticationError) as exc:
            assert exc.code == "NO_ACTIVE_TENANT", (
                f"Código inesperado en {label}: se esperaba 'NO_ACTIVE_TENANT', se obtuvo '{exc.code}'"
            )
            print(f" -> Bloqueo Fail-Fast confirmado en {label} ({type(exc).__name__}: {exc.code}).")

    print("✓ TEST 2 PASÓ: Todos los repositorios ORM multi-tenant aplican Fail-Fast sin sesión activa.")


def test_3_global_catalogs_and_user_auth() -> None:
    """[TEST 3] Verifica consultas de catálogos globales y búsqueda de usuario por agencia en ORM."""
    print("\n[TEST 3] Verificando catálogos globales y consulta de usuarios mediante SQLAlchemy ORM...")
    user_repo = UserORMRepository()
    vehicle_repo = VehicleORMRepository()

    # 3.1 Agencias globales
    agencies = user_repo.list_agencies(only_active=True)
    assert len(agencies) >= 1, "Debe existir al menos 1 agencia activa (Sede Central)"
    assert all(isinstance(a, Agency) for a in agencies)
    agency_1 = user_repo.get_agency_by_id(1)
    assert isinstance(agency_1, Agency) and agency_1.id_agencia == 1
    print(f" -> Subprueba 3.1: {len(agencies)} agencia(s) activa(s) recuperada(s); Sede Central='{agency_1.nombre_comercial}'.")

    # 3.2 Roles RBAC
    roles = user_repo.list_roles()
    assert len(roles) >= 4, f"Se esperaban al menos 4 roles RBAC, se obtuvieron {len(roles)}"
    assert all(isinstance(r, Role) for r in roles)
    admin_role = user_repo.get_role_by_name("ADMINISTRADOR")
    assert isinstance(admin_role, Role) and admin_role.id_rol is not None
    print(f" -> Subprueba 3.2: {len(roles)} roles RBAC cargados ({', '.join(r.nombre for r in roles)}).")

    # 3.3 Marcas y Modelos automotrices globales
    brands = vehicle_repo.list_brands()
    assert len(brands) >= 1, "El catálogo global de marcas no debe estar vacío"
    assert all(isinstance(b, Brand) for b in brands)

    models = vehicle_repo.list_models()
    assert len(models) >= 1, "El catálogo global de modelos no debe estar vacío"
    assert all(isinstance(m, VehicleModel) and bool(m.marca_nombre) for m in models)
    filtered_models = vehicle_repo.list_models(id_marca=brands[0].id_marca)
    assert all(m.id_marca == brands[0].id_marca for m in filtered_models)
    print(f" -> Subprueba 3.3: {len(brands)} marcas y {len(models)} modelos globales verificados con JOIN a marca.")

    # 3.4 Búsqueda de usuario admin en Agencia 1
    admin_user = user_repo.get_by_username("admin", tenant_id=1)
    assert isinstance(admin_user, User), "El usuario 'admin' debe existir en la Agencia 1"
    assert admin_user.tenant_id == 1
    assert admin_user.username.lower() == "admin"
    assert admin_user.rol_nombre is not None
    assert admin_user.agencia_codigo is not None
    print(
        f" -> Subprueba 3.4: Usuario '{admin_user.username}' (ID={admin_user.id_usuario}, "
        f"Rol={admin_user.rol_nombre}, Agencia={admin_user.agencia_codigo}) recuperado vía ORM."
    )

    print("✓ TEST 3 PASÓ: Catálogos globales y autenticación ORM verificados.")


def test_4_domain_parity_and_orm_reads_agency_1() -> None:
    """[TEST 4] Verifica paridad de modelos de dominio y lecturas en Sede Central (tenant_id=1)."""
    print("\n[TEST 4] Verificando paridad de modelos de dominio y lecturas ORM en Agencia 1 (tenant_id=1)...")
    _activate_agency_session(tenant_id=1, username="admin")

    user_repo = UserORMRepository()
    client_repo = ClientORMRepository()
    vehicle_repo = VehicleORMRepository()
    coverage_repo = CoverageORMRepository()
    reservation_repo = ReservationORMRepository()
    contract_repo = ContractORMRepository()
    payment_repo = PaymentORMRepository()
    return_repo = ReturnORMRepository()
    settlement_repo = SettlementORMRepository()
    maintenance_repo = MaintenanceORMRepository()
    audit_repo = AuditORMRepository()
    report_repo = ReportORMRepository()

    # 4.1 Usuarios y KPIs
    users = user_repo.list_all()
    assert len(users) >= 1 and all(isinstance(u, User) and u.tenant_id == 1 for u in users)
    kpis = user_repo.count_users_kpis()
    assert isinstance(kpis, dict) and kpis.get("total", 0) >= len(users)
    print(f" -> Subprueba 4.1: UserORMRepository -> {len(users)} usuarios en Agencia 1 (KPIs={kpis}).")

    # 4.2 Clientes y Licencias
    clients = client_repo.list_all()
    assert len(clients) >= 1, "Se esperaba al menos 1 cliente semilla en Agencia 1"
    for c in clients:
        assert isinstance(c, Client) and c.tenant_id == 1
        if c.licencia is not None:
            assert isinstance(c.licencia, DriverLicense)
    first_client = client_repo.get_by_id(clients[0].id_cliente)
    assert isinstance(first_client, Client) and first_client.id_cliente == clients[0].id_cliente
    print(f" -> Subprueba 4.2: ClientORMRepository -> {len(clients)} clientes mapeados a Client/DriverLicense.")

    # 4.3 Categorías y Flota de Vehículos
    categories = vehicle_repo.list_categories()
    assert len(categories) >= 1 and all(isinstance(cat, VehicleCategory) and cat.tenant_id == 1 for cat in categories)

    vehicles = vehicle_repo.list_all()
    assert len(vehicles) >= 1, "Se esperaba al menos 1 vehículo semilla en Agencia 1"
    for v in vehicles:
        assert isinstance(v, Vehicle) and v.tenant_id == 1
        assert v.modelo_nombre is not None and v.marca_nombre is not None and v.categoria_nombre is not None

    if hasattr(vehicle_repo, "count_by_status") and callable(getattr(vehicle_repo, "count_by_status")):
        status_counts = vehicle_repo.count_by_status()
        assert isinstance(status_counts, dict)
        print(f" -> Subprueba 4.3: VehicleORMRepository -> {len(vehicles)} vehículos, {len(categories)} categorías, conteo={status_counts}.")
    else:
        print(f" -> Subprueba 4.3: VehicleORMRepository -> {len(vehicles)} vehículos y {len(categories)} categorías verificados.")

    # 4.4 Coberturas de Seguro
    coverages = coverage_repo.list_all()
    assert len(coverages) >= 1 and all(isinstance(cov, InsuranceCoverage) and cov.tenant_id == 1 for cov in coverages)
    cov_one = coverage_repo.get_by_id(coverages[0].id_cobertura)
    assert isinstance(cov_one, InsuranceCoverage)
    print(f" -> Subprueba 4.4: CoverageORMRepository -> {len(coverages)} coberturas de seguro verificadas.")

    # 4.5 Reservas y Disponibilidad Temporal
    reservations = reservation_repo.list_all()
    assert all(isinstance(r, Reservation) and r.tenant_id == 1 for r in reservations)
    future_start = datetime.now() + timedelta(days=90)
    future_end = future_start + timedelta(days=3)
    available_vehicles = reservation_repo.get_available_vehicles_for_period(
        id_categoria=categories[0].id_categoria,
        start_dt=future_start,
        end_dt=future_end,
    )
    assert all(isinstance(av, Vehicle) and av.tenant_id == 1 for av in available_vehicles)
    print(
        f" -> Subprueba 4.5: ReservationORMRepository -> {len(reservations)} reservas y "
        f"{len(available_vehicles)} vehículos disponibles en ventana futura."
    )

    # 4.6 Contratos y Pagos
    contracts = contract_repo.list_all()
    assert all(isinstance(ct, Contract) and ct.tenant_id == 1 for ct in contracts)
    if contracts:
        detailed_ct = contract_repo.get_by_id(contracts[0].id_contrato)
        assert isinstance(detailed_ct, Contract)
        ct_payments = payment_repo.list_by_contract(contracts[0].id_contrato)
        assert all(isinstance(p, Payment) and p.tenant_id == 1 for p in ct_payments)
    total_payments = payment_repo.count_payments()
    assert isinstance(total_payments, int) and total_payments >= 0
    print(f" -> Subprueba 4.6: ContractORMRepository -> {len(contracts)} contratos y {total_payments} pagos registrados.")

    # 4.7 Devoluciones y Liquidaciones
    returns = return_repo.list_all()
    assert all(isinstance(ret, ReturnInspection) and ret.tenant_id == 1 for ret in returns)
    settlements = settlement_repo.list_all()
    assert all(isinstance(st, Settlement) and st.tenant_id == 1 for st in settlements)
    print(f" -> Subprueba 4.7: ReturnORMRepository ({len(returns)}) y SettlementORMRepository ({len(settlements)}) verificados.")

    # 4.8 Mantenimientos y Auditoría
    maintenances = maintenance_repo.list_all()
    assert all(isinstance(m, Maintenance) and m.tenant_id == 1 for m in maintenances)
    logs = audit_repo.list_logs(limit=15)
    assert all(isinstance(lg, AuditLog) and lg.tenant_id == 1 for lg in logs)
    print(f" -> Subprueba 4.8: MaintenanceORMRepository ({len(maintenances)}) y AuditORMRepository ({len(logs)} logs) verificados.")

    # 4.9 Reportes Analíticos (RF-34, RF-35, RF-36)
    today = date.today()
    fin_report = report_repo.get_financial_report(
        fecha_inicio=today - timedelta(days=180),
        fecha_fin=today + timedelta(days=30),
    )
    assert isinstance(fin_report, FinancialReportSummary)

    fleet_report = report_repo.get_fleet_utilization_report(
        fecha_inicio=today - timedelta(days=180),
        fecha_fin=today + timedelta(days=30),
    )
    assert isinstance(fleet_report, FleetUtilizationSummary)
    assert fleet_report.total_vehiculos >= 1

    client_report = report_repo.get_client_history_report()
    assert isinstance(client_report, ClientHistorySummary)
    assert client_report.total_clientes_analizados >= 1
    print(
        f" -> Subprueba 4.9: ReportORMRepository -> Finanzas(${fin_report.total_facturado}), "
        f"Flota({fleet_report.total_vehiculos} uds), Clientes({client_report.total_clientes_analizados} analizados)."
    )

    print("✓ TEST 4 PASÓ: Paridad de dominio y consultas ORM en Sede Central verificadas con éxito.")


def _ensure_second_agency_for_test() -> tuple[int, bool]:
    """Obtiene el ID de una segunda agencia existente o crea una agencia temporal para la prueba RLS.

    Returns:
        tuple[int, bool]: ``(id_agencia_2, created_temporarily)`` indicando si debe eliminarse al final.
    """
    user_repo = UserORMRepository()
    agencies = user_repo.list_agencies(only_active=False)
    for ag in agencies:
        if ag.id_agencia and int(ag.id_agencia) != 1:
            return int(ag.id_agencia), False

    with get_orm_session() as orm_session:
        row = orm_session.execute(
            text(
                """
                INSERT INTO agencias (codigo_agencia, nombre_comercial, ruc_nit, telefono, email, direccion, activo)
                VALUES (:code, :name, :ruc, :phone, :email, :addr, TRUE)
                RETURNING id_agencia;
                """
            ),
            {
                "code": TEMP_AGENCY_CODE,
                "name": "AutoRent Pro - Sucursal Aeropuerto ORM Test",
                "ruc": "J0310000888888",
                "phone": "+505-2255-8888",
                "email": "orm.test2@autorentpro.com.ni",
                "addr": "Aeropuerto Internacional, Managua",
            },
        ).fetchone()
        return int(row[0]), True


def _cleanup_temp_agency(tid_2: int, created_temporarily: bool) -> None:
    """Elimina la agencia temporal si fue aprovisionada específicamente durante el TEST 5."""
    if not created_temporarily:
        return
    with session.tenant_context(tid_2):
        with get_orm_session() as orm_session:
            orm_session.execute(text("DELETE FROM auditoria WHERE tenant_id = :tid;"), {"tid": tid_2})
            orm_session.execute(text("DELETE FROM licencias_conducir WHERE tenant_id = :tid;"), {"tid": tid_2})
            orm_session.execute(text("DELETE FROM clientes WHERE tenant_id = :tid;"), {"tid": tid_2})
            orm_session.execute(text("DELETE FROM agencias WHERE id_agencia = :tid;"), {"tid": tid_2})


def test_5_transactional_crud_and_multitenant_rls_isolation() -> None:
    """[TEST 5] Verifica escritura transaccional ORM y aislamiento Multi-Tenant RLS entre Agencia 1 y Agencia 2."""
    print("\n[TEST 5] Verificando persistencia transaccional ORM y aislamiento Multi-Tenant RLS (Agencia 1 vs Agencia 2)...")
    _activate_agency_session(tenant_id=1, username="admin")
    client_repo = ClientORMRepository()
    audit_repo = AuditORMRepository()

    # Limpieza preventiva si existiera un registro previo de prueba en Agencia 1
    existing_temp = client_repo.get_by_identificacion(TEMP_CLIENT_CEDULA)
    if existing_temp and existing_temp.id_cliente:
        client_repo.delete(existing_temp.id_cliente)

    tid_2, created_temp_agency = _ensure_second_agency_for_test()
    created_client: Optional[Client] = None
    audit_id: int = 0

    try:
        # 5.1 Crear cliente temporal con su licencia en Agencia 1 (tenant_id=1)
        new_client = Client(
            tipo_persona=ClientType.NATURAL,
            identificacion=TEMP_CLIENT_CEDULA,
            nombres="Carlos Alberto",
            apellidos="Fonseca Prueba ORM",
            telefono="+505-8999-7777",
            email="carlos.orm.test@autorent.com.ni",
            direccion="Managua, Sede Central",
            estado_cliente=ClientStatus.ACTIVO,
        )
        new_license = DriverLicense(
            numero_licencia="NIC-ORM-990999",
            categoria_licencia="CATEGORIA_3",
            fecha_emision=date(2023, 5, 10),
            fecha_vencimiento=date(2031, 5, 10),
            pais_emision="Nicaragua",
        )
        created_client = client_repo.create(new_client, license=new_license)
        assert created_client.id_cliente is not None
        assert created_client.tenant_id == 1
        assert created_client.licencia is not None and created_client.licencia.id_licencia is not None
        print(
            f" -> Subprueba 5.1: Cliente temporal ID={created_client.id_cliente} y Licencia "
            f"ID={created_client.licencia.id_licencia} creados en Agencia 1."
        )

        # 5.2 Actualizar cliente y registrar evento en bitácora de auditoría en Agencia 1
        created_client.telefono = "+505-8111-2222"
        updated_client = client_repo.update(created_client, license=new_license)
        assert updated_client.telefono == "+505-8111-2222"

        status_ok = client_repo.update_status(created_client.id_cliente, ClientStatus.MOROSO)
        assert status_ok is True
        reloaded_client = client_repo.get_by_id(created_client.id_cliente)
        assert reloaded_client is not None and reloaded_client.estado_cliente == ClientStatus.MOROSO

        audit_id = audit_repo.record_action(
            id_usuario=session.current_user.id_usuario if session.current_user else 1,
            username="admin",
            accion="TEST_ORM_CREATE_CLIENT",
            tabla_afectada="clientes",
            id_registro=created_client.id_cliente,
            detalles="Prueba de integración ORM Fase 2",
        )
        assert audit_id > 0
        print(f" -> Subprueba 5.2: Update ORM y registro de auditoría ID={audit_id} verificados en Agencia 1.")

        # 5.3 Conmutar contexto a Agencia 2 y verificar aislamiento estricto Multi-Tenant + RLS
        with session.tenant_context(tid_2):
            cross_client = client_repo.get_by_id(created_client.id_cliente)
            assert cross_client is None, "Agencia 2 NO debe poder leer por ID un cliente de Agencia 1"

            cross_by_cedula = client_repo.get_by_identificacion(TEMP_CLIENT_CEDULA)
            assert cross_by_cedula is None, "Agencia 2 NO debe encontrar por cédula un cliente de Agencia 1"

            clients_t2 = client_repo.list_all()
            assert all(c.id_cliente != created_client.id_cliente for c in clients_t2)

            logs_t2 = audit_repo.list_logs(limit=50, accion="TEST_ORM_CREATE_CLIENT")
            assert all(lg.id_auditoria != audit_id for lg in logs_t2)

            with get_orm_session() as orm_session:
                rls_tid = orm_session.execute(text("SHOW app.current_tenant_id;")).scalar()
                assert str(rls_tid) == str(tid_2)

        print(
            f" -> Subprueba 5.3: Aislamiento confirmado en Agencia 2 (tenant_id={tid_2}): "
            "cliente y auditoría de Agencia 1 son completamente invisibles."
        )

    finally:
        # 5.4 Limpieza transaccional de datos de prueba en Agencia 1 y Agencia 2
        _activate_agency_session(tenant_id=1, username="admin")
        if created_client and created_client.id_cliente:
            deleted = client_repo.delete(created_client.id_cliente)
            assert deleted is True
            assert client_repo.get_by_id(created_client.id_cliente) is None
        if audit_id > 0:
            with get_orm_session() as orm_session:
                orm_session.execute(
                    text("DELETE FROM auditoria WHERE id_auditoria = :aid AND tenant_id = 1;"),
                    {"aid": audit_id},
                )
        _cleanup_temp_agency(tid_2, created_temp_agency)
        _activate_agency_session(tenant_id=1, username="admin")
        print(" -> Subprueba 5.4: Registros temporales limpiados e integridad restaurada.")

    print("✓ TEST 5 PASÓ: Escritura transaccional ORM y aislamiento Multi-Tenant RLS verificados.")


def test_6_orm_repositories_docstring_audit() -> None:
    """[TEST 6] Audita programáticamente que todas las clases y métodos públicos ORM posean docstrings."""
    print("\n[TEST 6] Auditando docstrings en todas las clases y métodos públicos de src/repositories/orm/...")

    orm_repo_classes: List[Type] = [
        BaseORMRepository,
        UserORMRepository,
        AuditORMRepository,
        ClientORMRepository,
        VehicleORMRepository,
        ReservationORMRepository,
        ContractORMRepository,
        CoverageORMRepository,
        PaymentORMRepository,
        ReturnORMRepository,
        SettlementORMRepository,
        MaintenanceORMRepository,
        ReportORMRepository,
    ]

    missing_docs: List[str] = []
    total_methods_checked = 0

    for cls in orm_repo_classes:
        if not (cls.__doc__ and cls.__doc__.strip()):
            missing_docs.append(f"{cls.__name__} (clase sin docstring)")

        for method_name, method_fn in inspect.getmembers(cls, predicate=inspect.isfunction):
            if method_name.startswith("_"):
                continue
            total_methods_checked += 1
            if not (method_fn.__doc__ and method_fn.__doc__.strip()):
                missing_docs.append(f"{cls.__name__}.{method_name}()")

        for attr_name, attr_val in cls.__dict__.items():
            if attr_name.startswith("_"):
                continue
            if isinstance(attr_val, property):
                total_methods_checked += 1
                if not (attr_val.fget and attr_val.fget.__doc__ and attr_val.fget.__doc__.strip()):
                    missing_docs.append(f"{cls.__name__}.{attr_name} (property)")

    assert not missing_docs, (
        f"Se encontraron clases/métodos públicos sin docstring en src/repositories/orm/: {missing_docs}"
    )
    print(
        f" -> {len(orm_repo_classes)} clases de repositorios ORM y {total_methods_checked} "
        "métodos/propiedades públicos auditados al 100% con docstrings completos."
    )
    print("✓ TEST 6 PASÓ: Estándar de documentación Google/PEP-257 verificado en todos los repositorios ORM.")


def run_all_tests() -> None:
    """Ejecuta secuencialmente las 6 pruebas integrales de la Fase 2 (SQLAlchemy 2.0 ORM)."""
    setup_logging()
    print("\n" + "=" * 80)
    print("EJECUTANDO SUITE DE PRUEBAS: FASE 2 - CAPA SQLALCHEMY 2.0 ORM Y MULTI-TENANT RLS")
    print("=" * 80)

    try:
        test_1_engine_session_and_rls_sync()
        test_2_fail_fast_without_active_tenant()
        test_3_global_catalogs_and_user_auth()
        test_4_domain_parity_and_orm_reads_agency_1()
        test_5_transactional_crud_and_multitenant_rls_isolation()
        test_6_orm_repositories_docstring_audit()
    finally:
        _activate_agency_session(tenant_id=1, username="admin")
        engine.dispose()

    print("\n" + "=" * 80)
    print("¡TODAS LAS PRUEBAS DE LA CAPA SQLALCHEMY 2.0 ORM PASARON CON ÉXITO [6/6]!")
    print("=" * 80 + "\n")


run_tests = run_all_tests


if __name__ == "__main__":
    run_all_tests()
