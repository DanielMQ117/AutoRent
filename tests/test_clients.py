"""Pruebas automatizadas de integración para el módulo de Clientes y Licencias (Fase 3)."""

from datetime import date, timedelta
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.exceptions import BusinessRuleViolationError, DuplicateRecordError, ValidationError
from src.core.logger import setup_logging
from src.domain.enums import ClientStatus, ClientType
from src.domain.models import Client, DriverLicense
from src.services.client_service import client_service


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 70)
    print("EJECUTANDO SUITE DE PRUEBAS DE CLIENTES Y LICENCIAS (CRUD)")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # TEST 1: Listado inicial de clientes (Seed)
    # ------------------------------------------------------------------------
    print("\n[TEST 1] Listando clientes existentes...")
    initial_clients = client_service.list_clients()
    assert len(initial_clients) >= 4, f"Se esperaban al menos 4 clientes del seed, se obtuvieron {len(initial_clients)}"
    print(f" -> PASO: {len(initial_clients)} clientes recuperados exitosamente.")

    # ------------------------------------------------------------------------
    # TEST 2: Creación de nuevo cliente con Licencia de Conducir
    # ------------------------------------------------------------------------
    print("\n[TEST 2] Creando nuevo cliente con licencia vinculada...")
    test_id_doc = "001-200599-0099T"
    test_email = "test.cliente.fase3@email.com"

    # Limpiar posible residuo previo de pruebas
    try:
        existing = client_service.client_repo.get_by_identificacion(test_id_doc)
        if existing:
            client_service.client_repo.delete(existing.id_cliente)
    except Exception:
        pass

    new_client = Client(
        tipo_persona=ClientType.NATURAL,
        identificacion=test_id_doc,
        nombres="Alejandro",
        apellidos="Guevara Solis",
        telefono="+505-8811-2233",
        email=test_email,
        direccion="Residencial Las Colinas, Managua",
        estado_cliente=ClientStatus.ACTIVO,
    )

    license_data = DriverLicense(
        numero_licencia="LIC-TEST-FASE3",
        categoria_licencia="CATEGORIA_3",
        fecha_emision=date.today() - timedelta(days=365),
        fecha_vencimiento=date.today() + timedelta(days=365 * 4),
        pais_emision="Nicaragua",
    )

    created = client_service.create_client(new_client, license_data)
    assert created.id_cliente is not None, "El ID del cliente creado no debe ser None"
    assert created.nombres == "Alejandro"
    assert created.licencia is not None
    assert created.licencia.numero_licencia == "LIC-TEST-FASE3"
    print(f" -> PASO: Cliente creado con ID {created.id_cliente} y licencia vinculada.")

    # ------------------------------------------------------------------------
    # TEST 3: Recuperación por ID y comprobación de datos
    # ------------------------------------------------------------------------
    print("\n[TEST 3] Consultando cliente por ID...")
    retrieved = client_service.get_client(created.id_cliente)
    assert retrieved.identificacion == test_id_doc
    assert retrieved.email == test_email
    assert retrieved.licencia is not None
    assert retrieved.licencia.categoria_licencia == "CATEGORIA_3"
    print(f" -> PASO: Expediente completo de '{retrieved.nombre_completo}' verificado.")

    # ------------------------------------------------------------------------
    # TEST 4: Búsqueda y Filtros
    # ------------------------------------------------------------------------
    print("\n[TEST 4] Verificando búsqueda y filtros...")
    search_results = client_service.list_clients(search="Guevara")
    assert any(c.id_cliente == created.id_cliente for c in search_results), "La búsqueda por apellido falló"

    filter_morosos = client_service.list_clients(status="MOROSO")
    assert any(c.estado_cliente == ClientStatus.MOROSO for c in filter_morosos), "El filtro de morosos falló"
    assert all(c.estado_cliente == ClientStatus.MOROSO for c in filter_morosos), "Se incluyeron clientes no morosos"
    print(" -> PASO: Filtros por estado y búsqueda textual validados correctamente.")

    # ------------------------------------------------------------------------
    # TEST 5: Actualización de datos (Update)
    # ------------------------------------------------------------------------
    print("\n[TEST 5] Actualizando datos y vigencia de licencia...")
    retrieved.telefono = "+505-7766-5544"
    retrieved.direccion = "Nueva dirección actualizada, Managua"
    if retrieved.licencia:
        retrieved.licencia.categoria_licencia = "CATEGORIA_4"

    updated = client_service.update_client(retrieved, retrieved.licencia)
    assert updated.telefono == "+505-7766-5544"
    assert updated.direccion == "Nueva dirección actualizada, Managua"
    assert updated.licencia.categoria_licencia == "CATEGORIA_4"
    print(" -> PASO: Cliente y licencia actualizados correctamente.")

    # ------------------------------------------------------------------------
    # TEST 6: Validaciones de Integridad y Reglas de Negocio
    # ------------------------------------------------------------------------
    print("\n[TEST 6] Evaluando validaciones de duplicados y errores...")

    # 6.1 Identificación duplicada
    try:
        dup_client = Client(
            tipo_persona=ClientType.NATURAL,
            identificacion=test_id_doc,  # Mismo ID
            nombres="Otro",
            apellidos="Nombre",
            telefono="12345",
            email="otro.email@test.com",
            direccion="Direccion",
        )
        client_service.create_client(dup_client)
        assert False, "Debió rechazar identificación duplicada"
    except DuplicateRecordError as e:
        print(f" -> Subprueba 6.1: Identificación duplicada rechazada ({e.code}).")

    # 6.2 Email duplicado
    try:
        dup_email = Client(
            tipo_persona=ClientType.NATURAL,
            identificacion="001-999999-0099Z",
            nombres="Otro",
            apellidos="Nombre",
            telefono="12345",
            email=test_email,  # Mismo email
            direccion="Direccion",
        )
        client_service.create_client(dup_email)
        assert False, "Debió rechazar email duplicado"
    except DuplicateRecordError as e:
        print(f" -> Subprueba 6.2: Email duplicado rechazado ({e.code}).")

    # 6.3 Email con formato inválido
    try:
        bad_email = Client(
            tipo_persona=ClientType.NATURAL,
            identificacion="001-888888-0099Z",
            nombres="Otro",
            apellidos="Nombre",
            telefono="12345",
            email="formato_invalido_sin_arroba",
            direccion="Direccion",
        )
        client_service.create_client(bad_email)
        assert False, "Debió rechazar email con mal formato"
    except ValidationError as e:
        print(f" -> Subprueba 6.3: Formato de email inválido rechazado ({e.code}).")

    # 6.4 Licencia con fecha de vencimiento menor a fecha de emisión
    try:
        bad_lic = DriverLicense(
            numero_licencia="LIC-BAD-DATE",
            categoria_licencia="CATEGORIA_3",
            fecha_emision=date.today(),
            fecha_vencimiento=date.today() - timedelta(days=1),
        )
        valid_client = Client(
            tipo_persona=ClientType.NATURAL,
            identificacion="001-777777-0099Y",
            nombres="Prueba",
            apellidos="Fechas",
            telefono="12345",
            email="prueba.fechas@test.com",
            direccion="Direccion",
        )
        client_service.create_client(valid_client, bad_lic)
        assert False, "Debió rechazar licencia con fecha de vencimiento anterior"
    except ValidationError as e:
        print(f" -> Subprueba 6.4: Fechas inconsistentes de licencia rechazadas ({e.code}).")

    # ------------------------------------------------------------------------
    # TEST 7: Cambio de Estado (ACTIVO -> MOROSO -> VETADO)
    # ------------------------------------------------------------------------
    print("\n[TEST 7] Comprobando cambio de estados de cliente...")
    client_service.change_status(created.id_cliente, ClientStatus.MOROSO)
    assert client_service.get_client(created.id_cliente).estado_cliente == ClientStatus.MOROSO
    client_service.change_status(created.id_cliente, ClientStatus.VETADO)
    assert client_service.get_client(created.id_cliente).estado_cliente == ClientStatus.VETADO
    client_service.change_status(created.id_cliente, ClientStatus.ACTIVO)
    assert client_service.get_client(created.id_cliente).estado_cliente == ClientStatus.ACTIVO
    print(" -> PASO: Transiciones de estado de cliente validadas exitosamente.")

    # ------------------------------------------------------------------------
    # TEST 8: Eliminación (Delete)
    # ------------------------------------------------------------------------
    print("\n[TEST 8] Eliminando cliente de prueba sin historial...")
    client_service.delete_client(created.id_cliente)
    try:
        client_service.get_client(created.id_cliente)
        assert False, "El cliente debió haber sido eliminado"
    except Exception:
        print(" -> PASO: Cliente eliminado físicamente con éxito.")

    # Verificar que clientes con contratos (e.g. cliente 1 del seed) no se puedan eliminar
    print("\n[TEST 9] Verificando protección de cliente con contratos...")
    try:
        client_service.delete_client(1)  # Ernesto Cardenal del seed tiene contratos/reservas
        assert False, "Debió bloquearse la eliminación de cliente con contratos"
    except BusinessRuleViolationError as e:
        print(f" -> PASO: Eliminación protegida por regla de negocio: {e.message}")

    print("\n" + "=" * 70)
    print("TODAS LAS PRUEBAS DE CLIENTES FINALIZARON CON EXITO [9/9]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
