"""Vista principal para la gestión de Contratos de Alquiler, Salidas y Entregas (Fase 5)."""

from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
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
from src.domain.models import Contract, Reservation
from src.services.contract_service import contract_service
from src.ui.components.badges import get_contract_status_badge
from src.ui.views.contract_form_dialog import ContractFormDialog

logger = get_logger(__name__)


class ContractsView(QWidget):
    """Pantalla de administración, consulta y formalización de contratos de arrendamiento."""

    # Señal para regresar al Dashboard principal
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._contracts: List[Contract] = []
        self._init_ui()

    def _init_ui(self) -> None:
        """Inicializa la interfaz gráfica y los componentes de filtrado."""
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(16)

        # 1. Barra Superior de Navegación y Acciones
        header_layout = QHBoxLayout()

        back_btn = QPushButton("⬅ Volver al Menú Principal")
        back_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)

        title_info_layout = QVBoxLayout()
        title_label = QLabel("Gestión de Contratos y Entrega de Flota")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc;")

        subtitle_label = QLabel(
            "Fase 5: Formalización de contratos, inspección de salida, pólizas y control de depósitos en garantía."
        )
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet("color: #94a3b8;")

        title_info_layout.addWidget(title_label)
        title_info_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_info_layout, stretch=1)

        self.new_btn = QPushButton("＋ Nuevo Contrato Directo")
        self.new_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.new_btn.clicked.connect(self._open_create_dialog)
        header_layout.addWidget(self.new_btn)

        main_layout.addLayout(header_layout)

        # 2. Barra de Filtros y Búsqueda
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(10, 8, 10, 8)
        filter_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por código de contrato, cliente, cédula o placa...")
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

        filter_layout.addWidget(QLabel("Estado:"))
        self.status_combo = QComboBox()
        self.status_combo.setFont(QFont("Segoe UI", 9))
        self.status_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 140px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
            }
        """)
        self.status_combo.addItem("TODOS", "TODOS")
        for st in ContractStatus:
            self.status_combo.addItem(st.value.replace("_", " ").title(), st.value)
        self.status_combo.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.status_combo)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.setFont(QFont("Segoe UI", 9))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(refresh_btn)

        main_layout.addWidget(filter_card)

        # 3. Tabla de Contratos
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Código",
            "Cliente",
            "Identificación",
            "Vehículo / Placa",
            "Cobertura",
            "Inicio Pactado",
            "Fin Pactado",
            "Km Salida",
            "Tarifa/Día",
            "Garantía",
            "Estado",
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

        # 4. Barra de Acciones para fila seleccionada
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        self.btn_view = QPushButton("👁 Ver Detalle")
        self._style_action_button(self.btn_view, "#334155", "#475569")
        self.btn_view.clicked.connect(self._on_view_clicked)
        actions_bar.addWidget(self.btn_view)

        self.btn_cancel = QPushButton("✖ Anular Contrato")
        self._style_action_button(self.btn_cancel, "#7f1d1d", "#991b1b")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        actions_bar.addWidget(self.btn_cancel)

        actions_bar.addStretch()
        self.counter_label = QLabel("0 contratos registrados")
        self.counter_label.setFont(QFont("Segoe UI", 9))
        self.counter_label.setStyleSheet("color: #94a3b8;")
        actions_bar.addWidget(self.counter_label)

        main_layout.addLayout(actions_bar)

    @staticmethod
    def _style_action_button(btn: QPushButton, bg_color: str, hover_color: str) -> None:
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

    def load_data(self) -> None:
        """Carga y visualiza los contratos desde la base de datos aplicando los filtros vigentes."""
        search_query = self.search_input.text().strip()
        status_filter = self.status_combo.currentData()

        try:
            self._contracts = contract_service.list_contracts(
                search=search_query if search_query else None,
                status=status_filter if status_filter != "TODOS" else None,
            )
            self._render_table()
        except Exception as e:
            logger.error("Error al listar contratos: %s", e)
            QMessageBox.critical(self, "Error de Datos", f"No se pudo cargar la lista de contratos: {e}")

    def _render_table(self) -> None:
        """Llena la tabla con los contratos cargados."""
        self.table.setRowCount(0)
        self.counter_label.setText(f"{len(self._contracts)} contrato(s) registrado(s)")

        for c in self._contracts:
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)

            # 0: Código
            item_codigo = QTableWidgetItem(c.codigo_contrato)
            item_codigo.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_codigo.setForeground(Qt.GlobalColor.cyan)
            self.table.setItem(row_pos, 0, item_codigo)

            # 1: Cliente
            self.table.setItem(row_pos, 1, QTableWidgetItem(c.cliente_nombre or f"ID #{c.id_cliente}"))

            # 2: Identificación
            self.table.setItem(row_pos, 2, QTableWidgetItem(c.cliente_identificacion or "--"))

            # 3: Vehículo / Placa
            veh_text = f"{c.vehiculo_placa} — {c.vehiculo_modelo or ''}".strip(" —")
            self.table.setItem(row_pos, 3, QTableWidgetItem(veh_text))

            # 4: Cobertura
            self.table.setItem(row_pos, 4, QTableWidgetItem(c.cobertura_nombre or "--"))

            # 5: Inicio Pactado
            inicio_str = c.fecha_hora_inicio_pactada.strftime("%d/%m/%Y %H:%M") if c.fecha_hora_inicio_pactada else "--"
            self.table.setItem(row_pos, 5, QTableWidgetItem(inicio_str))

            # 6: Fin Pactado
            fin_str = c.fecha_hora_fin_pactada.strftime("%d/%m/%Y %H:%M") if c.fecha_hora_fin_pactada else "--"
            self.table.setItem(row_pos, 6, QTableWidgetItem(fin_str))

            # 7: Km Salida
            self.table.setItem(row_pos, 7, QTableWidgetItem(f"{c.kilometraje_salida:,} km"))

            # 8: Tarifa Diaria
            self.table.setItem(row_pos, 8, QTableWidgetItem(f"${c.tarifa_diaria_aplicada:.2f}"))

            # 9: Monto Garantía
            self.table.setItem(row_pos, 9, QTableWidgetItem(f"${c.monto_garantia:.2f}"))

            # 10: Estado con Badge
            badge_widget = get_contract_status_badge(c.estado)
            cell_container = QWidget()
            layout = QHBoxLayout(cell_container)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(badge_widget)
            self.table.setCellWidget(row_pos, 10, cell_container)

    def _get_selected_contract(self) -> Optional[Contract]:
        """Obtiene el contrato de la fila seleccionada."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        if 0 <= row < len(self._contracts):
            return self._contracts[row]
        return None

    def _open_create_dialog(self) -> None:
        """Abre el diálogo modal para crear un contrato directo."""
        dlg = ContractFormDialog(contract=None, reservation=None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def open_formalize_reservation_dialog(self, reservation: Reservation) -> None:
        """Abre el diálogo para formalizar una reserva específica convirtiéndola a contrato."""
        dlg = ContractFormDialog(contract=None, reservation=reservation, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _on_row_double_clicked(self) -> None:
        self._on_view_clicked()

    def _on_view_clicked(self) -> None:
        """Abre el contrato seleccionado en modo consulta / auditoría."""
        c = self._get_selected_contract()
        if not c:
            QMessageBox.information(self, "Selección Requerida", "Seleccione un contrato de la lista para visualizar.")
            return

        # Cargar el contrato completo con conductores y pagos
        full_contract = contract_service.get_contract(c.id_contrato)
        dlg = ContractFormDialog(contract=full_contract, parent=self)
        dlg.exec()

    def _on_cancel_clicked(self) -> None:
        """Procesa la anulación del contrato activo seleccionado."""
        c = self._get_selected_contract()
        if not c:
            QMessageBox.information(self, "Selección Requerida", "Seleccione un contrato de la lista para anular.")
            return

        if c.estado != ContractStatus.ACTIVO:
            QMessageBox.warning(
                self,
                "Estado no Válido",
                f"Solo los contratos en estado 'ACTIVO' pueden ser anulados. Estado actual: '{c.estado.value}'.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Anulación de Contrato",
            f"¿Está seguro de anular el contrato '{c.codigo_contrato}'?\n\n"
            f"• Cliente: {c.cliente_nombre}\n"
            f"• Vehículo: {c.vehiculo_placa}\n"
            "• El vehículo regresará inmediatamente a estado 'DISPONIBLE'.\n"
            "• Si se cobró depósito de garantía, se registrará el movimiento de reembolso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                contract_service.cancel_contract(c.id_contrato, motivo="Anulación manual desde panel de contratos")
                QMessageBox.information(self, "Contrato Anulado", f"El contrato {c.codigo_contrato} ha sido anulado exitosamente.")
                self.load_data()
            except AppException as e:
                QMessageBox.warning(self, "Operación Denegada", e.message)
            except Exception as e:
                logger.error("Error al anular contrato: %s", e)
                QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al anular el contrato: {e}")
