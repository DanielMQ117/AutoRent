"""Suite de pruebas automatizadas de integración para la API RESTful FastAPI y el Cliente HTTP.

Verifica programáticamente:
1. Health Check (`/health`) y listado público de agencias activas (`/api/v1/auth/agencies`).
2. Protección Fail-Fast: Rechazo de peticiones a endpoints protegidos sin token JWT (`401 NO_ACTIVE_TENANT`).
3. Autenticación JWT y Control de Acceso Basado en Roles (RBAC) vía API:
   - Rechazo de credenciales inválidas (`401 INVALID_PASSWORD`).
   - Rechazo de agencia inexistente (`401 TENANT_NOT_FOUND`).
   - Login exitoso como `admin` (`ADMINISTRADOR`) y validación de `/api/v1/auth/me`.
   - Login exitoso como `taller1` (`INSPECTOR_TALLER`), acceso permitido a taller/flota y bloqueo `403 PERMISSION_DENIED` en usuarios y reportes financieros.
4. Endpoints Operativos en Agencia 1: Clientes, Flota, Categorías, Modelos, Reservas, Contratos, Documento HTML de Contrato para firma, Mantenimientos, Reportes y Usuarios.
5. Aislamiento Multi-Tenant y Row Level Security (RLS) a través de FastAPI + JWT:
   - Aprovisionamiento de una segunda agencia temporal (`AUT-API-02`), aislamiento de lectura/escritura y bloqueo `404 CLIENT_NOT_FOUND` ante consulta cruzada por ID entre agencias.
6. Cierre de sesión (`POST /api/v1/auth/logout`) y revocación del token en el cliente HTTP.
"""

from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.api.main import app
from src.api_client import ApiClientError, AutoRentApiClient
from src.core.logger import setup_logging
from src.core.session import session
from src.repositories.orm.user_orm_repository import UserORMRepository
from src.services.auth_service import auth_service
from src.services.user_service import user_service

TEST_API_AGENCY_CODE = "AUT-API-02"


