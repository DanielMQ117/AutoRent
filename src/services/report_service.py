"""Servicio de lógica de negocio para Reportes, Estadísticas y Analítica (BLL)."""

import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.core.exceptions import ValidationError
from src.core.logger import get_logger
from src.core.session import session
from src.domain.models import (
    ClientHistorySummary,
    FinancialReportSummary,
    FleetUtilizationSummary,
)
from src.repositories.report_repository import ReportRepository
from src.services.base_service import BaseService

logger = get_logger(__name__)


class ReportService(BaseService):
    """Orquesta la consolidación de indicadores analíticos y exportación a formatos estándar (Fase 9)."""

    def __init__(self, report_repo: Optional[ReportRepository] = None) -> None:
        super().__init__()
        self.report_repo = report_repo or ReportRepository()

    # ------------------------------------------------------------------------
    # RF-34: Reporte Consolidado de Ingresos Financieros y Recaudación
    # ------------------------------------------------------------------------

    def get_financial_report(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        metodo_pago: Optional[str] = None,
        concepto: Optional[str] = None,
    ) -> FinancialReportSummary:
        """Consolida las transacciones y KPIs de facturación e ingresos en el rango temporal."""
        hoy = date.today()
        f_fin = fecha_fin or hoy
        f_ini = fecha_inicio or (f_fin.replace(day=1) if f_fin.day > 1 else f_fin - timedelta(days=30))

        if f_fin < f_ini:
            raise ValidationError(
                f"La fecha de fin ({f_fin}) no puede ser anterior a la fecha de inicio ({f_ini}).",
                code="INVALID_DATE_RANGE",
            )

        logger.info("Generando reporte financiero del %s al %s (Pago: %s, Concepto: %s)", f_ini, f_fin, metodo_pago, concepto)
        return self.report_repo.get_financial_report(
            fecha_inicio=f_ini,
            fecha_fin=f_fin,
            metodo_pago=metodo_pago,
            concepto=concepto,
        )

    # ------------------------------------------------------------------------
    # RF-35: Reporte de Utilización, Tasa de Ocupación y Rendimiento de Flota
    # ------------------------------------------------------------------------

    def get_fleet_utilization_report(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        id_categoria: Optional[int] = None,
        search: Optional[str] = None,
    ) -> FleetUtilizationSummary:
        """Calcula los indicadores de demanda, tasa de ocupación de flota e ingresos por vehículo."""
        hoy = date.today()
        f_fin = fecha_fin or hoy
        f_ini = fecha_inicio or (f_fin - timedelta(days=30))

        if f_fin < f_ini:
            raise ValidationError(
                f"La fecha de fin ({f_fin}) no puede ser anterior a la fecha de inicio ({f_ini}).",
                code="INVALID_DATE_RANGE",
            )

        logger.info("Generando reporte de ocupación de flota del %s al %s", f_ini, f_fin)
        return self.report_repo.get_fleet_utilization_report(
            fecha_inicio=f_ini,
            fecha_fin=f_fin,
            id_categoria=id_categoria,
            search=search,
        )

    # ------------------------------------------------------------------------
    # RF-36: Reporte de Historial de Clientes, Siniestralidad y Morosidad
    # ------------------------------------------------------------------------

    def get_client_history_report(
        self,
        filtro_criterio: str = "TODOS",
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        search: Optional[str] = None,
    ) -> ClientHistorySummary:
        """Segmenta y evalúa el riesgo y comportamiento histórico de los clientes arrendatarios."""
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationError(
                f"La fecha de fin ({fecha_fin}) no puede ser anterior a la fecha de inicio ({fecha_inicio}).",
                code="INVALID_DATE_RANGE",
            )

        logger.info("Generando reporte de clientes con criterio '%s'", filtro_criterio)
        return self.report_repo.get_client_history_report(
            filtro_criterio=filtro_criterio,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            search=search,
        )

    # ------------------------------------------------------------------------
    # RF-37: Exportación de Reportes a Formatos Estándar (CSV / HTML / PDF)
    # ------------------------------------------------------------------------

    def export_to_csv(
        self,
        filepath: str,
        headers: List[str],
        rows: List[List[Any]],
        title: str = "",
    ) -> None:
        """Exporta una estructura de datos tabular a un archivo CSV estándar con codificación UTF-8-BOM."""
        if not filepath.lower().endswith(".csv"):
            filepath += ".csv"

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                if title:
                    writer.writerow([f"AutoRent Pro — {title}"])
                    writer.writerow([f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
                    writer.writerow([])
                writer.writerow(headers)
                for r in rows:
                    writer.writerow([str(val) if val is not None else "" for val in r])

            logger.info("Reporte exportado exitosamente a CSV: %s (%d filas)", filepath, len(rows))
        except Exception as e:
            logger.exception("Error al exportar reporte a CSV en '%s'", filepath)
            raise ValidationError(f"No se pudo guardar el archivo CSV: {str(e)}", code="EXPORT_CSV_ERROR")

    def export_to_html(
        self,
        filepath: str,
        title: str,
        headers: List[str],
        rows: List[List[Any]],
        kpis: Optional[Dict[str, str]] = None,
        subtitle: str = "",
    ) -> None:
        """Genera un informe visual estructurado en HTML con diseño profesional listo para impresión o PDF."""
        if not filepath.lower().endswith(".html"):
            filepath += ".html"

        user_name = session.current_user.nombre_completo if session.current_user else "Administración"
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Tarjetas de KPIs en HTML
        kpi_cards_html = ""
        if kpis:
            kpi_cards_html = '<div class="kpi-grid">'
            for kpi_title, kpi_val in kpis.items():
                kpi_cards_html += f"""
                    <div class="kpi-card">
                        <div class="kpi-title">{kpi_title}</div>
                        <div class="kpi-val">{kpi_val}</div>
                    </div>
                """
            kpi_cards_html += "</div>"

        # Filas de tabla
        table_rows_html = ""
        for r in rows:
            table_rows_html += "<tr>"
            for c in r:
                c_str = str(c) if c is not None else "—"
                is_numeric = any(symbol in c_str for symbol in ("$", "%")) or c_str.replace(".", "", 1).isdigit()
                align = ' style="text-align: right;"' if is_numeric else ""
                table_rows_html += f"<td{align}>{c_str}</td>"
            table_rows_html += "</tr>\n"

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>AutoRent Pro — {title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            margin: 0;
            padding: 30px;
        }}
        .header {{
            border-bottom: 2px solid #0284c7;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .brand {{
            font-size: 22px;
            font-weight: bold;
            color: #0284c7;
            letter-spacing: 0.5px;
        }}
        .report-title {{
            font-size: 18px;
            font-weight: bold;
            color: #1e293b;
            margin-top: 5px;
        }}
        .report-meta {{
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }}
        .kpi-grid {{
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }}
        .kpi-card {{
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 18px;
            min-width: 140px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .kpi-title {{
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
            color: #64748b;
        }}
        .kpi-val {{
            font-size: 18px;
            font-weight: bold;
            color: #0284c7;
            margin-top: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            overflow: hidden;
            font-size: 12px;
        }}
        th {{
            background-color: #0f172a;
            color: #f8fafc;
            font-weight: bold;
            text-align: left;
            padding: 10px 12px;
        }}
        td {{
            padding: 9px 12px;
            border-bottom: 1px solid #f1f5f9;
        }}
        tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        .footer {{
            margin-top: 30px;
            border-top: 1px solid #e2e8f0;
            padding-top: 10px;
            font-size: 11px;
            color: #94a3b8;
            text-align: center;
        }}
        @media print {{
            body {{
                padding: 15px;
                background-color: #ffffff;
            }}
            .kpi-card {{
                box-shadow: none;
                border: 1px solid #cbd5e1;
            }}
            table {{
                font-size: 11px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">AutoRent Pro — Sistema de Gestión de Alquiler de Automóviles</div>
        <div class="report-title">{title}</div>
        <div class="report-meta">{subtitle} | Emitido: {fecha_str} | Responsable: {user_name}</div>
    </div>

    {kpi_cards_html}

    <table>
        <thead>
            <tr>
                {"".join(f"<th>{h}</th>" for h in headers)}
            </tr>
        </thead>
        <tbody>
            {table_rows_html}
        </tbody>
    </table>

    <div class="footer">
        Documento confidencial emitido por AutoRent Pro. Información sujeta a auditoría contable y operativa.
    </div>
</body>
</html>
"""
        try:
            with open(filepath, mode="w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("Reporte exportado exitosamente a HTML: %s", filepath)
        except Exception as e:
            logger.exception("Error al exportar reporte a HTML en '%s'", filepath)
            raise ValidationError(f"No se pudo guardar el archivo HTML: {str(e)}", code="EXPORT_HTML_ERROR")


# Instancia singleton para uso en controladores y vistas
report_service = ReportService()
