"""Pruebas automatizadas de integración para el Motor de Devoluciones, Inspección y Liquidación (Fase 6)."""

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
)
from src.core.logger import setup_logging
from src.domain.enums import (
    ClientStatus,
    ClientType,
    ContractStatus,
    DamageSeverity,
    DamageType,
    PaymentMethod,
    PaymentType,
    SettlementStatus,
    VehicleStatus,
)
from src.domain.models import (
    Client,
    Contract,
    Damage,
    DriverLicense,
    ReturnInspection,
    Vehicle,
)
from src.services.client_service import client_service
from src.services.contract_service import contract_service
from src.services.return_service import return_service
from src.services.vehicle_service import vehicle_service


def cleanup_test_returns_data(cedulas: list[str], placas: list[str]) -> None:
    """Elimina en cascada los registros generados durante las pruebas de devoluciones."""
    try:
        # 1. Limpieza por clientes
        for cedula in cedulas:
            c = client_service.client_repo.get_by_identificacion(cedula)
            if c and c.id_cliente:
                # Pagos vinculados a contratos del cliente
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM pagos WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_cliente = %s)",
                    (c.id_cliente,),
                )
                # Liquidaciones
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM liquidaciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_cliente = %s)",
                    (c.id_cliente,),
                )
                # Daños de devoluciones
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM danios WHERE id_devolucion IN "
                    "(SELECT id_devolucion FROM devoluciones WHERE id_contrato IN "
                    "(SELECT id_contrato FROM contratos WHERE id_cliente = %s))",
                    (c.id_cliente,),
                )
                # Devoluciones
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM devoluciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_cliente = %s)",
                    (c.id_cliente,),
                )
                # Conductores adicionales
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM conductores_adicionales WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_cliente = %s)",
                    (c.id_cliente,),
                )
                # Contratos
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM contratos WHERE id_cliente = %s", (c.id_cliente,)
                )
                # Reservas
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_cliente = %s", (c.id_cliente,)
                )
                # Cliente
                client_service.client_repo.delete(c.id_cliente)

        # 2. Limpieza por vehículos
        for placa in placas:
            v = vehicle_service.vehicle_repo.get_by_placa(placa)
            if v and v.id_vehiculo:
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM pagos WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM liquidaciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM danios WHERE id_devolucion IN "
                    "(SELECT id_devolucion FROM devoluciones WHERE id_contrato IN "
                    "(SELECT id_contrato FROM contratos WHERE id_vehiculo = %s))",
                    (v.id_vehiculo,),
                )
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM devoluciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM conductores_adicionales WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM contratos WHERE id_vehiculo = %s", (v.id_vehiculo,)
                )
                return_service.contract_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_vehiculo = %s", (v.id_vehiculo,)
                )
                vehicle_service.vehicle_repo.delete(v.id_vehiculo)
    except Exception as e:
        print(f" -> Aviso durante limpieza de devoluciones: {e}")


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 75)
    print("EJECUTANDO SUITE DE PRUEBAS DE DEVOLUCIONES, INSPECCIÓN Y LIQUIDACIÓN (FASE 6)")
    print("=" * 75)

    test_cedulas = ["001-200595-0011Z"]
    test_placas = ["M-RET-601", "M-RET-602", "M-RET-603", "M-RET-604"]

    cleanup_test_returns_data(test_cedulas, test_placas)

    # ------------------------------------------------------------------------
    # PREPARACIÓN: Cliente, Categoría, Modelo y Cobertura
    # ------------------------------------------------------------------------
    print("\n[PREPARACIÓN] Creando datos maestros de prueba...")
    coverages = contract_service.get_coverages()
    assert len(coverages) > 0, "Se requiere al menos una cobertura configurada."
    test_cov = coverages[0]

    categories = vehicle_service.get_categories()
    assert len(categories) > 0, "Se requiere al menos una categoría de vehículo."
    test_cat = categories[0]
    models = vehicle_service.get_models()

    # Cliente común para las pruebas
    test_client = Client(
        tipo_persona=ClientType.NATURAL,
        identificacion=test_cedulas[0],
        nombres="Rodrigo",
        apellidos="Mendoza Salgado",
        email="rodrigo.mendoza.test@autorent.com",
        telefono="89993344",
        direccion="Residencial Las Colinas, Managua",
        estado_cliente=ClientStatus.ACTIVO,
    )
    test_license = DriverLicense(
        numero_licencia="NIC-ROD-9500",
        categoria_licencia="CATEGORIA_3",
        fecha_emision=date(2021, 1, 1),
        fecha_vencimiento=date(2030, 12, 31),
        pais_emision="Nicaragua",
    )
    client = client_service.create_client(test_client, test_license)
    assert client.id_cliente is not None
    print(f" -> Cliente registrado: {client.nombre_completo} (ID: {client.id_cliente})")

    # ------------------------------------------------------------------------
    # TEST 1: Retorno a tiempo, tanque lleno, sin daños -> Reembolso de garantía
    # ------------------------------------------------------------------------
    print("\n[TEST 1] Retorno a tiempo, sin daños, tanque lleno -> Reembolso de garantía...")
    v1 = vehicle_service.create_vehicle(
        Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=test_cat.id_categoria,
            placa=test_placas[0],
            vin="1RET601TESTING001",
            color="Plata Metálico",
            kilometraje_actual=25000,
            nivel_combustible_actual=Decimal("1.00"),
            estado=VehicleStatus.DISPONIBLE,
            km_proximo_mantenimiento=35000,
            activo=True,
        )
    )

    now = datetime.now()
    start1 = now - timedelta(days=2)
    end1 = now

    ctr1 = contract_service.create_contract(
        Contract(
            id_cliente=client.id_cliente,
            id_vehiculo=v1.id_vehiculo,
            id_cobertura=test_cov.id_cobertura,
            fecha_hora_inicio_pactada=start1,
            fecha_hora_fin_pactada=end1,
            fecha_hora_salida_real=start1,
            kilometraje_salida=25000,
            combustible_salida=Decimal("1.00"),
            tarifa_diaria_aplicada=Decimal("40.00"),
            monto_garantia=Decimal("300.00"),
            kilometraje_ilimitado=True,
        ),
        metodo_pago_garantia=PaymentMethod.TARJETA_CREDITO,
        referencia_pago_garantia="AUTH-RET-01",
    )
    assert ctr1.estado == ContractStatus.ACTIVO
    ctr1 = contract_service.get_contract(ctr1.id_contrato)

    # Devolución: 25,250 km (+250 km), combustible 100%, sin daños, a tiempo
    ret1 = ReturnInspection(
        id_contrato=ctr1.id_contrato,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=25250,
        combustible_retorno=Decimal("1.00"),
        limpieza_aprobada=True,
        accesorios_completos=True,
        observaciones="Retorno en perfecto estado",
        danios=[],
    )

    # Validar cálculo de penalizaciones
    calc1 = return_service.calculate_penalties(ctr1, ret1)
    assert calc1["horas_retraso"] == 0
    assert calc1["cargos_retraso"] == Decimal("0.00")
    assert calc1["combustible_faltante"] == Decimal("0.00")
    assert calc1["cargos_combustible"] == Decimal("0.00")
    assert calc1["cargos_danios"] == Decimal("0.00")
    # Subtotal: 2 días * (40 + cobertura_costo_diario)
    subtotal_esperado = (Decimal("40.00") + (ctr1.cobertura_costo_diario or Decimal("0.00"))) * Decimal(2)
    assert calc1["subtotal_renta"] == subtotal_esperado
    assert calc1["saldo_cliente"] == subtotal_esperado - Decimal("300.00")  # Negativo = Reembolso

    # Procesar retorno y liquidación
    res1 = return_service.process_return_and_settlement(
        id_contrato=ctr1.id_contrato,
        return_data=ret1,
        metodo_pago=PaymentMethod.TARJETA_CREDITO,
        referencia_pago="REFUND-RET-01",
    )

    created_ret1 = res1["return_inspection"]
    created_sett1 = res1["settlement"]
    created_pay1 = res1["payment"]

    assert created_ret1.id_devolucion is not None
    assert created_sett1.estado_liquidacion == SettlementStatus.CERRADA
    assert created_pay1.tipo_movimiento == PaymentType.REEMBOLSO_GARANTIA
    assert created_pay1.monto == abs(calc1["saldo_cliente"])

    # Comprobar estado final de contrato y vehículo
    ctr1_after = contract_service.get_contract(ctr1.id_contrato)
    assert ctr1_after.estado == ContractStatus.LIQUIDADO

    v1_after = vehicle_service.get_vehicle(v1.id_vehiculo)
    assert v1_after.estado == VehicleStatus.DISPONIBLE
    assert v1_after.kilometraje_actual == 25250
    assert v1_after.nivel_combustible_actual == Decimal("1.00")
    print(f" -> PASO: Contrato '{ctr1.codigo_contrato}' LIQUIDADO. Reembolso: ${created_pay1.monto}. Vehículo DISPONIBLE ({v1_after.kilometraje_actual} km).")

    # ------------------------------------------------------------------------
    # TEST 2: Retorno con retraso y faltante de combustible -> Cobro de penalizaciones
    # ------------------------------------------------------------------------
    print("\n[TEST 2] Retorno con 4 horas de retraso y 1/2 tanque faltante -> Cobro de penalizaciones...")
    v2 = vehicle_service.create_vehicle(
        Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=test_cat.id_categoria,
            placa=test_placas[1],
            vin="1RET602TESTING002",
            color="Negro Obsidiana",
            kilometraje_actual=12000,
            nivel_combustible_actual=Decimal("1.00"),
            estado=VehicleStatus.DISPONIBLE,
            km_proximo_mantenimiento=20000,
            activo=True,
        )
    )

    start2 = now - timedelta(days=2)
    end2 = now - timedelta(hours=4)  # Pactado 4 horas antes

    ctr2 = contract_service.create_contract(
        Contract(
            id_cliente=client.id_cliente,
            id_vehiculo=v2.id_vehiculo,
            id_cobertura=test_cov.id_cobertura,
            fecha_hora_inicio_pactada=start2,
            fecha_hora_fin_pactada=end2,
            fecha_hora_salida_real=start2,
            kilometraje_salida=12000,
            combustible_salida=Decimal("1.00"),
            tarifa_diaria_aplicada=Decimal("30.00"),
            monto_garantia=Decimal("100.00"),
            kilometraje_ilimitado=True,
        ),
        metodo_pago_garantia=PaymentMethod.EFECTIVO,
    )
    ctr2 = contract_service.get_contract(ctr2.id_contrato)

    ret2 = ReturnInspection(
        id_contrato=ctr2.id_contrato,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=12180,
        combustible_retorno=Decimal("0.50"),  # Faltante: 0.50 -> 2 cuartos de tanque ($50.00)
        limpieza_aprobada=True,
        accesorios_completos=True,
        observaciones="Retorno con demora y combustible por la mitad",
        danios=[],
    )

    calc2 = return_service.calculate_penalties(ctr2, ret2)
    assert calc2["horas_retraso"] == 4
    assert calc2["cargos_retraso"] == Decimal("40.00")  # 4 hrs * $10/hr
    assert calc2["combustible_faltante"] == Decimal("0.50")
    assert calc2["cargos_combustible"] == Decimal("50.00")  # 0.50 * $100

    # Total bruto = subtotal_renta + retraso ($40) + combustible ($50)
    # Como total_bruto superará la garantía de $100 -> saldo_cliente > 0 -> COBRO
    assert calc2["saldo_cliente"] > Decimal("0.00")

    res2 = return_service.process_return_and_settlement(
        id_contrato=ctr2.id_contrato,
        return_data=ret2,
        metodo_pago=PaymentMethod.EFECTIVO,
        referencia_pago="PAGO-PENAL-02",
    )

    assert res2["payment"].tipo_movimiento == PaymentType.COBRO_LIQUIDACION
    assert res2["payment"].monto == calc2["saldo_cliente"]
    print(f" -> PASO: Cobro de liquidación por penalizaciones (${res2['payment'].monto}) asentado con TRX '{res2['payment'].codigo_transaccion}'.")

    # ------------------------------------------------------------------------
    # TEST 3: Retorno con registro y valuación de daños físicos
    # ------------------------------------------------------------------------
    print("\n[TEST 3] Retorno con múltiples averías leves/moderadas en carrocería...")
    v3 = vehicle_service.create_vehicle(
        Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=test_cat.id_categoria,
            placa=test_placas[2],
            vin="1RET603TESTING003",
            color="Azul Cosmos",
            kilometraje_actual=40000,
            nivel_combustible_actual=Decimal("1.00"),
            estado=VehicleStatus.DISPONIBLE,
            km_proximo_mantenimiento=50000,
            activo=True,
        )
    )

    start3 = now - timedelta(days=1)
    end3 = now
    ctr3 = contract_service.create_contract(
        Contract(
            id_cliente=client.id_cliente,
            id_vehiculo=v3.id_vehiculo,
            id_cobertura=test_cov.id_cobertura,
            fecha_hora_inicio_pactada=start3,
            fecha_hora_fin_pactada=end3,
            fecha_hora_salida_real=start3,
            kilometraje_salida=40000,
            combustible_salida=Decimal("1.00"),
            tarifa_diaria_aplicada=Decimal("50.00"),
            monto_garantia=Decimal("400.00"),
            kilometraje_ilimitado=True,
        )
    )
    ctr3 = contract_service.get_contract(ctr3.id_contrato)

    danios_lista = [
        Damage(
            zona_carroceria="Parachoques Delantero",
            tipo_danio=DamageType.RAYON,
            gravedad=DamageSeverity.LEVE,
            descripcion="Rayón superficial en esquina derecha",
            costo_reparacion=Decimal("75.00"),
        ),
        Damage(
            zona_carroceria="Retrovisor Izquierdo",
            tipo_danio=DamageType.ROTURA,
            gravedad=DamageSeverity.MODERADO,
            descripcion="Espejo lateral con cristal fisurado",
            costo_reparacion=Decimal("110.00"),
        ),
    ]

    ret3 = ReturnInspection(
        id_contrato=ctr3.id_contrato,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=40150,
        combustible_retorno=Decimal("1.00"),
        limpieza_aprobada=True,
        accesorios_completos=True,
        observaciones="Vehículo presenta 2 averías en carrocería",
        danios=danios_lista,
    )
    assert ret3.costo_total_danios == Decimal("185.00")
    assert ret3.tiene_danio_grave is False

    res3 = return_service.process_return_and_settlement(
        id_contrato=ctr3.id_contrato,
        return_data=ret3,
        metodo_pago=PaymentMethod.TARJETA_DEBITO,
    )

    # Verificar que los daños quedaron persistidos y se consultan
    ret_consultada = return_service.get_return(res3["return_inspection"].id_devolucion)
    assert len(ret_consultada.danios) == 2
    assert ret_consultada.costo_total_danios == Decimal("185.00")

    # Vehículo no tiene daño grave, debe volver a DISPONIBLE
    v3_after = vehicle_service.get_vehicle(v3.id_vehiculo)
    assert v3_after.estado == VehicleStatus.DISPONIBLE
    print(f" -> PASO: Averías persistidas ({len(ret_consultada.danios)}) por total de ${ret_consultada.costo_total_danios}. Vehículo DISPONIBLE.")

    # ------------------------------------------------------------------------
    # TEST 4: Daño GRAVE redirige el vehículo a EN_MANTENIMIENTO
    # ------------------------------------------------------------------------
    print("\n[TEST 4] Daño de severidad GRAVE redirige vehículo a EN_MANTENIMIENTO...")
    v4 = vehicle_service.create_vehicle(
        Vehicle(
            id_modelo=models[0].id_modelo,
            id_categoria=test_cat.id_categoria,
            placa=test_placas[3],
            vin="1RET604TESTING004",
            color="Rojo Carmesí",
            kilometraje_actual=15000,
            nivel_combustible_actual=Decimal("1.00"),
            estado=VehicleStatus.DISPONIBLE,
            km_proximo_mantenimiento=25000,
            activo=True,
        )
    )

    start4 = now - timedelta(days=1)
    end4 = now
    ctr4 = contract_service.create_contract(
        Contract(
            id_cliente=client.id_cliente,
            id_vehiculo=v4.id_vehiculo,
            id_cobertura=test_cov.id_cobertura,
            fecha_hora_inicio_pactada=start4,
            fecha_hora_fin_pactada=end4,
            fecha_hora_salida_real=start4,
            kilometraje_salida=15000,
            combustible_salida=Decimal("1.00"),
            tarifa_diaria_aplicada=Decimal("50.00"),
            monto_garantia=Decimal("500.00"),
            kilometraje_ilimitado=True,
        )
    )
    ctr4 = contract_service.get_contract(ctr4.id_contrato)

    ret4 = ReturnInspection(
        id_contrato=ctr4.id_contrato,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=15100,
        combustible_retorno=Decimal("1.00"),
        limpieza_aprobada=True,
        accesorios_completos=True,
        observaciones="Colisión grave en suspensión",
        danios=[
            Damage(
                zona_carroceria="Suspensión Delantera Derecha",
                tipo_danio=DamageType.GOLPE,
                gravedad=DamageSeverity.GRAVE,
                descripcion="Brazo de control doblado y amortiguador reventado",
                costo_reparacion=Decimal("600.00"),
            )
        ],
    )
    assert ret4.tiene_danio_grave is True

    return_service.process_return_and_settlement(
        id_contrato=ctr4.id_contrato,
        return_data=ret4,
        metodo_pago=PaymentMethod.TRANSFERENCIA,
    )

    # El contrato debe estar LIQUIDADO y el vehículo EN_MANTENIMIENTO
    ctr4_after = contract_service.get_contract(ctr4.id_contrato)
    assert ctr4_after.estado == ContractStatus.LIQUIDADO

    v4_after = vehicle_service.get_vehicle(v4.id_vehiculo)
    assert v4_after.estado == VehicleStatus.EN_MANTENIMIENTO, f"Esperado EN_MANTENIMIENTO, obtenido {v4_after.estado}"
    print(f" -> PASO: Vehículo '{v4_after.placa}' derivado correctamente a EN_MANTENIMIENTO por daño GRAVE.")

    # ------------------------------------------------------------------------
    # TEST 5: Reglas de validación y rechazo (Odómetro, Combustible, Duplicados)
    # ------------------------------------------------------------------------
    print("\n[TEST 5] Verificando validaciones de negocio e integridad...")

    # A. Rechazo por odómetro menor a la salida
    ret_bad_km = ReturnInspection(
        id_contrato=ctr1.id_contrato,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=24000,  # Salida fue 25,000
        combustible_retorno=Decimal("1.00"),
    )
    try:
        return_service.validate_return_rules(ctr1, ret_bad_km)
        assert False, "Debió rechazar odómetro de retorno menor al de salida."
    except BusinessRuleViolationError as e:
        assert e.code == "INVALID_RETURN_ODOMETER"
        print(f" -> PASO: Odómetro inconsistente rechazado: '{e.message}'")

    # B. Rechazo por nivel de combustible fuera de rango (0.00 - 1.00)
    ret_bad_fuel = ReturnInspection(
        id_contrato=ctr1.id_contrato,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=26000,
        combustible_retorno=Decimal("1.50"),  # > 1.00
    )
    try:
        return_service.validate_return_rules(ctr1, ret_bad_fuel)
        assert False, "Debió rechazar nivel de combustible superior al 100%."
    except BusinessRuleViolationError as e:
        assert e.code == "INVALID_FUEL_LEVEL"
        print(f" -> PASO: Nivel de combustible fuera de rango rechazado: '{e.message}'")

    # C. Rechazo si el contrato ya fue liquidado/devuelto
    try:
        return_service.process_return_and_settlement(
            id_contrato=ctr1.id_contrato,
            return_data=ret1,
        )
        assert False, "Debió rechazar devolución de un contrato ya liquidado."
    except BusinessRuleViolationError as e:
        assert e.code == "CONTRACT_ALREADY_RETURNED"
        print(f" -> PASO: Reintento de devolución en contrato liquidado bloqueado: '{e.message}'")

    # Limpieza final
    cleanup_test_returns_data(test_cedulas, test_placas)

    print("\n" + "=" * 75)
    print("¡TODAS LAS PRUEBAS DE DEVOLUCIONES Y LIQUIDACIÓN PASARON SATISFACTORIAMENTE! [100%]")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_tests()
