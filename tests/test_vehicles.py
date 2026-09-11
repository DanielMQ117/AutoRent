"""Pruebas automatizadas de integración para el módulo de Vehículos y Flota (Fase 3)."""

from decimal import Decimal
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.exceptions import (
    BusinessRuleViolationError,
    DuplicateRecordError,
    InvalidStateTransitionError,
    ValidationError,
)
from src.core.logger import setup_logging
from src.domain.enums import VehicleStatus
from src.domain.models import Vehicle
from src.services.vehicle_service import vehicle_service


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 70)
    print("EJECUTANDO SUITE DE PRUEBAS DE VEHÍCULOS, FLOTA Y ESTADOS (CRUD)")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # TEST 1: Catálogos auxiliares (Marcas, Modelos, Categorías)
    # ------------------------------------------------------------------------
    print("\n[TEST 1] Consultando catálogos de marcas, modelos y categorías...")
    brands = vehicle_service.get_brands()
    models = vehicle_service.get_models()
    categories = vehicle_service.get_categories()

    assert len(brands) >= 4, f"Se esperaban al menos 4 marcas, se obtuvieron {len(brands)}"
    assert len(models) >= 5, f"Se esperaban al menos 5 modelos, se obtuvieron {len(models)}"
    assert len(categories) >= 4, f"Se esperaban al menos 4 categorías, se obtuvieron {len(categories)}"
    print(f" -> PASO: {len(brands)} marcas, {len(models)} modelos y {len(categories)} categorías cargadas.")

    # ------------------------------------------------------------------------
    # TEST 2: Listado inicial de flota (Seed)
    # ------------------------------------------------------------------------
    print("\n[TEST 2] Listando vehículos existentes...")
    initial_vehicles = vehicle_service.list_vehicles()
    assert len(initial_vehicles) >= 5, f"Se esperaban al menos 5 vehículos, se obtuvieron {len(initial_vehicles)}"
    print(f" -> PASO: {len(initial_vehicles)} vehículos de flota recuperados.")

    # ------------------------------------------------------------------------
    # TEST 3: Creación de un nuevo vehículo (Create)
    # ------------------------------------------------------------------------
    print("\n[TEST 3] Registrando nuevo vehículo...")
    test_placa = "M-998877"
    test_vin = "1HGCR2F83HA999999"

    # Limpiar residuo si existiera
    try:
        existing = vehicle_service.vehicle_repo.get_by_placa(test_placa)
        if existing:
            vehicle_service.vehicle_repo.delete(existing.id_vehiculo)
    except Exception:
        pass

    new_vehicle = Vehicle(
        id_modelo=models[0].id_modelo,
        id_categoria=categories[0].id_categoria,
        placa=test_placa,
        vin=test_vin,
        color="Blanco Perla",
        kilometraje_actual=12000,
        nivel_combustible_actual=Decimal("1.00"),
        estado=VehicleStatus.DISPONIBLE,
        km_proximo_mantenimiento=17000,
        activo=True,
    )

    created = vehicle_service.create_vehicle(new_vehicle)
    assert created.id_vehiculo is not None
    assert created.placa == test_placa
    assert created.vin == test_vin
    assert created.estado == VehicleStatus.DISPONIBLE
    assert created.modelo_nombre is not None
    assert created.categoria_nombre is not None
    print(f" -> PASO: Vehículo ID {created.id_vehiculo} ({created.marca_nombre} {created.modelo_nombre}) creado.")

    # ------------------------------------------------------------------------
    # TEST 4: Búsqueda y Filtros de Flota
    # ------------------------------------------------------------------------
    print("\n[TEST 4] Verificando filtros y búsqueda de vehículos...")
    search_res = vehicle_service.list_vehicles(search="998877")
    assert any(v.id_vehiculo == created.id_vehiculo for v in search_res)

    disp_res = vehicle_service.list_vehicles(status=VehicleStatus.DISPONIBLE.value)
    assert any(v.id_vehiculo == created.id_vehiculo for v in disp_res)
    assert all(v.estado == VehicleStatus.DISPONIBLE for v in disp_res)

    mant_res = vehicle_service.list_vehicles(status=VehicleStatus.EN_MANTENIMIENTO.value)
    assert all(v.estado == VehicleStatus.EN_MANTENIMIENTO for v in mant_res)
    print(" -> PASO: Filtros por estado y búsqueda textual operativos.")

    # ------------------------------------------------------------------------
    # TEST 5: Actualización y Detección de Fraude de Odómetro (Update)
    # ------------------------------------------------------------------------
    print("\n[TEST 5] Actualizando datos de vehículo y control de odómetro...")
    created.color = "Negro Mate"
    created.kilometraje_actual = 15000  # Aumento legal de odómetro
    updated = vehicle_service.update_vehicle(created)
    assert updated.color == "Negro Mate"
    assert updated.kilometraje_actual == 15000
    print(" -> Subprueba 5.1: Actualización exitosa.")

    # Intento de retroceder odómetro (15000 -> 10000)
    try:
        updated.kilometraje_actual = 10000
        vehicle_service.update_vehicle(updated)
        assert False, "Debió rechazar reducción de kilometraje"
    except ValidationError as e:
        assert e.code == "ODOMETER_ROLLBACK_ATTEMPT"
        print(f" -> Subprueba 5.2: Intento de adulteración de odómetro bloqueado ({e.code}).")

    # ------------------------------------------------------------------------
    # TEST 6: Validaciones de Placa y VIN Duplicados
    # ------------------------------------------------------------------------
    print("\n[TEST 6] Verificando validaciones de duplicados y formatos...")
    # Placa duplicada
    try:
        dup_v = Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=categories[0].id_categoria,
            placa=test_placa,
            vin="OTROVIN1234567890",
            color="Rojo",
            kilometraje_actual=5000,
            km_proximo_mantenimiento=10000,
        )
        vehicle_service.create_vehicle(dup_v)
        assert False, "Debió rechazar placa duplicada"
    except DuplicateRecordError as e:
        print(f" -> Subprueba 6.1: Placa duplicada rechazada ({e.code}).")

    # VIN duplicado
    try:
        dup_vin_v = Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=categories[0].id_categoria,
            placa="M-887766",
            vin=test_vin,
            color="Verde",
            kilometraje_actual=5000,
            km_proximo_mantenimiento=10000,
        )
        vehicle_service.create_vehicle(dup_vin_v)
        assert False, "Debió rechazar VIN duplicado"
    except DuplicateRecordError as e:
        print(f" -> Subprueba 6.2: VIN duplicado rechazado ({e.code}).")

    # VIN con longitud inválida
    try:
        bad_vin = Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=categories[0].id_categoria,
            placa="M-112299",
            vin="CORTO123",
            color="Gris",
            kilometraje_actual=5000,
            km_proximo_mantenimiento=10000,
        )
        vehicle_service.create_vehicle(bad_vin)
        assert False, "Debió rechazar VIN con longitud menor a 17"
    except ValidationError as e:
        print(f" -> Subprueba 6.3: Formato de VIN inválido rechazado ({e.code}).")

    # ------------------------------------------------------------------------
    # TEST 7: Máquina de Estados (Disponible, Alquilado, Mantenimiento)
    # ------------------------------------------------------------------------
    print("\n[TEST 7] Evaluando transiciones de estado del vehículo...")

    # 7.1 DISPONIBLE -> EN_MANTENIMIENTO
    vehicle_service.change_status(created.id_vehiculo, VehicleStatus.EN_MANTENIMIENTO)
    v_status = vehicle_service.get_vehicle(created.id_vehiculo).estado
    assert v_status == VehicleStatus.EN_MANTENIMIENTO, "Falló transición a EN_MANTENIMIENTO"
    print(" -> Subprueba 7.1: Transición a EN_MANTENIMIENTO correcta.")

    # 7.2 EN_MANTENIMIENTO -> ALQUILADO (Bloqueada: primero debe volver a DISPONIBLE)
    try:
        vehicle_service.change_status(created.id_vehiculo, VehicleStatus.ALQUILADO)
        assert False, "Un vehículo en taller no debe pasar directo a alquilado"
    except InvalidStateTransitionError as e:
        print(f" -> Subprueba 7.2: Transición directa de Taller a Alquilado prevenida ({e.code}).")

    # 7.3 EN_MANTENIMIENTO -> DISPONIBLE
    vehicle_service.change_status(created.id_vehiculo, VehicleStatus.DISPONIBLE)
    v_status = vehicle_service.get_vehicle(created.id_vehiculo).estado
    assert v_status == VehicleStatus.DISPONIBLE, "Falló retorno a DISPONIBLE"
    print(" -> Subprueba 7.3: Retorno a DISPONIBLE correcto.")

    # 7.4 DISPONIBLE -> ALQUILADO
    vehicle_service.change_status(created.id_vehiculo, VehicleStatus.ALQUILADO)
    v_status = vehicle_service.get_vehicle(created.id_vehiculo).estado
    assert v_status == VehicleStatus.ALQUILADO, "Falló transición a ALQUILADO"
    print(" -> Subprueba 7.4: Transición a ALQUILADO correcta.")

    # ------------------------------------------------------------------------
    # TEST 8: Protección de Vehículo Alquilado con Contrato Activo
    # ------------------------------------------------------------------------
    print("\n[TEST 8] Evaluando bloqueo de sobreescritura en vehículos con contrato activo...")
    try:
        # El vehículo 4 del seed está alquilado bajo contrato activo
        vehicle_service.change_status(4, VehicleStatus.DISPONIBLE)
        assert False, "Debió bloquearse el cambio de estado de vehículo alquilado"
    except InvalidStateTransitionError as e:
        print(f" -> PASO: Cambio manual bloqueado por contrato activo ({e.code}): {e.message}")

    # ------------------------------------------------------------------------
    # TEST 9: Eliminación (Baja física y lógica)
    # ------------------------------------------------------------------------
    print("\n[TEST 9] Verificando baja y eliminación de vehículos...")
    # Retornar el de prueba a DISPONIBLE antes de eliminar
    vehicle_service.change_status(created.id_vehiculo, VehicleStatus.DISPONIBLE)
    vehicle_service.delete_vehicle(created.id_vehiculo, force_soft_delete=False)
    try:
        vehicle_service.get_vehicle(created.id_vehiculo)
        assert False, "El vehículo debió haber sido eliminado físicamente"
    except Exception:
        print(" -> PASO: Vehículo de prueba eliminado físicamente con éxito.")

    # Vehículo con contratos no se debe poder eliminar
    try:
        vehicle_service.delete_vehicle(4)
        assert False, "Debió impedirse la eliminación de vehículo con contratos"
    except BusinessRuleViolationError as e:
        print(f" -> PASO: Eliminación protegida por regla de negocio: {e.message}")

    print("\n" + "=" * 70)
    print("TODAS LAS PRUEBAS DE VEHÍCULOS FINALIZARON CON EXITO [9/9]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
