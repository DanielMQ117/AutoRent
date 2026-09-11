"""Pruebas automatizadas de integración para el Motor de Reservas y Disponibilidad (Fase 4)."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.exceptions import (
    BusinessRuleViolationError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)
from src.core.logger import setup_logging
from src.domain.enums import ClientStatus, ClientType, ReservationStatus, VehicleStatus
from src.domain.models import Client, DriverLicense, Reservation, Vehicle
from src.services.client_service import client_service
from src.services.reservation_service import reservation_service
from src.services.vehicle_service import vehicle_service


def cleanup_test_data(cedulas: list[str], placas: list[str]) -> None:
    """Elimina residuos de reservas, vehículos y clientes de pruebas previas."""
    try:
        for cedula in cedulas:
            c = client_service.client_repo.get_by_identificacion(cedula)
            if c and c.id_cliente:
                reservation_service.reservation_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_cliente = %s", (c.id_cliente,)
                )
                client_service.client_repo.delete(c.id_cliente)
        for placa in placas:
            v = vehicle_service.vehicle_repo.get_by_placa(placa)
            if v and v.id_vehiculo:
                reservation_service.reservation_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_vehiculo = %s", (v.id_vehiculo,)
                )
                vehicle_service.vehicle_repo.delete(v.id_vehiculo)
    except Exception as e:
        print(f" -> Aviso durante limpieza de pruebas: {e}")


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 70)
    print("EJECUTANDO SUITE DE PRUEBAS DE RESERVAS Y DISPONIBILIDAD TEMPORAL")
    print("=" * 70)

    test_cedulas = ["001-200199-0001X", "001-010190-0099Z"]
    test_placas = ["M-RES-401"]
    cleanup_test_data(test_cedulas, test_placas)

    # ------------------------------------------------------------------------
    # PREPARACIÓN: Obtener datos de referencia (Categorías, Vehículos, Clientes)
    # ------------------------------------------------------------------------
    print("\n[PREPARACIÓN] Cargando datos base para los escenarios de prueba...")
    categories = vehicle_service.get_categories()
    assert len(categories) > 0, "Debe haber al menos una categoría en el sistema."
    test_cat = categories[0]

    # Crear cliente de prueba con licencia válida a futuro
    cedula_test = test_cedulas[0]
    test_client = Client(
        tipo_persona=ClientType.NATURAL,
        identificacion=cedula_test,
        nombres="Carlos Roberto",
        apellidos="Mendoza Silva",
        email="carlos.mendoza.test@autorent.com",
        telefono="88990011",
        direccion="Altamira D'Este, Managua",
        estado_cliente=ClientStatus.ACTIVO,
    )
    test_license = DriverLicense(
        numero_licencia="NIC-CARLOS-9988",
        categoria_licencia="CATEGORIA_3",
        fecha_emision=date(2022, 1, 1),
        fecha_vencimiento=date(2030, 12, 31),  # Vigente holgadamente
        pais_emision="Nicaragua",
    )
    client = client_service.create_client(test_client, test_license)
    assert client.id_cliente is not None
    print(f" -> Cliente de prueba preparado: {client.nombre_completo} (ID: {client.id_cliente})")

    # Crear vehículo de prueba exclusivo para evitar colisiones con otros tests
    placa_res_test = test_placas[0]
    vin_res_test = "1RES401TESTING999"

    models = vehicle_service.get_models()
    test_vehicle = Vehicle(
        id_modelo=models[0].id_modelo,
        id_categoria=test_cat.id_categoria,
        placa=placa_res_test,
        vin=vin_res_test,
        color="Gris Metal",
        kilometraje_actual=25000,
        nivel_combustible_actual=Decimal("1.00"),
        estado=VehicleStatus.DISPONIBLE,
        km_proximo_mantenimiento=30000,
        activo=True,
    )
    vehicle = vehicle_service.create_vehicle(test_vehicle)
    assert vehicle.id_vehiculo is not None
    print(f" -> Vehículo de prueba preparado: Placa {vehicle.placa} (ID: {vehicle.id_vehiculo})")

    # ------------------------------------------------------------------------
    # TEST 1: Cálculo de duración y cotización económica
    # ------------------------------------------------------------------------
    print("\n[TEST 1] Calculando duración y cotización estimada...")
    now = datetime.now()
    start_dt = now + timedelta(days=2)
    end_dt = start_dt + timedelta(days=5)

    dias, tarifa, total = reservation_service.calculate_duration_and_cost(
        id_categoria=test_cat.id_categoria,
        start_dt=start_dt,
        end_dt=end_dt,
    )
    assert dias == 5, f"Se esperaban 5 días de alquiler, se obtuvieron {dias}"
    assert tarifa == test_cat.tarifa_base_diaria
    assert total == test_cat.tarifa_base_diaria * Decimal(5)
    print(f" -> PASO: Cotización calculada correctamente: {dias} días @ ${tarifa}/día = ${total}")

    # Rango inválido (fin <= inicio)
    try:
        reservation_service.calculate_duration_and_cost(
            id_categoria=test_cat.id_categoria,
            start_dt=end_dt,
            end_dt=start_dt,
        )
        assert False, "Debió rechazar cotización con fin anterior al inicio."
    except ValidationError:
        print(" -> PASO: Rango cronológico inverso rechazado como se esperaba.")

    # ------------------------------------------------------------------------
    # TEST 2: Validación de elegibilidad de Cliente (RN-001, RN-002)
    # ------------------------------------------------------------------------
    print("\n[TEST 2] Verificando validaciones de elegibilidad de clientes...")

    # A. Cliente inexistente
    try:
        res_fake_client = Reservation(
            id_cliente=999999,
            id_categoria=test_cat.id_categoria,
            id_vehiculo=vehicle.id_vehiculo,
            fecha_hora_inicio=start_dt,
            fecha_hora_fin=end_dt,
            monto_anticipo=Decimal("50.00"),
        )
        reservation_service.create_reservation(res_fake_client)
        assert False, "Debió rechazar cliente inexistente."
    except RecordNotFoundError:
        print(" -> PASO: Cliente inexistente rechazado con RecordNotFoundError.")

    # B. Cliente con licencia vencida para la fecha de reserva
    exp_cedula = "001-010190-0099Z"
    existing_exp = client_service.client_repo.get_by_identificacion(exp_cedula)
    if existing_exp:
        client_service.client_repo.delete(existing_exp.id_cliente)

    client_expired_lic = Client(
        tipo_persona=ClientType.NATURAL,
        identificacion=exp_cedula,
        nombres="Juan Licencia",
        apellidos="Vencida",
        email="lic.vencida@autorent.com",
        telefono="88112233",
        direccion="Managua",
        estado_cliente=ClientStatus.ACTIVO,
    )
    expired_license = DriverLicense(
        numero_licencia="NIC-EXP-1122",
        categoria_licencia="CATEGORIA_3",
        fecha_emision=date(2015, 1, 1),
        fecha_vencimiento=start_dt.date() + timedelta(days=1),  # Vence antes de end_dt
        pais_emision="Nicaragua",
    )
    created_exp_client = client_service.create_client(client_expired_lic, expired_license)

    try:
        res_expired_lic = Reservation(
            id_cliente=created_exp_client.id_cliente,
            id_categoria=test_cat.id_categoria,
            id_vehiculo=vehicle.id_vehiculo,
            fecha_hora_inicio=start_dt,
            fecha_hora_fin=end_dt,
            monto_anticipo=Decimal("50.00"),
        )
        reservation_service.create_reservation(res_expired_lic)
        assert False, "Debió rechazar cliente cuya licencia vence antes del fin de la reserva."
    except BusinessRuleViolationError as e:
        assert e.code == "EXPIRED_LICENSE_FOR_RESERVATION"
        print(f" -> PASO: Licencia que vence antes del fin de reserva rechazada: '{e.message}'")

    # C. Cliente en estado VETADO
    client_service.client_repo.update_status(client.id_cliente, ClientStatus.VETADO)
    try:
        res_banned = Reservation(
            id_cliente=client.id_cliente,
            id_categoria=test_cat.id_categoria,
            id_vehiculo=vehicle.id_vehiculo,
            fecha_hora_inicio=start_dt,
            fecha_hora_fin=end_dt,
            monto_anticipo=Decimal("0.00"),
        )
        reservation_service.create_reservation(res_banned)
        assert False, "Debió rechazar cliente VETADO."
    except BusinessRuleViolationError as e:
        assert e.code == "CLIENT_BANNED"
        print(f" -> PASO: Cliente VETADO bloqueado exitosamente: '{e.message}'")

    # Restaurar cliente a ACTIVO
    client_service.client_repo.update_status(client.id_cliente, ClientStatus.ACTIVO)

    # ------------------------------------------------------------------------
    # TEST 3: Verificación de Disponibilidad y Creación de Reserva
    # ------------------------------------------------------------------------
    print("\n[TEST 3] Verificando disponibilidad libre y creando reserva...")
    avail, free_veh, msg = reservation_service.check_availability(
        id_categoria=test_cat.id_categoria,
        start_dt=start_dt,
        end_dt=end_dt,
        id_vehiculo=vehicle.id_vehiculo,
    )
    assert avail is True, "El vehículo nuevo debe estar disponible."
    print(f" -> PASO: Disponibilidad confirmada para vehículo '{vehicle.placa}'. Mensaje: '{msg}'")

    valid_res = Reservation(
        id_cliente=client.id_cliente,
        id_categoria=test_cat.id_categoria,
        id_vehiculo=vehicle.id_vehiculo,
        fecha_hora_inicio=start_dt,
        fecha_hora_fin=end_dt,
        monto_anticipo=Decimal("60.00"),
    )
    created_res = reservation_service.create_reservation(valid_res)
    assert created_res.id_reserva is not None
    assert created_res.codigo_reserva.startswith("RES-")
    assert created_res.estado == ReservationStatus.CONFIRMADA  # Al tener anticipo
    print(f" -> PASO: Reserva creada exitosamente con código '{created_res.codigo_reserva}' (ID: {created_res.id_reserva})")

    # ------------------------------------------------------------------------
    # TEST 4: Detección y Bloqueo de Conflicto Temporal (Solapamiento)
    # ------------------------------------------------------------------------
    print("\n[TEST 4] Intentando reservar el mismo vehículo en fechas solapadas...")

    # Escenario A: Rango que se solapa parcialmente (start_dt + 1 día hasta end_dt + 2 días)
    overlap_start = start_dt + timedelta(days=1)
    overlap_end = end_dt + timedelta(days=2)

    avail_overlap, _, overlap_msg = reservation_service.check_availability(
        id_categoria=test_cat.id_categoria,
        start_dt=overlap_start,
        end_dt=overlap_end,
        id_vehiculo=vehicle.id_vehiculo,
    )
    assert avail_overlap is False, "Debe detectar conflicto temporal para el vehículo ya reservado."
    print(f" -> PASO: Conflicto detectado en check_availability: '{overlap_msg}'")

    # Escenario B: Intentar crear la reserva en conflicto debe lanzar BusinessRuleViolationError
    res_conflict = Reservation(
        id_cliente=client.id_cliente,
        id_categoria=test_cat.id_categoria,
        id_vehiculo=vehicle.id_vehiculo,
        fecha_hora_inicio=overlap_start,
        fecha_hora_fin=overlap_end,
        monto_anticipo=Decimal("30.00"),
    )
    try:
        reservation_service.create_reservation(res_conflict)
        assert False, "Debió rechazar creación de reserva con solapamiento temporal."
    except BusinessRuleViolationError as e:
        assert e.code == "VEHICLE_AVAILABILITY_CONFLICT"
        print(f" -> PASO: Creación bloqueada por colisión temporal: '{e.message}'")

    # ------------------------------------------------------------------------
    # TEST 5: Consultas, Filtros y Transición de Estados
    # ------------------------------------------------------------------------
    print("\n[TEST 5] Consultando y gestionando estados de la reserva...")

    # Búsqueda por código
    fetched = reservation_service.get_reservation(created_res.id_reserva)
    assert fetched.codigo_reserva == created_res.codigo_reserva

    # Lista con filtros
    search_list = reservation_service.list_reservations(search=created_res.codigo_reserva)
    assert len(search_list) == 1
    assert search_list[0].id_reserva == created_res.id_reserva
    print(f" -> PASO: Reserva localizada por búsqueda de código: {search_list[0].codigo_reserva}")

    # Transición: Intentar confirmar una reserva ya CONFIRMADA debe fallar
    try:
        reservation_service.confirm_reservation(created_res.id_reserva)
        assert False, "No se puede confirmar una reserva que ya está CONFIRMADA."
    except InvalidStateTransitionError:
        print(" -> PASO: Reconfirmación redundante rechazada correctamente.")

    # Cancelar la reserva
    reservation_service.cancel_reservation(created_res.id_reserva, motivo="Prueba de cancelación")
    after_cancel = reservation_service.get_reservation(created_res.id_reserva)
    assert after_cancel.estado == ReservationStatus.CANCELADA
    print(" -> PASO: Reserva cancelada satisfactoriamente.")

    # Intentar cancelar una reserva ya CANCELADA debe fallar
    try:
        reservation_service.cancel_reservation(created_res.id_reserva)
        assert False, "No se puede cancelar una reserva ya cancelada."
    except InvalidStateTransitionError:
        print(" -> PASO: Cancelación sobre reserva cancelada rechazada con InvalidStateTransitionError.")

    # ------------------------------------------------------------------------
    # TEST 6: Liberación del vehículo tras cancelación
    # ------------------------------------------------------------------------
    print("\n[TEST 6] Comprobando liberación del vehículo tras cancelación...")
    avail_after_cancel, _, _ = reservation_service.check_availability(
        id_categoria=test_cat.id_categoria,
        start_dt=start_dt,
        end_dt=end_dt,
        id_vehiculo=vehicle.id_vehiculo,
    )
    assert avail_after_cancel is True, "El vehículo debe volver a estar disponible tras cancelar la reserva."
    print(" -> PASO: El vehículo ha quedado liberado para nuevas reservas.")

    # Limpieza final de datos de prueba
    cleanup_test_data(test_cedulas, test_placas)

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE RESERVAS Y DISPONIBILIDAD PASARON SATISFACTORIAMENTE! [100%]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
