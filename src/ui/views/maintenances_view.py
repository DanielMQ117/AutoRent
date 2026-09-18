"""Vista principal para la gestión de Mantenimiento de Flota y Taller Mecánico (Fase 8)."""

from datetime import datetime
from decimal import Decimal
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
from src.domain.enums import MaintenanceStatus, MaintenanceType
from src.domain.models import Maintenance
from src.services.maintenance_service import maintenance_service
from src.ui.components.badges import get_maintenance_status_badge, get_maintenance_type_badge
from src.ui.views.maintenance_complete_dialog import MaintenanceCompleteDialog
from src.ui.views.maintenance_form_dialog import MaintenanceFormDialog

logger = get_logger(__name__)


class MaintenancesView(QWidget):
    """Pantalla para administrar órdenes de servicio en taller, bloqueo operativo y reactivación."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.maintenances_list: List[Maintenance] = []
        self._init_ui()
        self.load_data()

    def _init_ui(self) -> None:
        """Construye la interfaz visual del módulo de mantenimientos."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(14)

        # 1. Cabecera con botón volver, título y acción
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
        title = QLabel("Mantenimiento de Flota y Taller Mecánico")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #f8fafc;")

        subtitle = QLabel("Control de servicio preventivo y correctivo, bloqueo operativo (RF-32) y reprogramación de odómetro.")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #94a3b8;")
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        self.btn_new_maintenance = QPushButton("🔧 Nueva Entrada a Taller")
        self.btn_new_maintenance.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_new_maintenance.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_maintenance.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_new_maintenance.clicked.connect(self._open_new_maintenance_dialog)
        header_layout.addWidget(self.btn_new_maintenance)

        main_layout.addLayout(header_layout)

        # 2. Tarjetas de Métricas / KPIs
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total = self._create_kpi_card("Total Órdenes", "0", "#38bdf8")
        self.card_active = self._create_kpi_card("En Taller Activos", "0", "#fbbf24")
        self.card_completed = self._create_kpi_card("Finalizadas", "0", "#34d399")
        self.card_expenses = self._create_kpi_card("Inversión Total", "$0.00", "#c084fc")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_active)
        kpi_layout.addWidget(self.card_completed)
        kpi_layout.addWidget(self.card_expenses)
        main_layout.addLayout(kpi_layout)

        # 3. Barra de Filtros y Búsqueda
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
        self.search_input.setPlaceholderText("🔍 Buscar por placa, modelo, taller o trabajo...")
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

        lbl_filter_status = QLabel("Estado:")
        lbl_filter_status.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.combo_filter_status = QComboBox()
        self.combo_filter_status.addItem("TODOS", "TODOS")
        self.combo_filter_status.addItem("🔧 EN TALLER", MaintenanceStatus.EN_TALLER.value)
        self.combo_filter_status.addItem("✓ FINALIZADO", MaintenanceStatus.FINALIZADO.value)
        self.combo_filter_status.addItem("✖ CANCELADO", MaintenanceStatus.CANCELADO.value)
        self.combo_filter_status.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)
        self.combo_filter_status.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(lbl_filter_status)
        filter_layout.addWidget(self.combo_filter_status)

        lbl_filter_type = QLabel("Tipo:")
        lbl_filter_type.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.combo_filter_type = QComboBox()
        self.combo_filter_type.addItem("TODOS", "TODOS")
        self.combo_filter_type.addItem("🛡 PREVENTIVO", MaintenanceType.PREVENTIVO.value)
        self.combo_filter_type.addItem("⚠️ CORRECTIVO", MaintenanceType.CORRECTIVO.value)
        self.combo_filter_type.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)
        self.combo_filter_type.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(lbl_filter_type)
        filter_layout.addWidget(self.combo_filter_type)

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self._style_button(self.btn_refresh, "#334155", "#475569")
        self.btn_refresh.clicked.connect(self.load_data)
        filter_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(filter_card)

        # 4. Tabla Principal de Mantenimientos (9 columnas)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Vehículo",
            "Tipo",
            "Taller Mecánico",
            "Fecha Ingreso",
            "Odómetro Entrada",
            "Salida Real / Est.",
            "Costo ($)",
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

        # 5. Barra de Acciones Inferiores
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        self.btn_complete = QPushButton("✓ Finalizar y Liberar Unidad")
        self._style_button(self.btn_complete, "#059669", "#047857")
        self.btn_complete.clicked.connect(self._on_complete_clicked)
        actions_bar.addWidget(self.btn_complete)

        self.btn_cancel = QPushButton("✖ Cancelar Orden")
        self._style_button(self.btn_cancel, "#dc2626", "#b91c1c")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        actions_bar.addWidget(self.btn_cancel)

        self.btn_view_detail = QPushButton("👁 Ver Detalle")
        self._style_button(self.btn_view_detail, "#0284c7", "#0369a1")
        self.btn_view_detail.clicked.connect(self._on_view_detail_clicked)
        actions_bar.addWidget(self.btn_view_detail)

        actions_bar.addStretch()

        self.counter_label = QLabel("0 órdenes registradas")
        self.counter_label.setFont(QFont("Segoe UI", 9))
        self.counter_label.setStyleSheet("color: #94a3b8;")
        actions_bar.addWidget(self.counter_label)

        main_layout.addLayout(actions_bar)

    def _create_kpi_card(self, title: str, initial_value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        vbox = QVBoxLayout(card)
        vbox.setSpacing(2)
        vbox.setContentsMargins(8, 6, 8, 6)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        lbl_title.setStyleSheet("color: #94a3b8; text-transform: uppercase;")

        lbl_val = QLabel(initial_value)
        lbl_val.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_hex};")
        lbl_val.setObjectName("kpi_value")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        return card

    def _update_kpi_card_value(self, card: QFrame, value_text: str) -> None:
        lbl = card.findChild(QLabel, "kpi_value")
        if lbl:
            lbl.setText(value_text)

    def _style_button(self, btn: QPushButton, bg_color: str, hover_color: str) -> None:
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

    def load_data(self) -> None:
        """Carga y actualiza las órdenes en la tabla y los KPIs."""
        search = self.search_input.text().strip()
        status = self.combo_filter_status.currentData()
        m_type = self.combo_filter_type.currentData()

        try:
            self.maintenances_list = maintenance_service.list_maintenances(
                search=search,
                status=status if status != "TODOS" else None,
                maintenance_type=m_type if m_type != "TODOS" else None,
            )
            self.table.setRowCount(0)

            for m in self.maintenances_list:
                row = self.table.rowCount()
                self.table.insertRow(row)

                # Col 0: ID
                item_id = QTableWidgetItem(f"#{m.id_mantenimiento}")
                item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, item_id)

                # Col 1: Vehículo
                veh_str = f"{m.vehiculo_placa or '—'} ({m.vehiculo_modelo or '—'})"
                self.table.setItem(row, 1, QTableWidgetItem(veh_str))

                # Col 2: Tipo Badge
                badge_type = get_maintenance_type_badge(m.tipo_mantenimiento)
                cell_w_type = QWidget()
                cell_w_type.setStyleSheet("background: transparent;")
                hl_t = QHBoxLayout(cell_w_type)
                hl_t.setContentsMargins(4, 2, 4, 2)
                hl_t.addWidget(badge_type)
                self.table.setCellWidget(row, 2, cell_w_type)

                # Col 3: Taller
                self.table.setItem(row, 3, QTableWidgetItem(m.taller_servicio))

                # Col 4: Fecha Ingreso
                f_in = m.fecha_ingreso.strftime("%Y-%m-%d %H:%M") if m.fecha_ingreso else "—"
                item_fin = QTableWidgetItem(f_in)
                item_fin.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, item_fin)

                # Col 5: Odómetro Entrada
                item_km = QTableWidgetItem(f"{m.kilometraje_entrada:,} km")
                item_km.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 5, item_km)

                # Col 6: Salida Real o Estimada
                if m.fecha_salida_real:
                    salida_str = m.fecha_salida_real.strftime("%Y-%m-%d %H:%M")
                elif m.fecha_salida_estimada:
                    salida_str = f"{m.fecha_salida_estimada} (Est.)"
                else:
                    salida_str = "—"
                item_out = QTableWidgetItem(salida_str)
                item_out.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 6, item_out)

                # Col 7: Costo Total
                costo_str = f"${m.costo_total:,.2f}"
                item_cost = QTableWidgetItem(costo_str)
                item_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_cost.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                item_cost.setForeground(Qt.GlobalColor.cyan)
                self.table.setItem(row, 7, item_cost)

                # Col 8: Estado Badge
                badge_status = get_maintenance_status_badge(m.estado)
                cell_w_st = QWidget()
                cell_w_st.setStyleSheet("background: transparent;")
                hl_s = QHBoxLayout(cell_w_st)
                hl_s.setContentsMargins(4, 2, 4, 2)
                hl_s.addWidget(badge_status)
                self.table.setCellWidget(row, 8, cell_w_st)

            self.counter_label.setText(f"{len(self.maintenances_list)} órdenes registradas")

            # Actualizar KPIs
            kpis = maintenance_service.get_maintenance_kpis()
            self._update_kpi_card_value(self.card_total, str(kpis["total_ordenes"]))
            self._update_kpi_card_value(self.card_active, str(kpis["en_taller"]))
            self._update_kpi_card_value(self.card_completed, str(kpis["finalizadas"]))
            self._update_kpi_card_value(self.card_expenses, f"${kpis['gasto_total']:,.2f}")

        except AppException as e:
            QMessageBox.critical(self, "Error de Datos", f"Error al cargar mantenimientos: {e.message}")
        except Exception as e:
            logger.exception("Error general al cargar órdenes de mantenimiento")
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al cargar datos: {str(e)}")

    def _get_selected_order(self) -> Optional[Maintenance]:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.maintenances_list):
            return None
        return self.maintenances_list[row]

    def _open_new_maintenance_dialog(self, preselected_vehicle_id: Optional[int] = None) -> None:
        """Abre el diálogo para registrar una nueva entrada a taller."""
        dialog = MaintenanceFormDialog(self, preselected_vehicle_id=preselected_vehicle_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _on_complete_clicked(self) -> None:
        """Abre el diálogo para finalizar la orden seleccionada."""
        order = self._get_selected_order()
        if not order:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione una orden de la lista para finalizar.")
            return

        if order.estado != MaintenanceStatus.EN_TALLER:
            QMessageBox.information(
                self,
                "Orden no Elegible",
                f"La orden #{order.id_mantenimiento} se encuentra '{order.estado.value}'. "
                "Solo las órdenes 'EN_TALLER' pueden finalizarse.",
            )
            return

        dialog = MaintenanceCompleteDialog(self, maintenance=order)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _on_cancel_clicked(self) -> None:
        """Cancela una orden activa en taller previa confirmación."""
        order = self._get_selected_order()
        if not order:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione una orden para cancelar.")
            return

        if order.estado != MaintenanceStatus.EN_TALLER:
            QMessageBox.information(
                self,
                "Orden no Elegible",
                f"La orden #{order.id_mantenimiento} no se encuentra activa en taller.",
            )
            return

        res = QMessageBox.question(
            self,
            "Confirmar Cancelación",
            f"¿Está seguro de cancelar la orden #{order.id_mantenimiento} del vehículo {order.vehiculo_placa}?\n\n"
            "El vehículo será desbloqueado y devuelto al estado 'DISPONIBLE'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            try:
                maintenance_service.cancel_maintenance(
                    id_mantenimiento=order.id_mantenimiento,
                    motivo="Cancelada por usuario desde panel",
                )
                QMessageBox.information(self, "Orden Cancelada", f"La orden #{order.id_mantenimiento} ha sido cancelada.")
                self.load_data()
            except AppException as e:
                QMessageBox.critical(self, "Error al Cancelar", e.message)

    def _on_row_double_clicked(self) -> None:
        self._on_view_detail_clicked()

    def _on_view_detail_clicked(self) -> None:
        """Muestra el detalle completo de la orden en un cuadro de diálogo."""
        order = self._get_selected_order()
        if not order:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione una orden para ver su detalle.")
            return

        f_in = order.fecha_ingreso.strftime("%Y-%m-%d %H:%M") if order.fecha_ingreso else "—"
        f_out = order.fecha_salida_real.strftime("%Y-%m-%d %H:%M") if order.fecha_salida_real else (
            f"{order.fecha_salida_estimada} (Estimada)" if order.fecha_salida_estimada else "—"
        )

        detalle = (
            f"Ficha Técnica de Orden de Taller #{order.id_mantenimiento}\n"
            f"══════════════════════════════════════════════════\n"
            f"• Vehículo: {order.vehiculo_placa} — {order.vehiculo_modelo} ({order.vehiculo_categoria})\n"
            f"• Odómetro de Ingreso: {order.kilometraje_entrada:,} km\n"
            f"• Odómetro Actual Vehículo: {order.vehiculo_kilometraje_actual:,} km\n"
            f"• Próximo Mantenimiento Programado: {order.km_proximo_mantenimiento_actual:,} km\n\n"
            f"• Tipo de Servicio: {order.tipo_mantenimiento.value}\n"
            f"• Taller / Proveedor: {order.taller_servicio}\n"
            f"• Fecha de Ingreso: {f_in}\n"
            f"• Fecha de Salida: {f_out}\n"
            f"• Duración: {order.duracion_dias} día(s)\n"
            f"• Costo Total: ${order.costo_total:,.2f}\n"
            f"• Estado Operativo: {order.estado.value}\n"
            f"• Registrado por: {order.usuario_nombre or 'Sistema'}\n\n"
            f"Descripción / Trabajos Realizados:\n"
            f"{order.descripcion_trabajo}\n"
        )
        QMessageBox.information(self, f"Detalle Orden #{order.id_mantenimiento}", detalle)
