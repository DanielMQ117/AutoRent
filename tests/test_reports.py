"""Pruebas automatizadas de integración para el Centro de Reportes y Analítica (Fase 9)."""

from datetime import date, datetime, timedelta
from decimal import Decimal
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.core.exceptions import ValidationError
from src.core.logger import setup_logging
from src.services.report_service import report_service
from src.services.vehicle_service import vehicle_service


def run_tests() -> None:
    """Ejecuta el conjunto de pruebas unitarias y de integración para Reportes y Analítica (Fase 9)."""
    setup_logging()
    print("\n" + "=" * 70)
    print("INICIANDO SUITE DE PRUEBAS: FASE 9 - REPORTES, ESTADÍSTICAS Y ANALÍTICA")
    print("=" * 70)

    try:
        # ---------------------------------------------------------------------
        # TEST 1: RF-34 - Reporte Consolidado de Ingresos Financieros y Recaudación
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Reporte Consolidado de Ingresos Financieros y Recaudación (RF-34)...")
        f_ini = date.today() - timedelta(days=90)
        f_fin = date.today() + timedelta(days=30)

        summary_fin = report_service.get_financial_report(fecha_inicio=f_ini, fecha_fin=f_fin)

        assert summary_fin.total_facturado >= Decimal("0.00"), "El total facturado debe ser mayor o igual a 0."
        assert summary_fin.ingreso_neto is not None, "El ingreso neto debe calcularse."
        assert summary_fin.total_transacciones >= 0, "Las transacciones deben contarse."
        print(f" -> Total facturado detectado: ${summary_fin.total_facturado:,.2f} ({summary_fin.total_transacciones} trx)")
        print(f" -> Ingreso neto consolidado: ${summary_fin.ingreso_neto:,.2f}")

        # Filtro por método de pago
        summary_tarjeta = report_service.get_financial_report(
            fecha_inicio=f_ini,
            fecha_fin=f_fin,
            metodo_pago="TARJETA_CREDITO",
        )
        for item in summary_tarjeta.items:
            assert item.metodo_pago == "TARJETA_CREDITO", "Todos los ítems deben ser con Tarjeta de Crédito."

        # Validación de rango de fechas inválido
        try:
            report_service.get_financial_report(fecha_inicio=f_fin, fecha_fin=f_ini)
            assert False, "Debe rechazar un rango donde fecha_fin < fecha_inicio."
        except ValidationError as ex:
            assert ex.code == "INVALID_DATE_RANGE"
            print(f"✓ Validación de fechas inversas confirmada: {ex.code}")

        print("✓ TEST 1 PASÓ: Reporte de ingresos financieros y recaudación validado.")

        # ---------------------------------------------------------------------
        # TEST 2: RF-35 - Reporte de Utilización y Tasa de Ocupación de Flota
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Reporte de Rendimiento y Ocupación de Flota (RF-35)...")
        summary_fleet = report_service.get_fleet_utilization_report(
            fecha_inicio=f_ini,
            fecha_fin=f_fin,
        )

        assert summary_fleet.total_vehiculos > 0, "Debe haber vehículos analizados en la flota."
        assert summary_fleet.dias_periodo > 0, "Los días del periodo deben ser mayores a 0."
        assert 0.0 <= summary_fleet.tasa_ocupacion_promedio <= 100.0, "La tasa de ocupación debe estar entre 0% y 100%."
        assert len(summary_fleet.items) == summary_fleet.total_vehiculos

        for v_item in summary_fleet.items:
            assert v_item.placa, "Cada vehículo debe tener placa identificadora."
            assert 0.0 <= v_item.tasa_ocupacion_pct <= 100.0, "La tasa unitaria debe ser válida."
            assert v_item.dias_alquilado >= 0, "Días alquilados no pueden ser negativos."
            assert v_item.dias_taller >= 0, "Días en taller no pueden ser negativos."

        print(f" -> Vehículos en flota evaluados: {summary_fleet.total_vehiculos}")
        print(f" -> Tasa de ocupación promedio calculada: {summary_fleet.tasa_ocupacion_promedio:.1f}%")
        print(f" -> Vehículo más rentado detectado: {summary_fleet.vehiculo_mas_rentado}")

        # Filtro por categoría
        categories = vehicle_service.get_categories()
        if categories:
            cat_test = categories[0]
            summary_cat = report_service.get_fleet_utilization_report(
                fecha_inicio=f_ini,
                fecha_fin=f_fin,
                id_categoria=cat_test.id_categoria,
            )
            for v_cat in summary_cat.items:
                assert v_cat.categoria == cat_test.nombre

        print("✓ TEST 2 PASÓ: Reporte de rendimiento de flota y tasa de ocupación validado.")

        # ---------------------------------------------------------------------
        # TEST 3: RF-36 - Reporte de Historial de Clientes y Siniestralidad
        # ---------------------------------------------------------------------
        print("\n[TEST 3] Reporte de Historial de Clientes y Siniestralidad (RF-36)...")
        summary_clients = report_service.get_client_history_report(filtro_criterio="TODOS")

        assert summary_clients.total_clientes_analizados > 0, "Debe haber clientes analizados."
        print(f" -> Total clientes analizados: {summary_clients.total_clientes_analizados}")
        print(f" -> Clientes frecuentes: {summary_clients.clientes_frecuentes}")
        print(f" -> Clientes con siniestros: {summary_clients.clientes_con_siniestros}")
        print(f" -> Clientes de alto riesgo: {summary_clients.clientes_alto_riesgo}")

        for cli_item in summary_clients.items:
            assert cli_item.identificacion, "Debe tener identificación registrada."
            assert cli_item.total_contratos >= 0, "Contratos no pueden ser negativos."
            assert cli_item.total_gastado >= Decimal("0.00"), "Gasto no puede ser negativo."
            assert cli_item.nivel_riesgo in ("BAJO", "MEDIO", "ALTO"), "Nivel de riesgo debe ser válido."

        # Filtro por segmento frecuentes
        summary_frec = report_service.get_client_history_report(filtro_criterio="FRECUENTES")
        for c_frec in summary_frec.items:
            assert c_frec.total_contratos >= 2, "Un cliente frecuente debe tener al menos 2 contratos."

        # Filtro por siniestros
        summary_sin = report_service.get_client_history_report(filtro_criterio="CON_SINIESTROS")
        for c_sin in summary_sin.items:
            assert c_sin.total_danos_reportados > 0, "Debe tener al menos un daño reportado."

        print("✓ TEST 3 PASÓ: Clasificación de clientes y evaluación de siniestralidad validada.")

        # ---------------------------------------------------------------------
        # TEST 4: RF-37 - Exportación a Formatos Estándar (CSV y HTML/PDF)
        # ---------------------------------------------------------------------
        print("\n[TEST 4] Exportación de Reportes a CSV y HTML (RF-37)...")
        scratch_dir = ROOT_DIR / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)

        csv_path = str(scratch_dir / "test_report_fin.csv")
        html_path = str(scratch_dir / "test_report_fleet.html")

        # 4a. Exportar CSV
        headers_csv = ["ID", "Transacción", "Fecha", "Monto", "Concepto"]
        rows_csv = [
            ["1", "TRX-001", "2026-09-01", "$150.00", "Alquiler"],
            ["2", "TRX-002", "2026-09-02", "$200.00", "Fianza"],
        ]
        report_service.export_to_csv(csv_path, headers_csv, rows_csv, title="Prueba de Exportación Financiera")
        assert os.path.exists(csv_path), "El archivo CSV debe haberse creado."
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            content_csv = f.read()
            assert "TRX-001" in content_csv
            assert "Prueba de Exportación Financiera" in content_csv
        print("✓ Archivo CSV exportado y verificado con éxito.")

        # 4b. Exportar HTML
        headers_html = ["Placa", "Modelo", "Ocupación", "Ingresos"]
        rows_html = [
            ["M-312450", "Toyota Corolla", "85.0%", "$850.00"],
            ["M-198765", "Hyundai Tucson", "60.0%", "$600.00"],
        ]
        kpis_html = {"Ocupación Global": "72.5%", "Ingresos Totales": "$1,450.00"}
        report_service.export_to_html(
            html_path,
            title="Reporte de Rendimiento de Flota",
            headers=headers_html,
            rows=rows_html,
            kpis=kpis_html,
            subtitle="Periodo de Evaluación 2026",
        )
        assert os.path.exists(html_path), "El archivo HTML debe haberse creado."
        with open(html_path, "r", encoding="utf-8") as f:
            content_html = f.read()
            assert "<!DOCTYPE html>" in content_html
            assert "Toyota Corolla" in content_html
            assert "72.5%" in content_html
        print("✓ Archivo HTML con formato imprimible generado y verificado.")

        # Limpiar archivos de prueba temporales
        if os.path.exists(csv_path):
            os.remove(csv_path)
        if os.path.exists(html_path):
            os.remove(html_path)

        print("✓ TEST 4 PASÓ: Motores de exportación CSV y HTML operando correctamente.")

    finally:
        print("\nPruebas analíticas concluidas.")

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE FASE 9 (REPORTES Y ANALÍTICA) PASARON AL 100%!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