def cleanup_api_second_agency() -> None:
    """Elimina en cascada todos los datos de la agencia temporal AUT-API-02."""
    user_repo = UserORMRepository()
    row = user_repo.execute_query_one(
        "SELECT id_agencia FROM agencias WHERE codigo_agencia = %s",
        (TEST_API_AGENCY_CODE,),
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
    print("EJECUTANDO SUITE DE PRUEBAS: FASTAPI REST API + CLIENTE HTTP + JWT")
    print("=" * 75)

    cleanup_api_second_agency()
    api_client = AutoRentApiClient(app=app)

    try:
        # --------------------------------------------------------------------
        # TEST 1: Health Check y Listado Público de Agencias
        # --------------------------------------------------------------------
        print("\n[TEST 1] Verificando Health Check (/health) y agencias públicas (/api/v1/auth/agencies)...")
        health = api_client.health_check()
        assert health.get("status") in ("ok", "healthy"), f"Health check inválido: {health}"
        assert "version" in health

        agencies = api_client.list_agencies(only_active=True)
        assert isinstance(agencies, list) and len(agencies) >= 1
        assert any(int(a["id_agencia"]) == 1 for a in agencies)
        print(f" -> Health OK (v{health.get('version')}) y {len(agencies)} agencia(s) activa(s) listadas.")
        print("✓ TEST 1 PASÓ: Endpoints públicos verificados.")

        # --------------------------------------------------------------------
        # TEST 2: Protección Fail-Fast sin Token JWT (401 NO_ACTIVE_TENANT)
        # --------------------------------------------------------------------
        print("\n[TEST 2] Verificando protección Fail-Fast en endpoints protegidos sin JWT...")
        auth_service.logout()
        api_client.access_token = None

        try:
            api_client.list_clients()
            assert False, "Debió lanzar ApiClientError 401 al consultar /api/v1/clients sin token"
        except ApiClientError as e:
            assert e.status_code == 401, f"Se esperaba 401, se recibió {e.status_code}"
            assert e.code == "NO_ACTIVE_TENANT", f"Se esperaba NO_ACTIVE_TENANT, se recibió {e.code}"
            print(f" -> Subprueba 2.1: /api/v1/clients bloqueado sin JWT ({e.status_code} {e.code}).")

        try:
            api_client.list_vehicles()
            assert False, "Debió lanzar ApiClientError 401 al consultar /api/v1/vehicles sin token"
        except ApiClientError as e:
            assert e.status_code == 401, f"Se esperaba 401, se recibió {e.status_code}"
            assert e.code == "NO_ACTIVE_TENANT", f"Se esperaba NO_ACTIVE_TENANT, se recibió {e.code}"
            print(f" -> Subprueba 2.2: /api/v1/vehicles bloqueado sin JWT ({e.status_code} {e.code}).")

        print("✓ TEST 2 PASÓ: Protección Fail-Fast sin JWT verificada.")

        # --------------------------------------------------------------------
        # TEST 3: Autenticación JWT y RBAC vía API
        # --------------------------------------------------------------------
        print("\n[TEST 3] Verificando autenticación JWT y control de acceso RBAC vía API...")

        # 3.1 Contraseña inválida -> 401 INVALID_PASSWORD
        try:
            api_client.login("admin", "ClaveIncorrecta999*", tenant_id=1)
            assert False, "Debió rechazar contraseña inválida con 401 INVALID_PASSWORD"
        except ApiClientError as e:
            assert e.status_code == 401
            assert e.code == "INVALID_PASSWORD"
            print(f" -> Subprueba 3.1: Contraseña inválida rechazada ({e.status_code} {e.code}).")

        # 3.2 Agencia inexistente -> 401 TENANT_NOT_FOUND
        try:
            api_client.login("admin", "Admin123*", tenant_id=999999)
            assert False, "Debió rechazar agencia inexistente con 401 TENANT_NOT_FOUND"
        except ApiClientError as e:
            assert e.status_code == 401
            assert e.code == "TENANT_NOT_FOUND"
            print(f" -> Subprueba 3.2: Agencia inexistente rechazada ({e.status_code} {e.code}).")

        # 3.3 Login exitoso como admin en Agencia 1
        login_res = api_client.login("admin", "Admin123*", tenant_id=1)
        assert api_client.access_token is not None and len(api_client.access_token) > 20
        assert login_res["user"]["username"] == "admin"
        assert int(login_res["user"]["tenant_id"]) == 1

        me_res = api_client.get_me()
        assert int(me_res["tenant_id"]) == 1
        assert me_res["rol_nombre"] == "ADMINISTRADOR"
        print(f" -> Subprueba 3.3: Login JWT exitoso para @{me_res['username']} ({me_res['rol_nombre']}, tenant_id={me_res['tenant_id']}).")

        # 3.4 Login como taller1 (INSPECTOR_TALLER) y validación de permisos RBAC
        taller_login = api_client.login("taller1", "Taller123*", tenant_id=1)
        assert taller_login["user"]["rol_nombre"] == "INSPECTOR_TALLER"

        taller_maints = api_client.list_maintenances()
        taller_vehicles = api_client.list_vehicles()
        assert isinstance(taller_maints, list)
        assert isinstance(taller_vehicles, list)

        try:
            api_client.list_users()
            assert False, "INSPECTOR_TALLER no debe poder acceder a /api/v1/users"
        except ApiClientError as e:
            assert e.status_code == 403
            assert e.code == "PERMISSION_DENIED"
            print(f" -> Subprueba 3.4: INSPECTOR_TALLER bloqueado en /api/v1/users ({e.status_code} {e.code}).")

        try:
            api_client.get_financial_report()
            assert False, "INSPECTOR_TALLER no debe poder acceder a /api/v1/reports/financial"
        except ApiClientError as e:
            assert e.status_code == 403
            assert e.code == "PERMISSION_DENIED"
            print(f" -> Subprueba 3.5: INSPECTOR_TALLER bloqueado en /api/v1/reports/financial ({e.status_code} {e.code}).")

        print("✓ TEST 3 PASÓ: Autenticación JWT y RBAC verificados.")

        # --------------------------------------------------------------------
        # TEST 4: Endpoints Operativos en Agencia 1
        # --------------------------------------------------------------------
        print("\n[TEST 4] Verificando endpoints operativos en Agencia 1 como ADMINISTRADOR...")
        api_client.login("admin", "Admin123*", tenant_id=1)

        clients = api_client.list_clients()
        vehicles = api_client.list_vehicles()
        categories = api_client.list_categories()
        models = api_client.list_models()
        reservations = api_client.list_reservations()
        contracts = api_client.list_contracts()
        maintenances = api_client.list_maintenances()
        fin_report = api_client.get_financial_report()
        fleet_report = api_client.get_fleet_report()
        users = api_client.list_users()

        assert len(clients) >= 1, "Debe existir al menos 1 cliente en Agencia 1"
        assert len(vehicles) >= 1, "Debe existir al menos 1 vehículo en Agencia 1"
        assert len(categories) >= 1, "Debe existir al menos 1 categoría en Agencia 1"
        assert len(models) >= 1, "Debe existir al menos 1 modelo en el catálogo"
        assert isinstance(reservations, list)
        assert len(contracts) >= 1, "Debe existir al menos 1 contrato en Agencia 1"
        assert isinstance(maintenances, list)
        assert "total_facturado" in fin_report
        assert "total_vehiculos" in fleet_report
        assert len(users) >= 1

        # Verificar generación de documento HTML del contrato para firma e impresión
        first_contract_id = int(contracts[0]["id_contrato"])
        doc_html = api_client.get_contract_document_html(first_contract_id)
        assert "html" in doc_html and "<!DOCTYPE html>" in doc_html["html"]
        assert int(doc_html["id_contrato"]) == first_contract_id

        print(
            f" -> Datos recuperados vía API: {len(clients)} clientes, {len(vehicles)} vehículos, "
            f"{len(reservations)} reservas, {len(contracts)} contratos (HTML firma OK), {len(users)} usuarios."
        )
        print("✓ TEST 4 PASÓ: Endpoints operativos y documento HTML de contrato verificados.")

        # --------------------------------------------------------------------
        # TEST 5: Aislamiento Multi-Tenant y RLS vía FastAPI + JWT
        # --------------------------------------------------------------------
        print("\n[TEST 5] Verificando aislamiento Multi-Tenant y RLS vía FastAPI + JWT...")
        user_repo = UserORMRepository()
        ag_row = user_repo.execute_query_one(
            """
            INSERT INTO agencias (codigo_agencia, nombre_comercial, ruc_nit, telefono, email, direccion, activo)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id_agencia;
            """,
            (
                TEST_API_AGENCY_CODE,
                "AutoRent Pro - Sucursal API Test",
                "J0310000888888",
                "+505-2222-9999",
                "apitest@autorentpro.com.ni",
                "Managua, Nicaragua",
            ),
        )
        assert ag_row is not None
        tid_2 = int(ag_row["id_agencia"])

        with session.tenant_context(tid_2):
            user_service.create_user(
                username="admin_api2",
                password="AdminApi2*2026",
                nombre_completo="Admin Agencia API 2",
                email="admin@api2.com",
                id_rol=1,
                activo=True,
            )

        # Iniciar sesión vía API en Agencia 2
        api_client.login("admin_api2", "AdminApi2*2026", tenant_id=tid_2)
        assert api_client.tenant_id == tid_2

        clients_t2_initial = api_client.list_clients()
        vehicles_t2_initial = api_client.list_vehicles()
        assert len(clients_t2_initial) == 0, "Agencia 2 debe iniciar con 0 clientes"
        assert len(vehicles_t2_initial) == 0, "Agencia 2 debe iniciar con 0 vehículos"
        print(f" -> Subprueba 5.1: Agencia 2 (tenant_id={tid_2}) aislada con 0 clientes y 0 vehículos iniciales.")

        # Crear un cliente en Agencia 2 vía POST /api/v1/clients
        created_client_t2 = api_client.create_client(
            {
                "tipo_persona": "NATURAL",
                "identificacion": "001-200590-0099Z",
                "nombres": "Rubén",
                "apellidos": "Darío (Agencia 2)",
                "telefono": "+505-8888-9999",
                "email": "ruben.dario@api2.com",
                "direccion": "León, Nicaragua",
                "licencia": {
                    "numero_licencia": "NIC-001-200590",
                    "categoria_licencia": "CATEGORIA_3",
                    "fecha_emision": "2023-01-15",
                    "fecha_vencimiento": "2031-01-15",
                    "pais_emision": "Nicaragua",
                },
            }
        )
        client_t2_id = int(created_client_t2["id_cliente"])
        assert int(created_client_t2["tenant_id"]) == tid_2
        assert len(api_client.list_clients()) == 1
        print(f" -> Subprueba 5.2: Cliente creado en Agencia 2 vía POST /api/v1/clients (ID: {client_t2_id}).")

        # Conmutar a Agencia 1 y verificar bloqueo 404 al intentar leer el cliente de Agencia 2
        api_client.login("admin", "Admin123*", tenant_id=1)
        try:
            api_client.get_client(client_t2_id)
            assert False, "Agencia 1 no debe poder acceder por ID a un cliente de Agencia 2"
        except ApiClientError as e:
            assert e.status_code == 404
            assert e.code == "CLIENT_NOT_FOUND"
            print(f" -> Subprueba 5.3: Acceso cruzado bloqueado desde Agencia 1 ({e.status_code} {e.code}).")

        print("✓ TEST 5 PASÓ: Aislamiento Multi-Tenant y RLS extremo a extremo vía API verificados.")

        # --------------------------------------------------------------------
        # TEST 6: Cierre de Sesión (Logout) y Limpieza del Cliente HTTP
        # --------------------------------------------------------------------
        print("\n[TEST 6] Verificando cierre de sesión (/api/v1/auth/logout)...")
        logout_res = api_client.logout()
        assert api_client.access_token is None
        assert api_client.current_user is None
        assert api_client.tenant_id is None
        assert "message" in logout_res
        print(" -> Token JWT y contexto de usuario limpiados correctamente tras logout.")
        print("✓ TEST 6 PASÓ: Cierre de sesión vía API verificado.")

    finally:
        cleanup_api_second_agency()
        auth_service.login("admin", "Admin123*", tenant_id=1)
        api_client.close()

    print("\n" + "=" * 75)
    print("¡TODAS LAS PRUEBAS DE API RESTFUL Y CLIENTE HTTP FINALIZARON CON ÉXITO [6/6]!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_tests()
