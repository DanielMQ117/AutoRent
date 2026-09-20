"""Vista principal para el Centro de Reportes, Estadísticas y Analítica de Negocio (Fase 9)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.models import (
    ClientHistorySummary,
    FinancialReportSummary,
    FleetUtilizationSummary,
    VehicleCategory,
)
from src.services.report_service import report_service
from src.services.vehicle_service import vehicle_service
from src.ui.components.badges import create_badge

logger = get_logger(__name__)


class ReportsView(QWidget):
    """Pantalla integral de Inteligencia de Negocios, Auditoría y Reportes Estratégicos (RF-34 a RF-37)."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._categories_cache: List[VehicleCategory] = []
        self._financial_summary: Optional[FinancialReportSummary] = None
        self._fleet_summary: Optional[FleetUtilizationSummary] = None
        self._client_summary: Optional[ClientHistorySummary] = None

        self._init_ui()
        self._load_catalogs()
        self.load_all_reports()

    def _init_ui(self) -> None:
        """Construye la interfaz visual de la vista de reportes."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(14)

        # 1. Cabecera con navegación, títulos y botones de exportación global
        header_layout = QHBoxLayout()

        self.btn_back = QPushButton("← Volver al Panel")
        self.btn_back.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #475569;
                color: #ffffff;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel("Centro de Reportes, Estadísticas y Analítica de Negocio")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #f8fafc;")

        subtitle = QLabel("Inteligencia operativa, flujos financieros, rendimiento de flota y expediente de siniestralidad.")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #94a3b8;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        # Botones de exportación (RF-37)
        self.btn_export_csv = QPushButton("📥 Exportar CSV / Excel")
        self._style_button(self.btn_export_csv, "#059669", "#047857")
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        header_layout.addWidget(self.btn_export_csv)

        self.btn_export_html = QPushButton("📄 Informe Imprimible (PDF/HTML)")
        self._style_button(self.btn_export_html, "#0284c7", "#0369a1")
        self.btn_export_html.clicked.connect(self._handle_export_html)
        header_layout.addWidget(self.btn_export_html)

        main_layout.addLayout(header_layout)

        # 2. QTabWidget para las 3 secciones estratégicas
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: #1e293b;
                border-radius: 8px;
                padding: 12px;
            }
            QTabBar::tab {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 18px;
                font-family: 'Segoe UI';
                font-size: 10pt;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e293b;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QTabBar::tab:hover:!selected {
                background-color: #1e293b;
                color: #cbd5e1;
            }
        """)

        # Pestaña 1: Ingresos Financieros y Recaudación (RF-34)
        self.tab_financial = self._create_financial_tab()
        self.tabs.addTab(self.tab_financial, "💰 Ingresos Financieros y Recaudación")

        # Pestaña 2: Ocupación y Rendimiento de Flota (RF-35)
        self.tab_fleet = self._create_fleet_tab()
        self.tabs.addTab(self.tab_fleet, "🚗 Ocupación y Rendimiento de Flota")

        # Pestaña 3: Historial de Clientes y Siniestralidad (RF-36)
        self.tab_clients = self._create_clients_tab()
        self.tabs.addTab(self.tab_clients, "👥 Historial de Clientes y Siniestralidad")

        main_layout.addWidget(self.tabs, stretch=1)

    # ------------------------------------------------------------------------
    # PESTAÑA 1: REPORTE FINANCIERO (RF-34)
    # ------------------------------------------------------------------------

    def _create_financial_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Barra de Filtros
        filter_card = self._create_card_frame()
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(8, 6, 8, 6)
        f_layout.setSpacing(10)

        f_layout.addWidget(self._bold_label("Desde:"))
        self.fin_date_from = QDateEdit()
        self.fin_date_from.setCalendarPopup(True)
        self.fin_date_from.setDate(QDate.currentDate().addDays(-30))
        self.fin_date_from.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fin_date_from)

        f_layout.addWidget(self._bold_label("Hasta:"))
        self.fin_date_to = QDateEdit()
        self.fin_date_to.setCalendarPopup(True)
        self.fin_date_to.setDate(QDate.currentDate())
        self.fin_date_to.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fin_date_to)

        f_layout.addWidget(self._bold_label("Método:"))
        self.fin_combo_metodo = QComboBox()
        self.fin_combo_metodo.addItems(["TODOS", "EFECTIVO", "TARJETA_CREDITO", "TARJETA_DEBITO", "TRANSFERENCIA"])
        self.fin_combo_metodo.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fin_combo_metodo)

        f_layout.addWidget(self._bold_label("Concepto:"))
        self.fin_combo_concepto = QComboBox()
        self.fin_combo_concepto.addItems(["TODOS", "ANTICIPO_RESERVA", "DEPOSITO_GARANTIA", "COBRO_LIQUIDACION", "REEMBOLSO_GARANTIA"])
        self.fin_combo_concepto.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fin_combo_concepto)

        btn_filter_fin = QPushButton("🔍 Filtrar")
        self._style_button(btn_filter_fin, "#0284c7", "#0369a1")
        btn_filter_fin.clicked.connect(self.load_financial_report)
        f_layout.addWidget(btn_filter_fin)

        layout.addWidget(filter_card)

        # Tarjetas de KPIs Financieros
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.kpi_fin_total = self._create_kpi_card("Facturación Total", "$0.00", "#38bdf8")
        self.kpi_fin_renta = self._create_kpi_card("Ingresos Renta", "$0.00", "#34d399")
        self.kpi_fin_penal = self._create_kpi_card("Penalizaciones", "$0.00", "#fbbf24")
        self.kpi_fin_taller = self._create_kpi_card("Gastos Taller", "$0.00", "#f87171")
        self.kpi_fin_neto = self._create_kpi_card("Ingreso Neto", "$0.00", "#c084fc")
        self.kpi_fin_ticket = self._create_kpi_card("Ticket Promedio", "$0.00", "#38bdf8")

        kpi_layout.addWidget(self.kpi_fin_total)
        kpi_layout.addWidget(self.kpi_fin_renta)
        kpi_layout.addWidget(self.kpi_fin_penal)
        kpi_layout.addWidget(self.kpi_fin_taller)
        kpi_layout.addWidget(self.kpi_fin_neto)
        kpi_layout.addWidget(self.kpi_fin_ticket)
        layout.addLayout(kpi_layout)

        # Tabla de Transacciones
        self.table_financial = self._create_styled_table([
            "Código Trx",
            "Fecha y Hora",
            "Concepto / Operación",
            "Método de Pago",
            "Monto ($)",
            "Contrato / Ref",
            "Cliente",
        ])
        self.table_financial.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table_financial.setColumnWidth(0, 120)  # Código Trx
        self.table_financial.setColumnWidth(1, 135)  # Fecha y Hora
        self.table_financial.setColumnWidth(2, 180)  # Concepto
        self.table_financial.setColumnWidth(3, 135)  # Método
        self.table_financial.setColumnWidth(4, 105)  # Monto
        self.table_financial.setColumnWidth(5, 125)  # Contrato / Ref
        layout.addWidget(self.table_financial, stretch=1)

        return widget

    # ------------------------------------------------------------------------
    # PESTAÑA 2: OCUPACIÓN Y RENDIMIENTO DE FLOTA (RF-35)
    # ------------------------------------------------------------------------

    def _create_fleet_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Filtros de Flota
        filter_card = self._create_card_frame()
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(8, 6, 8, 6)
        f_layout.setSpacing(10)

        f_layout.addWidget(self._bold_label("Desde:"))
        self.fleet_date_from = QDateEdit()
        self.fleet_date_from.setCalendarPopup(True)
        self.fleet_date_from.setDate(QDate.currentDate().addDays(-30))
        self.fleet_date_from.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fleet_date_from)

        f_layout.addWidget(self._bold_label("Hasta:"))
        self.fleet_date_to = QDateEdit()
        self.fleet_date_to.setCalendarPopup(True)
        self.fleet_date_to.setDate(QDate.currentDate())
        self.fleet_date_to.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fleet_date_to)

        f_layout.addWidget(self._bold_label("Categoría:"))
        self.fleet_combo_cat = QComboBox()
        self.fleet_combo_cat.setStyleSheet(self._input_style())
        f_layout.addWidget(self.fleet_combo_cat)

        self.fleet_search = QLineEdit()
        self.fleet_search.setPlaceholderText("🔍 Buscar por placa, marca o modelo...")
        self.fleet_search.setStyleSheet(self._input_style())
        self.fleet_search.textChanged.connect(self.load_fleet_report)
        f_layout.addWidget(self.fleet_search, stretch=1)

        btn_filter_fleet = QPushButton("🔍 Filtrar")
        self._style_button(btn_filter_fleet, "#0284c7", "#0369a1")
        btn_filter_fleet.clicked.connect(self.load_fleet_report)
        f_layout.addWidget(btn_filter_fleet)

        layout.addWidget(filter_card)

        # Tarjetas de KPIs de Flota
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.kpi_fleet_ocup = self._create_kpi_card("Tasa Ocupación Global", "0.0%", "#38bdf8")
        self.kpi_fleet_vehs = self._create_kpi_card("Total Vehículos", "0", "#cbd5e1")
        self.kpi_fleet_dias_renta = self._create_kpi_card("Días en Renta", "0 d", "#34d399")
        self.kpi_fleet_dias_taller = self._create_kpi_card("Días en Taller", "0 d", "#fbbf24")
        self.kpi_fleet_ingresos = self._create_kpi_card("Ingresos Generados", "$0.00", "#c084fc")
        self.kpi_fleet_top = self._create_kpi_card("Vehículo Más Rentado", "—", "#38bdf8")

        kpi_layout.addWidget(self.kpi_fleet_ocup)
        kpi_layout.addWidget(self.kpi_fleet_vehs)
        kpi_layout.addWidget(self.kpi_fleet_dias_renta)
        kpi_layout.addWidget(self.kpi_fleet_dias_taller)
        kpi_layout.addWidget(self.kpi_fleet_ingresos)
        kpi_layout.addWidget(self.kpi_fleet_top)
        layout.addLayout(kpi_layout)

        # Tabla de Rendimiento de Flota
        self.table_fleet = self._create_styled_table([
            "Placa",
            "Marca / Modelo",
            "Categoría",
            "Contratos",
            "Días Rentado",
            "Ocupación (%)",
            "Ingresos ($)",
            "Días Taller",
            "Gastos Taller ($)",
            "Estado Actual",
        ])
        self.table_fleet.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_fleet.setColumnWidth(0, 95)   # Placa
        self.table_fleet.setColumnWidth(2, 115)  # Categoría
        self.table_fleet.setColumnWidth(3, 85)   # Contratos
        self.table_fleet.setColumnWidth(4, 95)   # Días Rentado
        self.table_fleet.setColumnWidth(5, 105)  # Ocupación (%)
        self.table_fleet.setColumnWidth(6, 110)  # Ingresos ($)
        self.table_fleet.setColumnWidth(7, 95)   # Días Taller
        self.table_fleet.setColumnWidth(8, 120)  # Gastos Taller ($)
        self.table_fleet.setColumnWidth(9, 130)  # Estado Actual
        layout.addWidget(self.table_fleet, stretch=1)

        return widget

    # ------------------------------------------------------------------------
    # PESTAÑA 3: HISTORIAL Y SINIESTRALIDAD DE CLIENTES (RF-36)
    # ------------------------------------------------------------------------

    def _create_clients_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Filtros de Clientes
        filter_card = self._create_card_frame()
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(8, 6, 8, 6)
        f_layout.setSpacing(10)

        f_layout.addWidget(self._bold_label("Segmentación:"))
        self.client_combo_criterio = QComboBox()
        self.client_combo_criterio.addItem("TODOS (Todos los clientes)", "TODOS")
        self.client_combo_criterio.addItem("⭐ Clientes Frecuentes (≥ 2 alquileres)", "FRECUENTES")
        self.client_combo_criterio.addItem("⚠️ Con Siniestros o Daños Reportados", "CON_SINIESTROS")
        self.client_combo_criterio.addItem("⛔ Alto Riesgo / Morosos / Vetados", "RIESGO_ALTO")
        self.client_combo_criterio.setStyleSheet(self._input_style())
        self.client_combo_criterio.currentIndexChanged.connect(self.load_client_history_report)
        f_layout.addWidget(self.client_combo_criterio)

        self.client_search = QLineEdit()
        self.client_search.setPlaceholderText("🔍 Buscar por cédula, nombre o correo...")
        self.client_search.setStyleSheet(self._input_style())
        self.client_search.textChanged.connect(self.load_client_history_report)
        f_layout.addWidget(self.client_search, stretch=1)

        btn_filter_clients = QPushButton("🔍 Filtrar")
        self._style_button(btn_filter_clients, "#0284c7", "#0369a1")
        btn_filter_clients.clicked.connect(self.load_client_history_report)
        f_layout.addWidget(btn_filter_clients)

        layout.addWidget(filter_card)

        # Tarjetas de KPIs de Clientes
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.kpi_cli_total = self._create_kpi_card("Clientes Analizados", "0", "#cbd5e1")
        self.kpi_cli_frec = self._create_kpi_card("Clientes Frecuentes", "0", "#34d399")
        self.kpi_cli_siniestros = self._create_kpi_card("Con Siniestros", "0", "#fbbf24")
        self.kpi_cli_riesgo = self._create_kpi_card("Alto Riesgo", "0", "#f87171")

        kpi_layout.addWidget(self.kpi_cli_total)
        kpi_layout.addWidget(self.kpi_cli_frec)
        kpi_layout.addWidget(self.kpi_cli_siniestros)
        kpi_layout.addWidget(self.kpi_cli_riesgo)
        layout.addLayout(kpi_layout)

        # Tabla de Expedientes de Clientes
        self.table_clients = self._create_styled_table([
            "Identificación",
            "Nombre Completo",
            "Teléfono",
            "Estado Cliente",
            "Contratos",
            "Total Desembolsado ($)",
            "Días Rentados",
            "Daños Reportados",
            "Penalizaciones ($)",
            "Nivel de Riesgo",
        ])
        self.table_clients.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_clients.setColumnWidth(0, 120)  # Identificación
        self.table_clients.setColumnWidth(2, 115)  # Teléfono
        self.table_clients.setColumnWidth(3, 120)  # Estado Cliente
        self.table_clients.setColumnWidth(4, 85)   # Contratos
        self.table_clients.setColumnWidth(5, 145)  # Total Desembolsado ($)
        self.table_clients.setColumnWidth(6, 105)  # Días Rentados
        self.table_clients.setColumnWidth(7, 125)  # Daños Reportados
        self.table_clients.setColumnWidth(8, 125)  # Penalizaciones ($)
        self.table_clients.setColumnWidth(9, 140)  # Nivel de Riesgo
        layout.addWidget(self.table_clients, stretch=1)

        return widget

    # ------------------------------------------------------------------------
    # COMPONENTES VISUALES AUXILIARES
    # ------------------------------------------------------------------------

    def _create_card_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        return frame

    def _bold_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        return lbl

    def _input_style(self) -> str:
        return """
            QLineEdit, QComboBox, QDateEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #38bdf8;
            }
        """

    def _style_button(self, btn: QPushButton, bg: str, hover: str) -> None:
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

    def _create_kpi_card(self, title: str, initial_value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        vbox = QVBoxLayout(card)
        vbox.setSpacing(2)
        vbox.setContentsMargins(6, 4, 6, 4)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        lbl_title.setStyleSheet("color: #94a3b8; text-transform: uppercase;")

        lbl_val = QLabel(initial_value)
        lbl_val.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_hex};")
        lbl_val.setObjectName("kpi_value")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        return card

    def _update_kpi_card_value(self, card: QFrame, value_text: str) -> None:
        lbl = card.findChild(QLabel, "kpi_value")
        if lbl:
            lbl.setText(value_text)

    def _create_styled_table(self, headers: List[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                color: #f8fafc;
                selection-background-color: #243247;
                selection-color: #38bdf8;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px;
                border: 1px solid #334155;
                font-size: 9pt;
                font-weight: bold;
            }
        """)
        return table

    # ------------------------------------------------------------------------
    # CARGA DE DATOS Y REPORTEADOR
    # ------------------------------------------------------------------------

    def _load_catalogs(self) -> None:
        """Carga las categorías de vehículo en el combo de filtros de flota."""
        try:
            self._categories_cache = vehicle_service.get_categories()
            self.fleet_combo_cat.clear()
            self.fleet_combo_cat.addItem("TODAS", 0)
            for c in self._categories_cache:
                self.fleet_combo_cat.addItem(c.nombre, c.id_categoria)
        except Exception as e:
            logger.warning("No se pudieron cargar categorías en reportes: %s", e)

    def load_all_reports(self) -> None:
        """Actualiza todas las pestañas de reportes."""
        self.load_financial_report()
        self.load_fleet_report()
        self.load_client_history_report()

    def load_financial_report(self) -> None:
        """Ejecuta y presenta el reporte de ingresos y recaudación (RF-34)."""
        f_ini = self.fin_date_from.date().toPython()
        f_fin = self.fin_date_to.date().toPython()
        metodo = self.fin_combo_metodo.currentText()
        concepto = self.fin_combo_concepto.currentText()

        try:
            self._financial_summary = report_service.get_financial_report(
                fecha_inicio=f_ini,
                fecha_fin=f_fin,
                metodo_pago=metodo if metodo != "TODOS" else None,
                concepto=concepto if concepto != "TODOS" else None,
            )

            # Actualizar KPIs
            s = self._financial_summary
            self._update_kpi_card_value(self.kpi_fin_total, f"${s.total_facturado:,.2f}")
            self._update_kpi_card_value(self.kpi_fin_renta, f"${s.ingresos_renta:,.2f}")
            self._update_kpi_card_value(self.kpi_fin_penal, f"${s.ingresos_penalizaciones:,.2f}")
            self._update_kpi_card_value(self.kpi_fin_taller, f"${s.gastos_mantenimiento:,.2f}")
            self._update_kpi_card_value(self.kpi_fin_neto, f"${s.ingreso_neto:,.2f}")
            self._update_kpi_card_value(self.kpi_fin_ticket, f"${s.ticket_promedio:,.2f}")

            # Poblar tabla
            self.table_financial.setRowCount(0)
            for item in s.items:
                row = self.table_financial.rowCount()
                self.table_financial.insertRow(row)

                self.table_financial.setItem(row, 0, QTableWidgetItem(item.codigo_transaccion))

                f_str = item.fecha_hora.strftime("%Y-%m-%d %H:%M") if item.fecha_hora else "—"
                it_fecha = QTableWidgetItem(f_str)
                it_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_financial.setItem(row, 1, it_fecha)

                self.table_financial.setItem(row, 2, QTableWidgetItem(item.concepto))
                self.table_financial.setItem(row, 3, QTableWidgetItem(item.metodo_pago))

                it_monto = QTableWidgetItem(f"${item.monto:,.2f}")
                it_monto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                it_monto.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                if item.tipo_movimiento == "REEMBOLSO_GARANTIA":
                    it_monto.setForeground(Qt.GlobalColor.red)
                else:
                    it_monto.setForeground(Qt.GlobalColor.cyan)
                self.table_financial.setItem(row, 4, it_monto)

                self.table_financial.setItem(row, 5, QTableWidgetItem(item.contrato_codigo or "—"))
                self.table_financial.setItem(row, 6, QTableWidgetItem(item.cliente_nombre or "—"))

        except AppException as e:
            QMessageBox.critical(self, "Error de Reporte", e.message)
        except Exception as e:
            logger.exception("Error al cargar reporte financiero")
            QMessageBox.critical(self, "Error Inesperado", str(e))

    def load_fleet_report(self) -> None:
        """Ejecuta y presenta el reporte de rendimiento y utilización de flota (RF-35)."""
        f_ini = self.fleet_date_from.date().toPython()
        f_fin = self.fleet_date_to.date().toPython()
        cat_id = self.fleet_combo_cat.currentData()
        search = self.fleet_search.text().strip()

        try:
            self._fleet_summary = report_service.get_fleet_utilization_report(
                fecha_inicio=f_ini,
                fecha_fin=f_fin,
                id_categoria=cat_id if cat_id and cat_id > 0 else None,
                search=search,
            )

            s = self._fleet_summary
            self._update_kpi_card_value(self.kpi_fleet_ocup, f"{s.tasa_ocupacion_promedio:.1f}%")
            self._update_kpi_card_value(self.kpi_fleet_vehs, str(s.total_vehiculos))
            self._update_kpi_card_value(self.kpi_fleet_dias_renta, f"{s.total_dias_alquilados} d")
            self._update_kpi_card_value(self.kpi_fleet_dias_taller, f"{sum(it.dias_taller for it in s.items)} d")
            self._update_kpi_card_value(self.kpi_fleet_ingresos, f"${s.ingresos_totales_flota:,.2f}")
            self._update_kpi_card_value(self.kpi_fleet_top, s.vehiculo_mas_rentado)

            # Poblar tabla
            self.table_fleet.setRowCount(0)
            for it in s.items:
                row = self.table_fleet.rowCount()
                self.table_fleet.insertRow(row)

                it_placa = QTableWidgetItem(it.placa)
                it_placa.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                it_placa.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_fleet.setItem(row, 0, it_placa)

                self.table_fleet.setItem(row, 1, QTableWidgetItem(it.marca_modelo))
                self.table_fleet.setItem(row, 2, QTableWidgetItem(it.categoria))

                it_ct = QTableWidgetItem(str(it.total_contratos))
                it_ct.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_fleet.setItem(row, 3, it_ct)

                it_d = QTableWidgetItem(f"{it.dias_alquilado} d")
                it_d.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_fleet.setItem(row, 4, it_d)

                it_ocup = QTableWidgetItem(f"{it.tasa_ocupacion_pct:.1f}%")
                it_ocup.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_ocup.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                if it.tasa_ocupacion_pct >= 50.0:
                    it_ocup.setForeground(Qt.GlobalColor.green)
                elif it.tasa_ocupacion_pct > 0:
                    it_ocup.setForeground(Qt.GlobalColor.cyan)
                self.table_fleet.setItem(row, 5, it_ocup)

                it_ing = QTableWidgetItem(f"${it.ingresos_generados:,.2f}")
                it_ing.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_fleet.setItem(row, 6, it_ing)

                it_dt = QTableWidgetItem(f"{it.dias_taller} d")
                it_dt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_fleet.setItem(row, 7, it_dt)

                it_gt = QTableWidgetItem(f"${it.gastos_taller:,.2f}")
                it_gt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_fleet.setItem(row, 8, it_gt)

                it_st = QTableWidgetItem(it.estado_actual)
                it_st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_fleet.setItem(row, 9, it_st)

        except AppException as e:
            QMessageBox.critical(self, "Error de Reporte", e.message)
        except Exception as e:
            logger.exception("Error al cargar reporte de flota")
            QMessageBox.critical(self, "Error Inesperado", str(e))

    def load_client_history_report(self) -> None:
        """Ejecuta y presenta el reporte de siniestralidad e historial de clientes (RF-36)."""
        criterio = self.client_combo_criterio.currentData()
        search = self.client_search.text().strip()

        try:
            self._client_summary = report_service.get_client_history_report(
                filtro_criterio=criterio or "TODOS",
                search=search,
            )

            s = self._client_summary
            self._update_kpi_card_value(self.kpi_cli_total, str(s.total_clientes_analizados))
            self._update_kpi_card_value(self.kpi_cli_frec, str(s.clientes_frecuentes))
            self._update_kpi_card_value(self.kpi_cli_siniestros, str(s.clientes_con_siniestros))
            self._update_kpi_card_value(self.kpi_cli_riesgo, str(s.clientes_alto_riesgo))

            # Poblar tabla
            self.table_clients.setRowCount(0)
            for it in s.items:
                row = self.table_clients.rowCount()
                self.table_clients.insertRow(row)

                self.table_clients.setItem(row, 0, QTableWidgetItem(it.identificacion))
                self.table_clients.setItem(row, 1, QTableWidgetItem(it.nombre_completo))
                self.table_clients.setItem(row, 2, QTableWidgetItem(it.telefono))

                it_st = QTableWidgetItem(it.estado_cliente)
                it_st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_clients.setItem(row, 3, it_st)

                it_ct = QTableWidgetItem(str(it.total_contratos))
                it_ct.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_clients.setItem(row, 4, it_ct)

                it_gasto = QTableWidgetItem(f"${it.total_gastado:,.2f}")
                it_gasto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_clients.setItem(row, 5, it_gasto)

                it_dias = QTableWidgetItem(f"{it.total_dias_alquilados} d")
                it_dias.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_clients.setItem(row, 6, it_dias)

                it_danos = QTableWidgetItem(str(it.total_danos_reportados))
                it_danos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if it.total_danos_reportados > 0:
                    it_danos.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    it_danos.setForeground(Qt.GlobalColor.red)
                self.table_clients.setItem(row, 7, it_danos)

                it_pen = QTableWidgetItem(f"${it.total_cargos_penalizaciones:,.2f}")
                it_pen.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_clients.setItem(row, 8, it_pen)

                # Nivel de Riesgo Badge
                cell_w_r = QWidget()
                cell_w_r.setStyleSheet("background: transparent;")
                hl_r = QHBoxLayout(cell_w_r)
                hl_r.setContentsMargins(4, 2, 4, 2)
                if it.nivel_riesgo == "ALTO":
                    badge = create_badge("⛔ ALTO", "rgba(239, 68, 68, 0.15)", "#f87171", "rgba(239, 68, 68, 0.4)")
                elif it.nivel_riesgo == "MEDIO":
                    badge = create_badge("⚠️ MEDIO", "rgba(245, 158, 11, 0.15)", "#fbbf24", "rgba(245, 158, 11, 0.4)")
                else:
                    badge = create_badge("✓ BAJO", "rgba(16, 185, 129, 0.15)", "#34d399", "rgba(16, 185, 129, 0.4)")
                hl_r.addWidget(badge)
                self.table_clients.setCellWidget(row, 9, cell_w_r)

        except AppException as e:
            QMessageBox.critical(self, "Error de Reporte", e.message)
        except Exception as e:
            logger.exception("Error al cargar reporte de clientes")
            QMessageBox.critical(self, "Error Inesperado", str(e))

    # ------------------------------------------------------------------------
    # MANEJADORES DE EXPORTACIÓN (RF-37)
    # ------------------------------------------------------------------------

    def _get_active_tab_data(self) -> tuple[str, str, List[str], List[List[Any]], Dict[str, str]]:
        """Retorna el título, subtítulo, encabezados, matriz de datos y KPIs de la pestaña activa."""
        tab_idx = self.tabs.currentIndex()

        if tab_idx == 0:
            title = "Reporte Consolidado de Ingresos Financieros y Recaudación (RF-34)"
            subtitle = f"Periodo: {self.fin_date_from.date().toString('yyyy-MM-dd')} al {self.fin_date_to.date().toString('yyyy-MM-dd')}"
            table = self.table_financial
            s = self._financial_summary
            kpis = {
                "Facturación Total": f"${s.total_facturado:,.2f}" if s else "$0.00",
                "Ingresos Renta": f"${s.ingresos_renta:,.2f}" if s else "$0.00",
                "Penalizaciones": f"${s.ingresos_penalizaciones:,.2f}" if s else "$0.00",
                "Gastos Taller": f"${s.gastos_mantenimiento:,.2f}" if s else "$0.00",
                "Ingreso Neto": f"${s.ingreso_neto:,.2f}" if s else "$0.00",
                "Ticket Promedio": f"${s.ticket_promedio:,.2f}" if s else "$0.00",
            }
        elif tab_idx == 1:
            title = "Reporte de Utilización y Rendimiento de Flota (RF-35)"
            subtitle = f"Periodo: {self.fleet_date_from.date().toString('yyyy-MM-dd')} al {self.fleet_date_to.date().toString('yyyy-MM-dd')}"
            table = self.table_fleet
            s = self._fleet_summary
            kpis = {
                "Ocupación Global": f"{s.tasa_ocupacion_promedio:.1f}%" if s else "0.0%",
                "Total Vehículos": str(s.total_vehiculos) if s else "0",
                "Días en Renta": f"{s.total_dias_alquilados} d" if s else "0 d",
                "Ingresos Flota": f"${s.ingresos_totales_flota:,.2f}" if s else "$0.00",
                "Más Rentado": s.vehiculo_mas_rentado if s else "—",
            }
        else:
            title = "Reporte de Historial de Clientes, Siniestralidad y Riesgo (RF-36)"
            subtitle = f"Criterio: {self.client_combo_criterio.currentText()}"
            table = self.table_clients
            s = self._client_summary
            kpis = {
                "Clientes Analizados": str(s.total_clientes_analizados) if s else "0",
                "Frecuentes": str(s.clientes_frecuentes) if s else "0",
                "Con Siniestros": str(s.clientes_con_siniestros) if s else "0",
                "Alto Riesgo": str(s.clientes_alto_riesgo) if s else "0",
            }

        headers = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
        rows: List[List[Any]] = []
        for r in range(table.rowCount()):
            row_data = []
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item:
                    row_data.append(item.text())
                else:
                    # En caso de celdas con QWidget badge (ej. Riesgo)
                    cell_widget = table.cellWidget(r, c)
                    if cell_widget:
                        lbl = cell_widget.findChild(QLabel)
                        row_data.append(lbl.text().strip() if lbl else "—")
                    else:
                        row_data.append("—")
            rows.append(row_data)

        return title, subtitle, headers, rows, kpis

    def _handle_export_csv(self) -> None:
        """Exporta la tabla actualmente activa a formato CSV compatible con Microsoft Excel (RF-37)."""
        title, subtitle, headers, rows, _ = self._get_active_tab_data()
        default_name = f"{title.split('(')[0].strip().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte a CSV / Excel",
            default_name,
            "Archivos CSV (*.csv);;Todos los archivos (*.*)",
        )
        if not filepath:
            return

        try:
            report_service.export_to_csv(
                filepath=filepath,
                headers=headers,
                rows=rows,
                title=f"{title} — {subtitle}",
            )
            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"El reporte ha sido exportado satisfactoriamente a:\n\n{filepath}\n\n"
                f"• Total de registros exportados: {len(rows)}\n"
                "• Formato: CSV delimitado por punto y coma (UTF-8 con BOM para Excel).",
            )
        except AppException as e:
            QMessageBox.critical(self, "Error al Exportar", e.message)

    def _handle_export_html(self) -> None:
        """Exporta el reporte activo a formato HTML con diseño profesional para impresión o PDF (RF-37)."""
        title, subtitle, headers, rows, kpis = self._get_active_tab_data()
        default_name = f"{title.split('(')[0].strip().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Informe Imprimible (HTML / PDF)",
            default_name,
            "Archivos Web HTML (*.html);;Todos los archivos (*.*)",
        )
        if not filepath:
            return

        try:
            report_service.export_to_html(
                filepath=filepath,
                title=title,
                headers=headers,
                rows=rows,
                kpis=kpis,
                subtitle=subtitle,
            )
            QMessageBox.information(
                self,
                "Informe Generado Exitosamente",
                f"El informe imprimible ha sido generado en:\n\n{filepath}\n\n"
                "Puede abrirlo en cualquier navegador web moderno y presionar Ctrl+P para imprimirlo o 'Guardar como PDF'.",
            )
        except AppException as e:
            QMessageBox.critical(self, "Error al Exportar", e.message)
