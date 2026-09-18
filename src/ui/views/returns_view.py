"""Vista principal para la gestión de Devoluciones, Inspecciones de Retorno y Liquidaciones (Fase 6)."""

from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import ContractStatus
from src.domain.models import Contract, ReturnInspection
from src.services.contract_service import contract_service
from src.services.return_service import return_service
from src.ui.views.return_form_dialog import ReturnFormDialog

logger = get_logger(__name__)


class ReturnsView(QWidget):
    """Pantalla de administración, consulta y registro de devoluciones físicas y liquidaciones."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.returns_list: List[ReturnInspection] = []
        self._init_ui()
        self.load_data()

    def _init_ui(self) -> None:
        """Construye la interfaz visual de la vista de devoluciones."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(16)

        # 1. Cabecera con botón de retroceso y título
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
        title = QLabel("Devoluciones e Inspecciones de Retorno (Check-out)")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #f8fafc;")

        subtitle = QLabel("Recepción de vehículos, inspección de carrocería, odómetro, combustible y balance de liquidación.")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #94a3b8;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        self.btn_new_return = QPushButton("📥 Registrar Devolución")
        self.btn_new_return.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_new_return.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_return.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        self.btn_new_return.clicked.connect(self._open_select_contract_for_return)
        header_layout.addWidget(self.btn_new_return)

        main_layout.addLayout(header_layout)

        # 2. Barra de Búsqueda y Filtros
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(8, 6, 8, 6)
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por contrato, cliente, cédula o placa vehicular...")
        self.search_input.setFont(QFont("Segoe UI", 9))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.search_input.textChanged.connect(self.load_data)
        filter_layout.addWidget(self.search_input, stretch=2)

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self._style_button(self.btn_refresh, "#334155", "#475569")
        self.btn_refresh.clicked.connect(self.load_data)
        filter_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(filter_card)

        # 3. Tabla Principal de Devoluciones (10 columnas)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Contrato",
            "Cliente",
            "Placa",
            "Modelo",
            "Fecha Retorno",
            "Km Retorno",
            "Combustible",
            "Retraso",
            "Daños",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                color: #f8fafc;
                selection-background-color: #243247;
                selection-color: #38bdf8;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 8px;
                border: 1px solid #334155;
                font-size: 9pt;
                font-weight: bold;
            }
        """)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        main_layout.addWidget(self.table, stretch=1)

        # 4. Barra de Acciones Inferiores
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        self.btn_view_detail = QPushButton("👁 Ver Acta y Liquidación")
        self._style_button(self.btn_view_detail, "#0284c7", "#0369a1")
        self.btn_view_detail.clicked.connect(self._on_view_detail_clicked)
        actions_bar.addWidget(self.btn_view_detail)

        actions_bar.addStretch()

        self.counter_label = QLabel("0 devoluciones registradas")
        self.counter_label.setFont(QFont("Segoe UI", 9))
        self.counter_label.setStyleSheet("color: #94a3b8;")
        actions_bar.addWidget(self.counter_label)

        main_layout.addLayout(actions_bar)

    def load_data(self) -> None:
        """Carga y actualiza los datos de la tabla de devoluciones."""
        search = self.search_input.text().strip()
        try:
            self.returns_list = return_service.list_returns(search=search)
            self.table.setRowCount(0)

            for ret in self.returns_list:
                row = self.table.rowCount()
                self.table.insertRow(row)

                self.table.setItem(row, 0, QTableWidgetItem(str(ret.id_devolucion)))
                self.table.setItem(row, 1, QTableWidgetItem(ret.contrato_codigo or "N/A"))
                self.table.setItem(row, 2, QTableWidgetItem(ret.cliente_nombre or "N/A"))
                self.table.setItem(row, 3, QTableWidgetItem(ret.vehiculo_placa or "N/A"))
                self.table.setItem(row, 4, QTableWidgetItem(ret.vehiculo_modelo or "N/A"))

                fecha_str = ret.fecha_hora_retorno_real.strftime("%d/%m/%Y %H:%M") if ret.fecha_hora_retorno_real else "N/A"
                self.table.setItem(row, 5, QTableWidgetItem(fecha_str))

                km_str = f"{ret.kilometraje_retorno:,} km (+{ret.km_recorridos:,} km)"
                self.table.setItem(row, 6, QTableWidgetItem(km_str))

                comb_pct = int(ret.combustible_retorno * 100)
                self.table.setItem(row, 7, QTableWidgetItem(f"{comb_pct}%"))

                retraso_str = f"{ret.horas_retraso} hr(s)" if ret.horas_retraso > 0 else "A tiempo"
                self.table.setItem(row, 8, QTableWidgetItem(retraso_str))

                danios_str = f"{len(ret.danios)} avería(s) (${ret.costo_total_danios:,.2f})" if ret.danios else "Sin averías"
                self.table.setItem(row, 9, QTableWidgetItem(danios_str))

            total_count = len(self.returns_list)
            self.counter_label.setText(f"{total_count} devolución{'es' if total_count != 1 else ''} registrada{'s' if total_count != 1 else ''}")

        except Exception as e:
            logger.exception("Error al cargar devoluciones.")
            QMessageBox.critical(self, "Error de Datos", f"No se pudo cargar la lista de devoluciones: {e}")

    def _get_selected_return(self) -> Optional[ReturnInspection]:
        """Obtiene la devolución seleccionada en la tabla."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.returns_list):
            return None
        return self.returns_list[row]

    def _on_row_double_clicked(self) -> None:
        self._on_view_detail_clicked()

    def _on_view_detail_clicked(self) -> None:
        """Abre la devolución seleccionada en modo auditoría."""
        ret = self._get_selected_return()
        if not ret:
            QMessageBox.information(self, "Selección Requerida", "Seleccione un acta de devolución de la lista.")
            return

        contract = contract_service.get_contract(ret.id_contrato)
        dlg = ReturnFormDialog(contract=contract, return_inspection=ret, parent=self)
        dlg.exec()

    def _open_select_contract_for_return(self) -> None:
        """Despliega la selección de contratos activos para proceder a su recepción."""
        active_contracts = contract_service.list_contracts(status="ACTIVO")
        if not active_contracts:
            QMessageBox.information(
                self,
                "Sin Contratos Activos",
                "No existen contratos activos pendientes de devolución en este momento.",
            )
            return

        # Diálogo simple de selección de contrato
        select_dlg = QDialog(self)
        select_dlg.setWindowTitle("Seleccionar Contrato para Devolución")
        select_dlg.resize(650, 400)
        select_dlg.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        vbox = QVBoxLayout(select_dlg)
        vbox.setContentsMargins(18, 14, 18, 14)
        vbox.setSpacing(10)

        lbl = QLabel("Seleccione el contrato activo cuyo vehículo va a ser recibido:")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        vbox.addWidget(lbl)

        contract_table = QTableWidget(len(active_contracts), 4)
        contract_table.setHorizontalHeaderLabels(["Código", "Cliente", "Placa", "Fin Pactado"])
        contract_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        contract_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        contract_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        contract_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        contract_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                gridline-color: #334155;
                color: #f8fafc;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                padding: 6px;
            }
        """)

        for i, c in enumerate(active_contracts):
            contract_table.setItem(i, 0, QTableWidgetItem(c.codigo_contrato))
            contract_table.setItem(i, 1, QTableWidgetItem(c.cliente_nombre or "N/A"))
            contract_table.setItem(i, 2, QTableWidgetItem(c.vehiculo_placa or "N/A"))
            fin_str = c.fecha_hora_fin_pactada.strftime("%d/%m/%Y %H:%M") if c.fecha_hora_fin_pactada else "N/A"
            contract_table.setItem(i, 3, QTableWidgetItem(fin_str))

        contract_table.selectRow(0)
        vbox.addWidget(contract_table)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(select_dlg.reject)
        self._style_button(btn_cancel, "#334155", "#475569")
        btn_box.addWidget(btn_cancel)

        btn_box.addStretch()

        btn_proceed = QPushButton("Continuar a Inspección →")
        btn_proceed.clicked.connect(select_dlg.accept)
        self._style_button(btn_proceed, "#059669", "#047857")
        btn_box.addWidget(btn_proceed)
        vbox.addLayout(btn_box)

        if select_dlg.exec() == QDialog.DialogCode.Accepted:
            selected_idx = contract_table.currentRow()
            if 0 <= selected_idx < len(active_contracts):
                target_contract = active_contracts[selected_idx]
                self.open_return_dialog_for_contract(target_contract)

    def open_return_dialog_for_contract(self, contract: Contract) -> None:
        """Abre el diálogo de recepción e inspección para un contrato dado."""
        dlg = ReturnFormDialog(contract=contract, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    @staticmethod
    def _style_button(btn: QPushButton, bg_color: str, hover_color: str) -> None:
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)
