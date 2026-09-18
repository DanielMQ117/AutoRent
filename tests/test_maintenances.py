"""Pruebas automatizadas de integración para el Motor de Mantenimiento de Flota y Taller Mecánico (Fase 8)."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    MaintenanceStatus,
    MaintenanceType,
    VehicleStatus,
)
from src.domain.models import (
    Client,
    Contract,
    DriverLicense,
    Maintenance,
    Vehicle,
)
from src.services.client_service import client_service
from src.services.contract_service import contract_service
from src.services.maintenance_service import maintenance_service
from src.services.vehicle_service import vehicle_service


def cleanup_test_maintenances_data(placas: list[str]) -> None:
    """Elimina los registros creados durante las pruebas de mantenimiento."""
    try:
        for placa in placas:
            v = vehicle_service.vehicle_repo.get_by_placa(placa)
            if v and v.id_vehiculo:
                # 1. Eliminar mantenimientos vinculados
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM mantenimientos WHERE id_vehiculo = %s",
                    (v.id_vehiculo,),
                )
                # 2. Pagos, liquidaciones, devoluciones, contratos
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM pagos WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM liquidaciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM danios WHERE id_devolucion IN (SELECT id_devolucion FROM devoluciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s))",
                    (v.id_vehiculo,),
                )
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM devoluciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM conductores_adicionales WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo = %s)",
                    (v.id_vehiculo,),
                )
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM contratos WHERE id_vehiculo = %s",
                    (v.id_vehiculo,),
                )
                maintenance_service.maintenance_repo.execute_non_query(
                    "DELETE FROM reservas WHERE id_vehiculo = %s",
                    (v.id_vehiculo,),
                )
                # 3. Eliminar vehículo
                vehicle_service.vehicle_repo.delete(v.id_vehiculo)
    except Exception as ex:
        print(f"Advertencia en cleanup de mantenimientos: {ex}")


def create_test_vehicle(placa: str, vin: str, km: int = 15000, km_next: int = 20000) -> Vehicle:
    """Crea un vehículo de prueba en la base de datos."""
    models = vehicle_service.get_models()
    categories = vehicle_service.get_categories()
    v = Vehicle(
        id_modelo=models[0].id_modelo if models else 1,
        id_categoria=categories[0].id_categoria if categories else 1,
        placa=placa,
        vin=vin,
        color="Plateado Taller",
        kilometraje_actual=km,
        nivel_combustible_actual=Decimal("1.00"),
        estado=VehicleStatus.DISPONIBLE,
        km_proximo_mantenimiento=km_next,
        activo=True,
    )
    return vehicle_service.create_vehicle(v)


def run_tests() -> None:
    """Ejecuta el conjunto completo de pruebas unitarias y de integración para Mantenimientos."""
    setup_logging()
    print("\n" + "=" * 70)
    print("INICIANDO SUITE DE PRUEBAS: FASE 8 - MANTENIMIENTO DE FLOTA Y TALLER")
    print("=" * 70)

    test_placas = ["MNT-001", "MNT-002", "MNT-003", "MNT-004"]
    cleanup_test_maintenances_data(test_placas)

    try:
        # ---------------------------------------------------------------------
        # TEST 1: RF-31 - Registro de Orden Preventiva y Bloqueo a EN_MANTENIMIENTO
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Registro de Orden Preventiva y Bloqueo Operativo (RF-31, RF-32)...")
        v1 = create_test_vehicle("MNT-001", "VINMNT001TEST0001", km=20500, km_next=20000)

        orden_prev = Maintenance(
            id_vehiculo=v1.id_vehiculo,
            tipo_mantenimiento=MaintenanceType.PREVENTIVO,
            fecha_ingreso=datetime.now() - timedelta(hours=2),
            fecha_salida_estimada=date.today() + timedelta(days=2),
            kilometraje_entrada=20550,
            taller_servicio="Taller Central AutoRent",
            descripcion_trabajo="Mantenimiento preventivo general: cambio de aceite 5W-30, filtro aire y bujías.",
            costo_total=Decimal("180.00"),
        )
        created_order = maintenance_service.create_maintenance_order(orden_prev)

        assert created_order.id_mantenimiento is not None, "El ID de mantenimiento debe generarse."
        assert created_order.estado == MaintenanceStatus.EN_TALLER, "El estado de la orden debe ser EN_TALLER."
        assert created_order.tipo_mantenimiento == MaintenanceType.PREVENTIVO

        # Verificar bloqueo en el vehículo (RF-32)
        v1_updated = vehicle_service.get_vehicle(v1.id_vehiculo)
        assert v1_updated.estado == VehicleStatus.EN_MANTENIMIENTO, "El vehículo debe estar bloqueado en EN_MANTENIMIENTO."
        print("✓ TEST 1 PASÓ: Orden preventiva creada con éxito y vehículo bloqueado en taller.")

        # ---------------------------------------------------------------------
        # TEST 2: RF-32 - Validación de Bloqueo Operativo (Imposible Alquilar o Duplicar)
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Verificación de Bloqueos Operativos (RF-32)...")

        # 2a. Intento de cambiar estado directamente a ALQUILADO sin pasar por DISPONIBLE
        try:
            vehicle_service.change_status(v1.id_vehiculo, VehicleStatus.ALQUILADO)
            assert False, "No debe permitirse cambiar un vehículo en taller a ALQUILADO directamente."
        except InvalidStateTransitionError as ex:
            print(f"✓ Bloqueo confirmado por transición inválida: {ex.code}")

        # 2b. Intento de crear segunda orden en taller simultánea para el mismo vehículo
        try:
            orden_duplicada = Maintenance(
                id_vehiculo=v1.id_vehiculo,
                tipo_mantenimiento=MaintenanceType.CORRECTIVO,
                kilometraje_entrada=20550,
                taller_servicio="Otro Taller",
                descripcion_trabajo="Reparación duplicada no permitida",
            )
            maintenance_service.create_maintenance_order(orden_duplicada)
            assert False, "No debe permitirse abrir dos órdenes de taller activas al mismo vehículo."
        except BusinessRuleViolationError as ex:
            assert ex.code == "MAINTENANCE_ALREADY_ACTIVE"
            print(f"✓ Bloqueo confirmado contra órdenes duplicadas: {ex.code}")

        # 2c. Intento de odómetro con retroceso
        v2 = create_test_vehicle("MNT-002", "VINMNT002TEST0002", km=50000, km_next=55000)
        try:
            orden_km_invalido = Maintenance(
                id_vehiculo=v2.id_vehiculo,
                tipo_mantenimiento=MaintenanceType.CORRECTIVO,
                kilometraje_entrada=49000,  # Menor a 50,000 km
                taller_servicio="Taller Ruedas",
                descripcion_trabajo="Revisión de suspensión",
            )
            maintenance_service.create_maintenance_order(orden_km_invalido)
            assert False, "Debe rechazar odómetro de entrada inferior al actual del vehículo."
        except ValidationError as ex:
            assert ex.code == "ODOMETER_ROLLBACK_ATTEMPT"
            print(f"✓ Bloqueo confirmado contra retroceso de odómetro: {ex.code}")

        print("✓ TEST 2 PASÓ: Todos los bloqueos operativos de taller están activos y validados.")

        # ---------------------------------------------------------------------
        # TEST 3: RF-33 - Finalización de Mantenimiento, Costos y Reactivación
        # ---------------------------------------------------------------------
        print("\n[TEST 3] Finalización de Mantenimiento y Reactivación (RF-33)...")

        # Completar la orden preventiva de v1
        fecha_salida = datetime.now()
        costo_final = Decimal("215.50")
        nuevo_km_maint = 30000

        completed_order = maintenance_service.complete_maintenance(
            id_mantenimiento=created_order.id_mantenimiento,
            fecha_salida_real=fecha_salida,
            costo_total=costo_final,
            nuevo_km_proximo_mantenimiento=nuevo_km_maint,
            notas_cierre="Cambio de pastillas traseras adicionales. Prueba de ruta exitosa.",
        )

        assert completed_order.estado == MaintenanceStatus.FINALIZADO, "La orden debe estar FINALIZADO."
        assert completed_order.costo_total == costo_final, "El costo total final debe ser 215.50."
        assert completed_order.fecha_salida_real is not None, "La fecha real debe estar registrada."
        assert "pastillas traseras" in completed_order.descripcion_trabajo

        # Verificar vehículo reactivado a DISPONIBLE y con nuevo próximo mantenimiento
        v1_liberado = vehicle_service.get_vehicle(v1.id_vehiculo)
        assert v1_liberado.estado == VehicleStatus.DISPONIBLE, "El vehículo debe reactivarse a DISPONIBLE."
        assert v1_liberado.km_proximo_mantenimiento == nuevo_km_maint, "El km de próximo mantenimiento debe ser 30,000."
        print(f"✓ TEST 3 PASÓ: Orden #{completed_order.id_mantenimiento} finalizada, vehículo reactivado a DISPONIBLE.")

        # ---------------------------------------------------------------------
        # TEST 4: Mantenimiento Correctivo y Cancelación
        # ---------------------------------------------------------------------
        print("\n[TEST 4] Mantenimiento Correctivo y Cancelación de Orden...")
        v3 = create_test_vehicle("MNT-003", "VINMNT003TEST0003", km=12000, km_next=15000)

        orden_corr = Maintenance(
            id_vehiculo=v3.id_vehiculo,
            tipo_mantenimiento=MaintenanceType.CORRECTIVO,
            kilometraje_entrada=12100,
            taller_servicio="ElectroAuto",
            descripcion_trabajo="Falla intermitente en alternador y sistema de encendido.",
            costo_total=Decimal("95.00"),
        )
        created_corr = maintenance_service.create_maintenance_order(orden_corr)
        assert created_corr.estado == MaintenanceStatus.EN_TALLER
        assert vehicle_service.get_vehicle(v3.id_vehiculo).estado == VehicleStatus.EN_MANTENIMIENTO

        # Cancelar la orden
        cancelled_order = maintenance_service.cancel_maintenance(
            id_mantenimiento=created_corr.id_mantenimiento,
            motivo="Falsa alarma, solo requería cambio de fusible rápido en garaje.",
        )
        assert cancelled_order.estado == MaintenanceStatus.CANCELADO
        assert "Falsa alarma" in cancelled_order.descripcion_trabajo

        # Vehículo liberado a DISPONIBLE
        v3_liberado = vehicle_service.get_vehicle(v3.id_vehiculo)
        assert v3_liberado.estado == VehicleStatus.DISPONIBLE, "Vehículo debe restaurarse a DISPONIBLE tras cancelar orden."
        print("✓ TEST 4 PASÓ: Cancelación de orden ejecutada correctamente y vehículo liberado.")

        # ---------------------------------------------------------------------
        # TEST 5: Validaciones de Reglas de Negocio en Finalización
        # ---------------------------------------------------------------------
        print("\n[TEST 5] Validaciones de Negocio en Finalización...")

        # 5a. Intento de finalizar una orden ya cancelada
        try:
            maintenance_service.complete_maintenance(cancelled_order.id_mantenimiento)
            assert False, "No debe permitirse finalizar una orden cancelada."
        except InvalidStateTransitionError as ex:
            assert ex.code == "MAINTENANCE_NOT_IN_WORKSHOP"
            print(f"✓ Rechazo de orden no activa confirmado: {ex.code}")

        # 5b. Intento de reprogramar km de servicio menor o igual al actual
        v4 = create_test_vehicle("MNT-004", "VINMNT004TEST0004", km=40000, km_next=45000)
        orden_v4 = Maintenance(
            id_vehiculo=v4.id_vehiculo,
            tipo_mantenimiento=MaintenanceType.PREVENTIVO,
            kilometraje_entrada=40000,
            taller_servicio="Taller Diesel",
            descripcion_trabajo="Servicio 40,000 km",
        )
        m4 = maintenance_service.create_maintenance_order(orden_v4)

        try:
            maintenance_service.complete_maintenance(
                id_mantenimiento=m4.id_mantenimiento,
                nuevo_km_proximo_mantenimiento=35000,  # Menor a 40,000
            )
            assert False, "No debe permitirse próximo mantenimiento inferior al odómetro actual."
        except ValidationError as ex:
            assert ex.code == "INVALID_NEXT_MAINTENANCE_KM"
            print(f"✓ Validación de próximo km confirmada: {ex.code}")

        # Finalizar correctamente v4
        maintenance_service.complete_maintenance(m4.id_mantenimiento)
        assert vehicle_service.get_vehicle(v4.id_vehiculo).estado == VehicleStatus.DISPONIBLE
        print("✓ TEST 5 PASÓ: Todas las validaciones de finalización aprobadas.")

        # ---------------------------------------------------------------------
        # TEST 6: KPIs y Consultas de Catálogo de Taller
        # ---------------------------------------------------------------------
        print("\n[TEST 6] Verificación de KPIs y Métodos de Consulta...")
        kpis = maintenance_service.get_maintenance_kpis()
        assert kpis["total_ordenes"] >= 3, "Debe haber al menos 3 órdenes registradas."
        assert kpis["finalizadas"] >= 2, "Debe haber al menos 2 órdenes finalizadas."
        assert kpis["gasto_total"] > Decimal("0.00"), "El gasto total debe ser mayor a 0."

        # Listado con filtros
        en_taller = maintenance_service.list_maintenances(status=MaintenanceStatus.EN_TALLER.value)
        finalizadas = maintenance_service.list_maintenances(status=MaintenanceStatus.FINALIZADO.value)
        assert all(m.estado == MaintenanceStatus.FINALIZADO for m in finalizadas)

        # Vehículos elegibles
        elegibles = maintenance_service.get_eligible_vehicles_for_maintenance()
        assert all(v.estado not in (VehicleStatus.ALQUILADO, VehicleStatus.DE_BAJA) for v in elegibles)

        print("✓ TEST 6 PASÓ: KPIs, consultas y filtros funcionando con precisión.")

    finally:
        print("\nLimpiando datos de prueba de Mantenimientos...")
        cleanup_test_maintenances_data(test_placas)
        print("✓ Limpieza completada.")

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE FASE 8 (MANTENIMIENTO DE FLOTA) PASARON AL 100%!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
