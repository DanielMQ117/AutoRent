"""Pruebas automatizadas de integración para el Motor de Contratos, Entrega y Formalización (Fase 5)."""

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
from src.domain.enums import (
    ClientStatus,
    ClientType,
    ContractStatus,
    PaymentMethod,
    PaymentType,
    ReservationStatus,
    VehicleStatus,
)
from src.domain.models import (
    AdditionalDriver,
    Client,
    Contract,
    DriverLicense,
    Reservation,
    Vehicle,
)
from src.services.client_service import client_service
from src.services.contract_service import contract_service
from src.services.reservation_service import reservation_service
from src.services.vehicle_service import vehicle_service


def cleanup_test_contracts_data(cedulas: list[str], placas: list[str]) -> None:
    """Elimina residuos de contratos, pagos, reservas, vehículos y clientes de pruebas."""
    try:
        # 1. Limpiar por clientes
        for cedula in cedulas:
            c = client_service.client_repo.get_by_identificacion(cedula)
            if c and c.id_cliente:
                # Pagos vinculados a contratos del cliente
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM pagos WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_cliente = %s)",
                    (c.id_cliente,),
                )
                # Conductores adicionales
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM conductores_adicionales WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_cliente = %s)",
                    (c.id_cliente,),
                )
                # Contratos
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM contratos WHERE id_cliente = %s", (c.id_cliente,)
                )
                # Reservas
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_cliente = %s", (c.id_cliente,)
                )
                # Cliente
                client_service.client_repo.delete(c.id_cliente)

        # 2. Limpiar por vehículos
        for placa in placas:
            v = vehicle_service.vehicle_repo.get_by_placa(placa)
            if v and v.id_vehiculo:
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM pagos WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM conductores_adicionales WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM contratos WHERE id_vehiculo = %s", (v.id_vehiculo,)
                )
                contract_service.contract_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_vehiculo = %s", (v.id_vehiculo,)
                )
                vehicle_service.vehicle_repo.delete(v.id_vehiculo)
    except Exception as e:
        print(f" -> Aviso durante limpieza de pruebas de contratos: {e}")


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 70)
    print("EJECUTANDO SUITE DE PRUEBAS DE CONTRATOS, ENTREGA Y FORMALIZACIÓN")
    print("=" * 70)

    test_cedulas = ["001-300199-0005Y", "001-020290-0088W"]
    test_placas = ["M-CTR-501", "M-CTR-502"]
    cleanup_test_contracts_data(test_cedulas, test_placas)

    # ------------------------------------------------------------------------
    # PREPARACIÓN: Datos Base (Cliente, Vehículo, Coberturas)
    # ------------------------------------------------------------------------
    print("\n[PREPARACIÓN] Configurando cliente, vehículo y coberturas de prueba...")
    coverages = contract_service.get_coverages()
    assert len(coverages) > 0, "Debe existir al menos una cobertura de seguro configurada."
    test_cov = coverages[0]

    categories = vehicle_service.get_categories()
    assert len(categories) > 0, "Debe existir al menos una categoría de vehículo."
    test_cat = categories[0]
    models = vehicle_service.get_models()

    # Cliente A (Apto con licencia a largo plazo)
    test_client = Client(
        tipo_persona=ClientType.NATURAL,
        identificacion=test_cedulas[0],
        nombres="Valeria",
        apellidos="Reyes Centeno",
        email="valeria.reyes.test@autorent.com",
        telefono="84551122",
        direccion="Los Robles, Managua",
        estado_cliente=ClientStatus.ACTIVO,
    )
    test_license = DriverLicense(
        numero_licencia="NIC-VAL-5501",
        categoria_licencia="CATEGORIA_3",
        fecha_emision=date(2022, 1, 1),
        fecha_vencimiento=date(2030, 12, 31),
        pais_emision="Nicaragua",
    )
    client = client_service.create_client(test_client, test_license)
    assert client.id_cliente is not None
    print(f" -> Cliente preparado: {client.nombre_completo} (ID: {client.id_cliente})")

    # Vehículo A (Disponible con 35,000 km)
    test_vehicle = Vehicle(
        id_modelo=models[0].id_modelo,
        id_categoria=test_cat.id_categoria,
        placa=test_placas[0],
        vin="1CTR501TESTING999",
        color="Blanco Polar",
        kilometraje_actual=35000,
        nivel_combustible_actual=Decimal("1.00"),
        estado=VehicleStatus.DISPONIBLE,
        km_proximo_mantenimiento=40000,
        activo=True,
    )
    vehicle = vehicle_service.create_vehicle(test_vehicle)
    assert vehicle.id_vehiculo is not None
    print(f" -> Vehículo preparado: Placa {vehicle.placa} (ID: {vehicle.id_vehiculo}, {vehicle.kilometraje_actual} km)")

    # ------------------------------------------------------------------------
    # TEST 1: Cálculo de cotización para contrato (calculate_quote)
    # ------------------------------------------------------------------------
    print("\n[TEST 1] Calculando cotización de contrato (días, tarifa, seguro, garantía)...")
    now = datetime.now()
    start_dt = now + timedelta(hours=1)
    end_dt = start_dt + timedelta(days=4)

    dias, tarifa, seguro, total, garantia = contract_service.calculate_quote(
        id_vehiculo=vehicle.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        start_dt=start_dt,
        end_dt=end_dt,
    )
    assert dias == 4, f"Se esperaban 4 días, se obtuvieron {dias}"
    assert tarifa == test_cat.tarifa_base_diaria
    assert seguro == test_cov.costo_diario
    assert total == (tarifa + seguro) * Decimal(4)
    assert garantia == test_cat.deposito_garantia_sugerido
    print(f" -> PASO: Cotización calculada: {dias} días @ (${tarifa} renta + ${seguro} seguro) = ${total} (Garantía: ${garantia})")

    # ------------------------------------------------------------------------
    # TEST 2: Validaciones de Reglas de Negocio (RN-001, RN-002, Odómetro)
    # ------------------------------------------------------------------------
    print("\n[TEST 2] Verificando validaciones de negocio e integridad física...")

    # A. Rechazo por odómetro menor al actual del vehículo
    contract_bad_km = Contract(
        id_cliente=client.id_cliente,
        id_vehiculo=vehicle.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        fecha_hora_inicio_pactada=start_dt,
        fecha_hora_fin_pactada=end_dt,
        kilometraje_salida=34000,  # Menor a 35,000 actual
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=tarifa,
        monto_garantia=garantia,
    )
    try:
        contract_service.create_contract(contract_bad_km)
        assert False, "Debió rechazar odómetro de salida menor al actual."
    except BusinessRuleViolationError as e:
        assert e.code == "INVALID_ODOMETER_VALUE"
        print(f" -> PASO: Intento de reducción de odómetro bloqueado: '{e.message}'")

    # B. Rechazo si cliente tiene licencia que vence antes del fin de contrato
    client_expired = Client(
        tipo_persona=ClientType.NATURAL,
        identificacion=test_cedulas[1],
        nombres="Mauricio",
        apellidos="Licencia Corta",
        email="mauricio.corta@autorent.com",
        telefono="88776655",
        direccion="Managua",
        estado_cliente=ClientStatus.ACTIVO,
    )
    short_license = DriverLicense(
        numero_licencia="NIC-MAU-SHORT",
        categoria_licencia="CATEGORIA_3",
        fecha_emision=date(2020, 1, 1),
        fecha_vencimiento=start_dt.date() + timedelta(days=1),  # Vence antes de end_dt
        pais_emision="Nicaragua",
    )
    created_short_client = client_service.create_client(client_expired, short_license)

    contract_bad_lic = Contract(
        id_cliente=created_short_client.id_cliente,
        id_vehiculo=vehicle.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        fecha_hora_inicio_pactada=start_dt,
        fecha_hora_fin_pactada=end_dt,
        kilometraje_salida=vehicle.kilometraje_actual,
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=tarifa,
        monto_garantia=garantia,
    )
    try:
        contract_service.create_contract(contract_bad_lic)
        assert False, "Debió rechazar cliente con licencia vencida para el fin del contrato."
    except BusinessRuleViolationError as e:
        assert e.code == "EXPIRED_LICENSE_FOR_CONTRACT"
        print(f" -> PASO: Licencia no vigente hasta fin de contrato rechazada: '{e.message}'")

    # C. Rechazo si conductor adicional tiene licencia vencida
    contract_bad_driver = Contract(
        id_cliente=client.id_cliente,
        id_vehiculo=vehicle.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        fecha_hora_inicio_pactada=start_dt,
        fecha_hora_fin_pactada=end_dt,
        kilometraje_salida=vehicle.kilometraje_actual,
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=tarifa,
        monto_garantia=garantia,
        conductores_adicionales=[
            AdditionalDriver(
                nombre_completo="Conductor Inválido",
                identificacion="001-999999-0001A",
                numero_licencia="NIC-COND-INV",
                fecha_vencimiento_licencia=start_dt.date() + timedelta(days=1),
            )
        ],
    )
    try:
        contract_service.create_contract(contract_bad_driver)
        assert False, "Debió rechazar conductor adicional con licencia próxima a vencer."
    except BusinessRuleViolationError as e:
        assert e.code == "EXPIRED_ADDITIONAL_DRIVER_LICENSE"
        print(f" -> PASO: Conductor adicional con licencia vencida rechazado: '{e.message}'")

    # ------------------------------------------------------------------------
    # TEST 3: Emisión y Formalización de Contrato Directo
    # ------------------------------------------------------------------------
    print("\n[TEST 3] Formalizando nuevo contrato directo con conductor adicional y garantía...")
    valid_driver = AdditionalDriver(
        nombre_completo="Fernando José Castillo",
        identificacion="001-150292-0044K",
        numero_licencia="NIC-COND-VAL-1",
        fecha_vencimiento_licencia=date(2029, 6, 30),
    )

    valid_contract = Contract(
        id_cliente=client.id_cliente,
        id_vehiculo=vehicle.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        fecha_hora_inicio_pactada=start_dt,
        fecha_hora_fin_pactada=end_dt,
        kilometraje_salida=35020,  # Odómetro actualizado
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=tarifa,
        monto_garantia=Decimal("400.00"),
        kilometraje_ilimitado=True,
        conductores_adicionales=[valid_driver],
    )

    created_ctr = contract_service.create_contract(
        valid_contract,
        metodo_pago_garantia=PaymentMethod.TARJETA_CREDITO,
        referencia_pago_garantia="HOLD-998877",
    )
    assert created_ctr.id_contrato is not None
    assert created_ctr.codigo_contrato.startswith("CTR-")
    assert created_ctr.estado == ContractStatus.ACTIVO
    print(f" -> PASO: Contrato '{created_ctr.codigo_contrato}' creado exitosamente (ID: {created_ctr.id_contrato})")

    # Comprobar que el vehículo pasó automáticamente a estado ALQUILADO
    veh_after = vehicle_service.get_vehicle(vehicle.id_vehiculo)
    assert veh_after.estado == VehicleStatus.ALQUILADO
    assert veh_after.kilometraje_actual == 35020
    print(f" -> PASO: Vehículo '{veh_after.placa}' pasó a ALQUILADO con km={veh_after.kilometraje_actual}.")

    # Comprobar que se insertó el pago del depósito de garantía
    payments = contract_service.payment_repo.list_by_contract(created_ctr.id_contrato)
    assert len(payments) == 1
    assert payments[0].tipo_movimiento == PaymentType.DEPOSITO_GARANTIA
    assert payments[0].monto == Decimal("400.00")
    print(f" -> PASO: Depósito en garantía por ${payments[0].monto} registrado con TRX: {payments[0].codigo_transaccion}")

    # Comprobar que se persistió el conductor adicional
    loaded_ctr = contract_service.get_contract(created_ctr.id_contrato)
    assert len(loaded_ctr.conductores_adicionales) == 1
    assert loaded_ctr.conductores_adicionales[0].nombre_completo == "Fernando José Castillo"
    print(" -> PASO: Conductor adicional vinculado correctamente.")

    # ------------------------------------------------------------------------
    # TEST 4: Bloqueo de Conflicto / Doble Alquiler (GiST Exclusion)
    # ------------------------------------------------------------------------
    print("\n[TEST 4] Intentando emitir otro contrato para el mismo vehículo en fechas solapadas...")
    overlap_ctr = Contract(
        id_cliente=client.id_cliente,
        id_vehiculo=vehicle.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        fecha_hora_inicio_pactada=start_dt + timedelta(days=1),
        fecha_hora_fin_pactada=end_dt + timedelta(days=1),
        kilometraje_salida=35020,
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=tarifa,
        monto_garantia=garantia,
    )
    try:
        contract_service.create_contract(overlap_ctr)
        assert False, "Debió bloquear emisión de contrato para un vehículo ya alquilado."
    except BusinessRuleViolationError as e:
        print(f" -> PASO: Conflicto de contrato y vehículo no disponible bloqueado: '{e.message}'")

    # ------------------------------------------------------------------------
    # TEST 5: Formalización de Reserva Previa hacia Contrato
    # ------------------------------------------------------------------------
    print("\n[TEST 5] Formalizando contrato desde una reserva previa...")
    # Crear un segundo vehículo
    test_veh2 = Vehicle(
        id_modelo=models[0].id_modelo,
        id_categoria=test_cat.id_categoria,
        placa=test_placas[1],
        vin="1CTR502TESTING888",
        color="Rojo Rubí",
        kilometraje_actual=18000,
        nivel_combustible_actual=Decimal("1.00"),
        estado=VehicleStatus.DISPONIBLE,
        km_proximo_mantenimiento=23000,
        activo=True,
    )
    vehicle2 = vehicle_service.create_vehicle(test_veh2)

    res_start = now + timedelta(days=10)
    res_end = res_start + timedelta(days=3)
    new_res = Reservation(
        id_cliente=client.id_cliente,
        id_categoria=test_cat.id_categoria,
        id_vehiculo=vehicle2.id_vehiculo,
        fecha_hora_inicio=res_start,
        fecha_hora_fin=res_end,
        monto_anticipo=Decimal("50.00"),
    )
    created_res = reservation_service.create_reservation(new_res)
    assert created_res.estado == ReservationStatus.CONFIRMADA
    print(f" -> Reserva previa '{created_res.codigo_reserva}' creada (ID: {created_res.id_reserva})")

    # Convertir reserva en contrato
    contract_from_res = Contract(
        id_reserva=created_res.id_reserva,
        id_cliente=client.id_cliente,
        id_vehiculo=vehicle2.id_vehiculo,
        id_cobertura=test_cov.id_cobertura,
        fecha_hora_inicio_pactada=res_start,
        fecha_hora_fin_pactada=res_end,
        kilometraje_salida=18000,
        combustible_salida=Decimal("1.00"),
        tarifa_diaria_aplicada=tarifa,
        monto_garantia=Decimal("300.00"),
    )
    formalized_ctr = contract_service.create_contract(contract_from_res)
    assert formalized_ctr.id_contrato is not None

    # Comprobar que la reserva pasó a CONVERTIDA_A_CONTRATO
    res_updated = reservation_service.get_reservation(created_res.id_reserva)
    assert res_updated.estado == ReservationStatus.CONVERTIDA_A_CONTRATO
    print(f" -> PASO: Reserva '{res_updated.codigo_reserva}' convertida exitosamente a contrato (Estado: {res_updated.estado.value})")

    # Comprobar que vehículo 2 pasó a ALQUILADO
    v2_after = vehicle_service.get_vehicle(vehicle2.id_vehiculo)
    assert v2_after.estado == VehicleStatus.ALQUILADO
    print(f" -> PASO: Vehículo '{v2_after.placa}' pasó a ALQUILADO tras formalizar la reserva.")

    # ------------------------------------------------------------------------
    # TEST 6: Anulación de Contrato y Restitución de Vehículo
    # ------------------------------------------------------------------------
    print("\n[TEST 6] Anulando contrato y restituyendo vehículo a DISPONIBLE...")
    contract_service.cancel_contract(created_ctr.id_contrato, motivo="Prueba de anulación y restitución")

    canceled_ctr = contract_service.get_contract(created_ctr.id_contrato)
    assert canceled_ctr.estado == ContractStatus.ANULADO
    print(f" -> PASO: Contrato '{canceled_ctr.codigo_contrato}' marcado como ANULADO.")

    veh_liberado = vehicle_service.get_vehicle(vehicle.id_vehiculo)
    assert veh_liberado.estado == VehicleStatus.DISPONIBLE
    print(f" -> PASO: Vehículo '{veh_liberado.placa}' restituido exitosamente a estado DISPONIBLE.")

    # Comprobar movimiento de reembolso de garantía
    reembolso_payments = [
        p for p in contract_service.payment_repo.list_by_contract(created_ctr.id_contrato)
        if p.tipo_movimiento == PaymentType.REEMBOLSO_GARANTIA
    ]
    assert len(reembolso_payments) == 1
    assert reembolso_payments[0].monto == Decimal("400.00")
    print(f" -> PASO: Movimiento de reembolso de garantía registrado: {reembolso_payments[0].codigo_transaccion}")

    # Limpieza final
    cleanup_test_contracts_data(test_cedulas, test_placas)

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE CONTRATOS Y FORMALIZACIÓN PASARON SATISFACTORIAMENTE! [100%]")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
