"""Suite de pruebas automatizadas para la Arquitectura Multi-Tenant (Múltiples Agencias) y Principio Fail-Fast.

Verifica programáticamente:
1. Principio Fail-Fast: Prohibición de acceso a repositorios y servicios sin sesión activa (NO_ACTIVE_TENANT).
2. Rechazo de login ante agencia inexistente (TENANT_NOT_FOUND) o deshabilitada (TENANT_DISABLED).
3. Creación y aprovisionamiento de una segunda agencia independiente (Sucursal León - AUT-LEO-02).
4. Aislamiento de autenticación entre agencias (Cross-Tenant Auth Protection).
5. Independencia de restricciones UNIQUE compuestas por tenant_id (misma cédula, email, licencia, placa y VIN en distintas agencias).
6. Aislamiento estricto de datos operativos (Clientes, Flota, Reservas, Mantenimientos, Reportes y Auditoría) e inaccesibilidad cruzada por ID.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.exceptions import (
    AuthenticationError,
    DuplicateRecordError,
    RecordNotFoundError,
)
from src.core.logger import setup_logging
from src.core.security import hash_password
from src.core.session import session
from src.domain.enums import (
    ClientStatus,
    ClientType,
    MaintenanceType,
    ReservationStatus,
    VehicleStatus,
)
from src.domain.models import (
    Agency,
    Client,
    DriverLicense,
    Maintenance,
    Reservation,
    Vehicle,
)
from src.repositories.user_repository import UserRepository
from src.services.auth_service import auth_service
from src.services.client_service import client_service
from src.services.maintenance_service import maintenance_service
from src.services.report_service import report_service
from src.services.reservation_service import reservation_service
from src.services.user_service import user_service
from src.services.vehicle_service import vehicle_service

TEST_AGENCY_CODE = "AUT-LEO-02"


def cleanup_second_agency() -> None:
    """Elimina en cascada todos los datos pertenecientes a la agencia de prueba AUT-LEO-02."""
    user_repo = UserRepository()
    row = user_repo.execute_query_one(
        "SELECT id_agencia FROM agencias WHERE codigo_agencia = %s",
        (TEST_AGENCY_CODE,),
    )
    if not row:
        return

    tid = int(row["id_agencia"])
    tables = [
        "auditoria",
        "pagos",
        "liquidaciones",
        "danios",
        "devoluciones",
        "conductores_adicionales",
        "contratos",
        "mantenimientos",
        "reservas",
        "licencias_conducir",
        "clientes",
        "vehiculos",
        "coberturas_seguro",
        "categorias_vehiculo",
        "usuarios",
    ]
    with session.tenant_context(tid):
        for tbl in tables:
            user_repo.execute_non_query(f"DELETE FROM {tbl} WHERE tenant_id = %s", (tid,))
        user_repo.execute_non_query("DELETE FROM agencias WHERE id_agencia = %s", (tid,))


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 75)
    print("EJECUTANDO SUITE DE PRUEBAS: ARQUITECTURA MULTI-TENANT Y FAIL-FAST")
    print("=" * 75)

    cleanup_second_agency()

    try:
        # --------------------------------------------------------------------
        # TEST 1: Principio Fail-Fast sin sesión activa (NO_ACTIVE_TENANT)
        # --------------------------------------------------------------------
        print("\n[TEST 1] Verificando principio Fail-Fast sin sesión activa...")
        auth_service.logout()
        assert not session.is_authenticated

        # 1.1 Acceso directo a session.tenant_id sin sesión debe fallar inmediatamente
        try:
            _ = session.tenant_id
            assert False, "Debió lanzar AuthenticationError (NO_ACTIVE_TENANT)"
        except AuthenticationError as e:
            assert e.code == "NO_ACTIVE_TENANT"
            print(f" -> Subprueba 1.1: session.tenant_id bloqueado sin sesión ({e.code}).")

        # 1.2 Consultas a servicios sin sesión activa deben fallar inmediatamente
        try:
            client_service.list_clients()
            assert False, "list_clients() sin sesión debió lanzar AuthenticationError"
        except AuthenticationError as e:
            assert e.code == "NO_ACTIVE_TENANT"
            print(f" -> Subprueba 1.2: client_service.list_clients() bloqueado sin sesión ({e.code}).")

        try:
            vehicle_service.list_vehicles()
            assert False, "list_vehicles() sin sesión debió lanzar AuthenticationError"
        except AuthenticationError as e:
            assert e.code == "NO_ACTIVE_TENANT"
            print(f" -> Subprueba 1.3: vehicle_service.list_vehicles() bloqueado sin sesión ({e.code}).")

        # 1.3 Login en una agencia inexistente debe fallar con TENANT_NOT_FOUND
        try:
            auth_service.login("admin", "Admin123*", tenant_id=999999)
            assert False, "Debió rechazar agencia inexistente con TENANT_NOT_FOUND"
        except AuthenticationError as e:
            assert e.code == "TENANT_NOT_FOUND"
            print(f" -> Subprueba 1.4: Agencia inexistente rechazada ({e.code}).")

        print("✓ TEST 1 PASÓ: Principio Fail-Fast verificado sin valores por defecto implícitos.")

        # --------------------------------------------------------------------
        # TEST 2: Creación y Aprovisionamiento de Segunda Agencia (AUT-LEO-02)
        # --------------------------------------------------------------------
        print("\n[TEST 2] Creando segunda agencia (Sucursal León - AUT-LEO-02)...")
        user_repo = UserRepository()
        ag_row = user_repo.execute_query_one(
            """
            INSERT INTO agencias (codigo_agencia, nombre_comercial, ruc_nit, telefono, email, direccion, activo)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id_agencia;
            """,
            (
                TEST_AGENCY_CODE,
                "AutoRent Pro - Sucursal León",
                "J0310000999999",
                "+505-2311-5500",
                "leon@autorentpro.com.ni",
                "Costado Norte Catedral de León, León, Nicaragua",
            ),
        )
        assert ag_row is not None
        tid_2 = int(ag_row["id_agencia"])
        new_agency = user_repo.get_agency_by_id(tid_2)
        assert new_agency is not None
        print(f" -> Agencia 2 creada con ID {tid_2}: {new_agency.nombre_comercial} ({new_agency.codigo_agencia})")

        active_agencies = auth_service.list_agencies(only_active=True)
        assert any(a.id_agencia == 1 for a in active_agencies)
        assert any(a.id_agencia == tid_2 for a in active_agencies)

        # Aprovisionar usuario admin y categoría base en Agencia 2
        session.set_default_tenant(tid_2)
        admin_t2 = user_service.create_user(
            username="admin",
            password="AdminLeon2026*",
            nombre_completo="Administrador Sucursal León",
            email="admin@autorent.com",  # Mismo email que en Agencia 1
            id_rol=1,
            activo=True,
        )
        assert admin_t2.tenant_id == tid_2

        # Crear una categoría de vehículo en Agencia 2 con el mismo nombre 'ECONÓMICO' de Agencia 1
        cat_row = user_repo.execute_query_one(
            """
            INSERT INTO categorias_vehiculo (tenant_id, nombre, descripcion, tarifa_base_diaria, deposito_garantia_sugerido)
            VALUES (%s, 'ECONÓMICO', 'Flota compacta Sucursal León', 40.00, 250.00)
            RETURNING id_categoria
            """,
            (tid_2,),
        )
        cat_id_t2 = int(cat_row["id_categoria"])
        auth_service.logout()
        print(f" -> Administrador (@{admin_t2.username}, ID {admin_t2.id_usuario}) y categoría ID {cat_id_t2} aprovisionados en Agencia 2.")
        print("✓ TEST 2 PASÓ: Segunda agencia aprovisionada exitosamente.")

        # --------------------------------------------------------------------
        # TEST 3: Aislamiento de Autenticación entre Agencias (Cross-Tenant Auth)
        # --------------------------------------------------------------------
        print("\n[TEST 3] Verificando aislamiento de credenciales entre Agencia 1 y Agencia 2...")

        # 3.1 La clave del admin de Agencia 1 no debe funcionar en Agencia 2
        try:
            auth_service.login("admin", "Admin123*", tenant_id=tid_2)
            assert False, "No debe permitir login en Agencia 2 con la contraseña de Agencia 1"
        except AuthenticationError as e:
            assert e.code == "INVALID_PASSWORD"
            print(" -> Subprueba 3.1: Contraseña de Agencia 1 rechazada en Agencia 2.")

        # 3.2 El usuario 'agente1' de Agencia 1 no existe en Agencia 2
        try:
            auth_service.login("agente1", "Agente123*", tenant_id=tid_2)
            assert False, "Usuario exclusivo de Agencia 1 no debe existir en Agencia 2"
        except AuthenticationError as e:
            assert e.code == "USER_NOT_FOUND"
            print(" -> Subprueba 3.2: Usuario 'agente1' de Agencia 1 no existe en Agencia 2 (USER_NOT_FOUND).")

        # 3.3 Login válido en Agencia 2
        logged_t2 = auth_service.login("admin", "AdminLeon2026*", tenant_id=tid_2)
        assert logged_t2.tenant_id == tid_2
        assert session.tenant_id == tid_2
        assert session.agency_code == TEST_AGENCY_CODE
        assert "León" in session.agency_name
        print(f" -> Subprueba 3.3: Login exitoso en Agencia 2 (tenant_id={session.tenant_id}, {session.agency_code}).")
        print("✓ TEST 3 PASÓ: Autenticación aislada por agencia verificada.")

        # --------------------------------------------------------------------
        # TEST 4: Restricciones UNIQUE Compuestas y Aislamiento de Catálogos
        # --------------------------------------------------------------------
        print("\n[TEST 4] Verificando restricciones UNIQUE (tenant_id, ...) e independencia de datos...")

        # Al iniciar en Agencia 2, no debe ver ningún cliente ni vehículo de Agencia 1
        assert len(client_service.list_clients()) == 0, "Agencia 2 debe iniciar con 0 clientes"
        assert len(vehicle_service.list_vehicles()) == 0, "Agencia 2 debe iniciar con 0 vehículos"
        print(" -> Agencia 2 inicia con 0 clientes y 0 vehículos (aislamiento de lectura confirmado).")

        # Registrar en Agencia 2 un cliente con la MISMA cédula, email y licencia que el cliente 1 de Agencia 1
        client_t2 = client_service.create_client(
            Client(
                tipo_persona=ClientType.NATURAL,
                identificacion="001-150485-0012A",  # Misma cédula que en Agencia 1
                nombres="Ernesto",
                apellidos="Cardenal (León)",
                telefono="+505-8888-1111",
                email="ernesto.cardenal@email.com",  # Mismo email que en Agencia 1
                direccion="León, Nicaragua",
                estado_cliente=ClientStatus.ACTIVO,
            ),
            DriverLicense(
                numero_licencia="NIC-001-150485",  # Misma licencia que en Agencia 1
                categoria_licencia="CATEGORIA_3",
                fecha_emision=date(2022, 1, 10),
                fecha_vencimiento=date(2030, 1, 10),
                pais_emision="Nicaragua",
            ),
        )
        assert client_t2.id_cliente is not None
        assert client_t2.tenant_id == tid_2
        print(f" -> Cliente creado en Agencia 2 con misma cédula/email/licencia que Agencia 1 (ID: {client_t2.id_cliente}).")

        # Intentar duplicar esa misma cédula DENTRO de la Agencia 2 debe fallar
        try:
            client_service.create_client(
                Client(
                    tipo_persona=ClientType.NATURAL,
                    identificacion="001-150485-0012A",
                    nombres="Duplicado",
                    apellidos="Mismo Tenant",
                    telefono="88880000",
                    email="otro.leon@email.com",
                    direccion="León",
                )
            )
            assert False, "Debió rechazar cédula duplicada dentro de la misma Agencia 2"
        except DuplicateRecordError:
            print(" -> Duplicado de cédula dentro de la misma Agencia 2 bloqueado correctamente.")

        # Registrar en Agencia 2 un vehículo con la MISMA placa y VIN que el vehículo 1 de Agencia 1
        models = vehicle_service.get_models()
        vehicle_t2 = vehicle_service.create_vehicle(
            Vehicle(
                id_modelo=models[0].id_modelo,
                id_categoria=cat_id_t2,
                placa="M-345101",  # Misma placa que en Agencia 1
                vin="JTDBT923001234501",  # Mismo VIN que en Agencia 1
                color="Azul León",
                kilometraje_actual=10000,
                nivel_combustible_actual=Decimal("1.00"),
                estado=VehicleStatus.DISPONIBLE,
                km_proximo_mantenimiento=15000,
                activo=True,
            )
        )
        assert vehicle_t2.id_vehiculo is not None
        assert vehicle_t2.tenant_id == tid_2
        print(f" -> Vehículo creado en Agencia 2 con misma placa/VIN que Agencia 1 (ID: {vehicle_t2.id_vehiculo}).")
        print("✓ TEST 4 PASÓ: Restricciones UNIQUE compuestas (tenant_id, ...) verificadas.")

        # --------------------------------------------------------------------
        # TEST 5: Aislamiento Operativo (Reservas, Taller, Reportes) y Bloqueo ID Cruzado
        # --------------------------------------------------------------------
        print("\n[TEST 5] Verificando aislamiento operativo y protección contra acceso cruzado por ID...")
        now = datetime.now()
        res_t2 = reservation_service.create_reservation(
            Reservation(
                id_cliente=client_t2.id_cliente,
                id_categoria=cat_id_t2,
                id_vehiculo=vehicle_t2.id_vehiculo,
                fecha_hora_inicio=now + timedelta(days=5),
                fecha_hora_fin=now + timedelta(days=8),
                monto_anticipo=Decimal("40.00"),
            )
        )
        assert res_t2.tenant_id == tid_2
        assert res_t2.estado == ReservationStatus.CONFIRMADA

        maint_t2 = maintenance_service.create_maintenance_order(
            Maintenance(
                id_vehiculo=vehicle_t2.id_vehiculo,
                tipo_mantenimiento=MaintenanceType.PREVENTIVO,
                kilometraje_entrada=10000,
                taller_servicio="Taller Central León",
                descripcion_trabajo="Cambio de aceite y filtros",
                costo_total=Decimal("65.00"),
            )
        )
        assert maint_t2.tenant_id == tid_2

        # Verificar conteos y reportes en Agencia 2
        assert len(client_service.list_clients()) == 1
        assert len(vehicle_service.list_vehicles()) == 1
        assert len(reservation_service.list_reservations()) == 1
        assert len(maintenance_service.list_maintenances()) == 1

        fleet_rep_t2 = report_service.get_fleet_utilization_report(
            fecha_inicio=date.today() - timedelta(days=30),
            fecha_fin=date.today() + timedelta(days=30),
        )
        assert fleet_rep_t2.total_vehiculos == 1

        # Conmutar sesión a Agencia 1 y verificar que los IDs de Agencia 2 son invisibles
        auth_service.login("admin", "Admin123*", tenant_id=1)
        assert session.tenant_id == 1

        try:
            client_service.get_client(client_t2.id_cliente)
            assert False, "Agencia 1 no debe poder consultar por ID un cliente de Agencia 2"
        except RecordNotFoundError:
            print(" -> Acceso cruzado por ID a cliente de Agencia 2 bloqueado desde Agencia 1.")

        try:
            vehicle_service.get_vehicle(vehicle_t2.id_vehiculo)
            assert False, "Agencia 1 no debe poder consultar por ID un vehículo de Agencia 2"
        except RecordNotFoundError:
            print(" -> Acceso cruzado por ID a vehículo de Agencia 2 bloqueado desde Agencia 1.")

        try:
            reservation_service.get_reservation(res_t2.id_reserva)
            assert False, "Agencia 1 no debe poder consultar por ID una reserva de Agencia 2"
        except RecordNotFoundError:
            print(" -> Acceso cruzado por ID a reserva de Agencia 2 bloqueado desde Agencia 1.")

        try:
            maintenance_service.get_maintenance(maint_t2.id_mantenimiento)
            assert False, "Agencia 1 no debe poder consultar por ID un mantenimiento de Agencia 2"
        except RecordNotFoundError:
            print(" -> Acceso cruzado por ID a mantenimiento de Agencia 2 bloqueado desde Agencia 1.")

        print("✓ TEST 5 PASÓ: Aislamiento operativo y protección contra consultas cruzadas por ID confirmados.")

        # --------------------------------------------------------------------
        # TEST 6: Rechazo de Login en Agencia Deshabilitada (TENANT_DISABLED)
        # --------------------------------------------------------------------
        print("\n[TEST 6] Verificando bloqueo de acceso a agencia inactiva (TENANT_DISABLED)...")
        user_repo.execute_non_query(
            "UPDATE agencias SET activo = FALSE WHERE id_agencia = %s",
            (tid_2,),
        )
        try:
            auth_service.login("admin", "AdminLeon2026*", tenant_id=tid_2)
            assert False, "Debió rechazar inicio de sesión en agencia deshabilitada"
        except AuthenticationError as e:
            assert e.code == "TENANT_DISABLED"
            print(f" -> Agencia deshabilitada rechazada correctamente ({e.code}): {e.message}")
        print("✓ TEST 6 PASÓ: Protección de agencia deshabilitada verificada.")

        # --------------------------------------------------------------------
        # TEST 7: Verificación de Políticas RLS (Row Level Security) en PostgreSQL
        # --------------------------------------------------------------------
        print("\n[TEST 7] Verificando activación e imposición de Row Level Security (RLS Policy) en PostgreSQL...")
        rls_tables = [
            "usuarios",
            "auditoria",
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
        ]

        # 7.1 Verificar en catálogo pg_class y pg_policies que las 15 tablas tienen RLS activo y forzado
        rls_status = user_repo.execute_query(
            """
            SELECT c.relname AS tabla,
                   c.relrowsecurity AS rls_enabled,
                   c.relforcerowsecurity AS rls_forced,
                   COUNT(p.polname) AS num_policies
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_policy p ON p.polrelid = c.oid
            WHERE n.nspname = 'public'
              AND c.relname = ANY(%s)
            GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity;
            """,
            (rls_tables,),
        )
        assert len(rls_status) == 15, f"Se esperaban 15 tablas con RLS, se encontraron {len(rls_status)}"
        for row in rls_status:
            assert row["rls_enabled"] is True, f"RLS no habilitado en {row['tabla']}"
            assert row["rls_forced"] is True, f"FORCE RLS no habilitado en {row['tabla']}"
            assert int(row["num_policies"]) >= 1, f"Sin política RLS en {row['tabla']}"
        print(" -> Subprueba 7.1: 15/15 tablas multi-tenant tienen ENABLE + FORCE ROW LEVEL SECURITY y políticas activas.")

        # 7.2 Verificar imposición real de la política RLS a nivel de motor con el rol 'autorent_app'
        with user_repo.db.transaction() as conn:
            with user_repo.db.cursor(conn=conn, dict_cursor=True) as cur:
                cur.execute("SET LOCAL ROLE autorent_app;")

                # A. Sin contexto de agencia (Fail-Fast en BD): SELECT sin WHERE retorna 0 filas
                cur.execute("SELECT sp_set_tenant_context(NULL);")
                cur.execute("SELECT COUNT(*) AS total FROM clientes;")
                assert int(cur.fetchone()["total"]) == 0, "RLS debe retornar 0 filas cuando no hay tenant en sesión"

                # B. Con contexto en Agencia 2 (tid_2): SELECT * FROM clientes (SIN cláusula WHERE) solo retorna Agencia 2
                cur.execute("SELECT sp_set_tenant_context(%s);", (tid_2,))
                cur.execute("SELECT id_cliente, tenant_id, identificacion FROM clientes;")
                rows_t2 = cur.fetchall()
                assert len(rows_t2) == 1 and int(rows_t2[0]["tenant_id"]) == tid_2
                print(
                    f" -> Subprueba 7.2: Con app.current_tenant_id={tid_2}, 'SELECT * FROM clientes' (sin WHERE) aisló automáticamente 1 fila de Agencia 2."
                )

                # C. Con contexto en Agencia 1: SELECT * FROM clientes (SIN cláusula WHERE) solo retorna Agencia 1
                cur.execute("SELECT sp_set_tenant_context(1);")
                cur.execute("SELECT DISTINCT tenant_id FROM clientes;")
                distinct_tenants = [int(r["tenant_id"]) for r in cur.fetchall()]
                assert distinct_tenants == [1], f"RLS expuso tenants indebidos: {distinct_tenants}"
                print(" -> Subprueba 7.3: Con app.current_tenant_id=1, 'SELECT * FROM clientes' (sin WHERE) retornó únicamente filas de Agencia 1.")

                cur.execute("RESET ROLE;")

        print("✓ TEST 7 PASÓ: Políticas RLS de PostgreSQL verificadas en catálogo y en ejecución real.")

    finally:
        cleanup_second_agency()
        auth_service.login("admin", "Admin123*", tenant_id=1)

    print("\n" + "=" * 75)
    print("¡TODAS LAS PRUEBAS DE TENENCIA MÚLTIPLE, RLS Y FAIL-FAST PASARON CON ÉXITO [7/7]!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_tests()
