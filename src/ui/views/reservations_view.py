"""Vista principal para la administración del Módulo de Reservas y Disponibilidad."""

from datetime import datetime
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
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
    QComboBox,
    QDialog,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import ReservationStatus
from src.domain.models import Reservation
from src.services.reservation_service import reservation_service
from src.ui.components.badges import get_reservation_status_badge
from src.ui.views.reservation_form_dialog import ReservationFormDialog

logger = get_logger(__name__)


class ReservationsView(QWidget):
    """Pantalla principal para consultar, filtrar y gestionar reservas."""

    # Señal emitida para regresar al menú principal del Dashboard
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._reservations: list[Reservation] = []
        self._init_ui()

    def _init_ui(self) -> None:
        """Inicializa la interfaz gráfica y los controles de filtrado."""
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(16)

        # 1. Barra de Encabezado
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
        title_label = QLabel("Gestión de Reservas y Disponibilidad")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc;")

        subtitle_label = QLabel(
            "Fase 4: Verificación de disponibilidad temporal, cálculo de cotización y bloqueo de flota."
        )
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet("color: #94a3b8;")

        title_info_layout.addWidget(title_label)
        title_info_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_info_layout, stretch=1)

        # Botón para Crear Reserva
        self.new_btn = QPushButton("＋ Nueva Reserva")
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

        # Campo de Búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por código, cliente o placa...")
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

        # Filtro de Estado
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
        self.status_combo.addItem("TODAS", "TODAS")
        for st in ReservationStatus:
            self.status_combo.addItem(st.value, st.value)
        self.status_combo.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.status_combo)

        # Botón Refrescar
        refresh_btn = QPushButton("↻ Refrescar")
        refresh_btn.setFont(QFont("Segoe UI", 9))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: none;
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

        # 3. Tabla Principal de Reservas
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Código",
            "Cliente",
            "Categoría",
            "Vehículo",
            "Inicio",
            "Fin",
            "Días",
            "Anticipo",
            "Estado",
        ])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                color: #f8fafc;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #334155;
                padding: 8px 10px;
            }
            QTableWidget::item:selected {
                background-color: #0369a1;
                color: #ffffff;
            }
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(False)

        # Anchos de columna balanceados
        self.table.setColumnWidth(0, 50)    # ID
        self.table.setColumnWidth(1, 125)   # Código
        # Col 2: Cliente (Stretch)
        self.table.setColumnWidth(3, 120)   # Categoría
        self.table.setColumnWidth(4, 140)   # Vehículo
        self.table.setColumnWidth(5, 125)   # Inicio
        self.table.setColumnWidth(6, 125)   # Fin
        self.table.setColumnWidth(7, 65)    # Días
        self.table.setColumnWidth(8, 95)    # Anticipo
        self.table.setColumnWidth(9, 135)   # Estado

        main_layout.addWidget(self.table, stretch=1)

        # 4. Barra Inferior de Operaciones Transaccionales
        actions_bar = QFrame()
        actions_bar.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 14px;
            }
        """)
        bar_layout = QHBoxLayout(actions_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(10)

        self.confirm_btn = QPushButton("✓ Confirmar Reserva")
        self.confirm_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.confirm_btn.clicked.connect(self._handle_confirm)

        self.cancel_btn = QPushButton("✖ Cancelar Reserva")
        self.cancel_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.cancel_btn.clicked.connect(self._handle_cancel)

        self.edit_btn = QPushButton("✏ Editar Reserva")
        self.edit_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.edit_btn.clicked.connect(self._open_edit_dialog)

        self.convert_btn = QPushButton("📄 Formalizar en Contrato")
        self.convert_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.convert_btn.clicked.connect(self._handle_convert_to_contract)

        bar_layout.addWidget(self.confirm_btn)
        bar_layout.addWidget(self.cancel_btn)
        bar_layout.addWidget(self.edit_btn)
        bar_layout.addStretch()
        bar_layout.addWidget(self.convert_btn)

        main_layout.addWidget(actions_bar)

    def load_data(self) -> None:
        """Carga y renderiza el listado de reservas desde la base de datos."""
        search_text = self.search_input.text().strip()
        status_filter = self.status_combo.currentData()

        try:
            self._reservations = reservation_service.list_reservations(
                search=search_text if search_text else None,
                status=status_filter if status_filter != "TODAS" else None,
            )

            self.table.setRowCount(len(self._reservations))

            for row_idx, r in enumerate(self._reservations):
                # 0. ID
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(r.id_reserva)))
                # 1. Código
                item_code = QTableWidgetItem(r.codigo_reserva)
                item_code.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                item_code.setForeground(Qt.GlobalColor.cyan)
                self.table.setItem(row_idx, 1, item_code)
                # 2. Cliente
                cli_text = f"{r.cliente_nombre} ({r.cliente_identificacion})" if r.cliente_nombre else f"Cliente #{r.id_cliente}"
                self.table.setItem(row_idx, 2, QTableWidgetItem(cli_text))
                # 3. Categoría
                cat_text = r.categoria_nombre or f"Cat #{r.id_categoria}"
                self.table.setItem(row_idx, 3, QTableWidgetItem(cat_text))
                # 4. Vehículo Asignado
                veh_text = f"{r.vehiculo_placa} - {r.vehiculo_modelo}" if r.vehiculo_placa else "(Por Asignar en Contrato)"
                self.table.setItem(row_idx, 4, QTableWidgetItem(veh_text))
                # 5. Inicio
                start_str = r.fecha_hora_inicio.strftime("%d/%m/%Y %H:%M") if r.fecha_hora_inicio else "-"
                self.table.setItem(row_idx, 5, QTableWidgetItem(start_str))
                # 6. Fin
                end_str = r.fecha_hora_fin.strftime("%d/%m/%Y %H:%M") if r.fecha_hora_fin else "-"
                self.table.setItem(row_idx, 6, QTableWidgetItem(end_str))
                # 7. Días
                self.table.setItem(row_idx, 7, QTableWidgetItem(f"{r.duracion_dias} d"))
                # 8. Anticipo
                self.table.setItem(row_idx, 8, QTableWidgetItem(f"${r.monto_anticipo:.2f}"))
                # 9. Estado Badge
                badge = get_reservation_status_badge(r.estado)
                self.table.setCellWidget(row_idx, 9, badge)

        except Exception as e:
            logger.error("Error al cargar listado de reservas: %s", e)

    def _get_selected_reservation(self) -> Optional[Reservation]:
        """Retorna la reserva correspondiente a la fila seleccionada en la tabla."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row_idx = selected_rows[0].row()
        if 0 <= row_idx < len(self._reservations):
            return self._reservations[row_idx]
        return None

    def _open_create_dialog(self) -> None:
        """Abre el formulario modal para registrar una nueva reserva."""
        dialog = ReservationFormDialog(parent=self, reservation=None)
        if dialog.exec():
            self.load_data()

    def _open_edit_dialog(self) -> None:
        """Abre el formulario modal para modificar la reserva seleccionada."""
        selected = self._get_selected_reservation()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Por favor seleccione una reserva de la tabla.")
            return

        if selected.estado in (ReservationStatus.CANCELADA, ReservationStatus.VENCIDA, ReservationStatus.CONVERTIDA_A_CONTRATO):
            QMessageBox.warning(
                self,
                "Acción no Permitida",
                f"No se puede modificar una reserva en estado '{selected.estado.value}'.",
            )
            return

        dialog = ReservationFormDialog(parent=self, reservation=selected)
        if dialog.exec():
            self.load_data()

    def _handle_confirm(self) -> None:
        """Confirma una reserva en estado PENDIENTE."""
        selected = self._get_selected_reservation()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Por favor seleccione una reserva para confirmar.")
            return

        if selected.estado != ReservationStatus.PENDIENTE:
            QMessageBox.warning(
                self,
                "Operación Inválida",
                f"La reserva '{selected.codigo_reserva}' ya se encuentra en estado '{selected.estado.value}'.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Reserva",
            f"¿Desea marcar la reserva '{selected.codigo_reserva}' como CONFIRMADA?\n"
            f"Cliente: {selected.cliente_nombre}\n"
            f"Anticipo Registrado: ${selected.monto_anticipo:.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                reservation_service.confirm_reservation(selected.id_reserva)
                QMessageBox.information(self, "Éxito", f"Reserva '{selected.codigo_reserva}' confirmada exitosamente.")
                self.load_data()
            except AppException as e:
                QMessageBox.warning(self, "Error", e.message)

    def _handle_cancel(self) -> None:
        """Cancela una reserva activa."""
        selected = self._get_selected_reservation()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Por favor seleccione una reserva para cancelar.")
            return

        if selected.estado not in (ReservationStatus.PENDIENTE, ReservationStatus.CONFIRMADA):
            QMessageBox.warning(
                self,
                "Operación Inválida",
                f"No se puede cancelar una reserva que ya está '{selected.estado.value}'.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Cancelar Reserva",
            f"¿Está seguro de que desea CANCELAR la reserva '{selected.codigo_reserva}'?\n\n"
            "El vehículo o cupo quedará inmediatamente liberado para otros clientes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                reservation_service.cancel_reservation(selected.id_reserva, motivo="Cancelación solicitada por usuario")
                QMessageBox.information(self, "Reserva Cancelada", f"La reserva '{selected.codigo_reserva}' ha sido cancelada.")
                self.load_data()
            except AppException as e:
                QMessageBox.warning(self, "Error", e.message)

    def _handle_convert_to_contract(self) -> None:
        """Formaliza la reserva seleccionada abriendo el diálogo de contrato y entrega."""
        selected = self._get_selected_reservation()
        if not selected:
            QMessageBox.warning(self, "Selección Requerida", "Por favor seleccione una reserva.")
            return

        if selected.estado not in (ReservationStatus.CONFIRMADA, ReservationStatus.PENDIENTE):
            QMessageBox.warning(
                self,
                "Estado Incompatible",
                f"Solo las reservas 'CONFIRMADAS' o 'PENDIENTES' pueden formalizarse en contrato. Estado actual: '{selected.estado.value}'.",
            )
            return

        from src.ui.views.contract_form_dialog import ContractFormDialog
        dlg = ContractFormDialog(contract=None, reservation=selected, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()
