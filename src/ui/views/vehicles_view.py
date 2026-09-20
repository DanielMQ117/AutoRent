"""Vista principal del módulo de Catálogo de Flota y Vehículos (Fase 3)."""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
from src.domain.enums import VehicleStatus
from src.domain.models import Vehicle
from src.services.vehicle_service import vehicle_service
from src.ui.components.badges import get_vehicle_status_badge
from src.ui.views.vehicle_form_dialog import VehicleFormDialog
from src.ui.views.vehicle_status_dialog import VehicleStatusDialog

logger = get_logger(__name__)


class VehiclesView(QWidget):
    """Vista de catálogo y administración de la flota automotriz con CRUD y control de estados."""

    # Señal para retornar al Dashboard principal
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._vehicles_cache: List[Vehicle] = []
        self._init_ui()
        self._load_category_filter()
        self.load_data()

    def _init_ui(self) -> None:
        """Inicializa los componentes visuales de la vista de vehículos."""
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(18)

        # 1. Barra Superior con Título y Navegación
        top_bar = QHBoxLayout()

        back_btn = QPushButton("← Volver al Panel")
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
        top_bar.addWidget(back_btn)

        title_label = QLabel("Catálogo de Flota & Vehículos")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc; margin-left: 10px;")
        top_bar.addWidget(title_label)

        top_bar.addStretch()

        self.new_vehicle_btn = QPushButton("+ Nuevo Vehículo")
        self.new_vehicle_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.new_vehicle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_vehicle_btn.setStyleSheet("""
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
        self.new_vehicle_btn.clicked.connect(self._handle_new_vehicle)
        top_bar.addWidget(self.new_vehicle_btn)

        main_layout.addLayout(top_bar)

        # 2. Métricas Rápidas de la Flota (KPIs)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)

        self.kpi_total = self._create_kpi_card("Total Flota", "0", "#38bdf8")
        self.kpi_disp = self._create_kpi_card("Disponibles", "0", "#34d399")
        self.kpi_alq = self._create_kpi_card("Alquilados", "0", "#38bdf8")
        self.kpi_mant = self._create_kpi_card("En Taller", "0", "#fbbf24")

        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_disp)
        kpi_layout.addWidget(self.kpi_alq)
        kpi_layout.addWidget(self.kpi_mant)
        main_layout.addLayout(kpi_layout)

        # 3. Barra de Búsqueda y Filtros
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar por placa, VIN, marca, modelo o color...")
        self.search_input.setFont(QFont("Segoe UI", 9))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        self.search_input.textChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.search_input, stretch=3)

        # Filtro de Estado
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("Todos los Estados", "TODOS")
        self.status_filter_combo.addItem("✓ DISPONIBLE", VehicleStatus.DISPONIBLE.value)
        self.status_filter_combo.addItem("⚡ ALQUILADO", VehicleStatus.ALQUILADO.value)
        self.status_filter_combo.addItem("🔧 EN TALLER", VehicleStatus.EN_MANTENIMIENTO.value)
        self.status_filter_combo.addItem("✖ DE BAJA", VehicleStatus.DE_BAJA.value)
        self._style_combo(self.status_filter_combo)
        self.status_filter_combo.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.status_filter_combo)

        # Filtro de Categoría
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.addItem("Todas las Categorías", 0)
        self._style_combo(self.category_filter_combo)
        self.category_filter_combo.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.category_filter_combo)

        refresh_btn = QPushButton("🔄 Refrescar")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        filter_bar.addWidget(refresh_btn)

        main_layout.addLayout(filter_bar)

        # 4. Tabla de Vehículos
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "Placa", "Marca / Modelo", "Año", "Categoría", "Color", "Km Actual", "Combustible", "Próx. Mant.", "Estado", "Acciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._handle_row_double_click)

        # Anchos predeterminados optimizados
        self.table.setColumnWidth(0, 50)    # ID
        self.table.setColumnWidth(1, 100)   # Placa
        # Col 2: Marca / Modelo (Stretch)
        self.table.setColumnWidth(3, 70)    # Año
        self.table.setColumnWidth(4, 115)   # Categoría
        self.table.setColumnWidth(5, 90)    # Color
        self.table.setColumnWidth(6, 100)   # Km Actual
        self.table.setColumnWidth(7, 95)    # Combustible
        self.table.setColumnWidth(8, 140)   # Próx. Mant.
        self.table.setColumnWidth(9, 130)   # Estado
        self.table.setColumnWidth(10, 290)  # Acciones

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
                font-family: 'Segoe UI';
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #283548;
            }
            QTableWidget::item:selected {
                background-color: #24344d;
                color: #38bdf8;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #334155;
                padding: 8px;
            }
        """)
        main_layout.addWidget(self.table, stretch=1)

    def _create_kpi_card(self, title: str, value: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 4px solid {accent_color};
                border-radius: 6px;
                padding: 10px 14px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 8))
        lbl_title.setStyleSheet("color: #94a3b8; border: none;")

        lbl_val = QLabel(value)
        lbl_val.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {accent_color}; border: none;")
        card.value_label = lbl_val

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card

    @staticmethod
    def _style_combo(combo: QComboBox) -> None:
        combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                min-width: 140px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
            }
        """)

    def _load_category_filter(self) -> None:
        """Carga las categorías disponibles en el filtro superior."""
        try:
            categories = vehicle_service.get_categories()
            self.category_filter_combo.blockSignals(True)
            self.category_filter_combo.clear()
            self.category_filter_combo.addItem("Todas las Categorías", 0)
            for cat in categories:
                self.category_filter_combo.addItem(cat.nombre, cat.id_categoria)
            self.category_filter_combo.blockSignals(False)
        except Exception as e:
            logger.warning("No se pudieron cargar categorías en filtro: %s", e)

    def load_data(self) -> None:
        """Carga la lista completa de vehículos desde el servicio BLL."""
        try:
            self._vehicles_cache = vehicle_service.list_vehicles()
            self._update_kpis()
            self._render_table(self._vehicles_cache)
        except Exception as e:
            logger.error("Error al cargar lista de vehículos: %s", e)
            QMessageBox.critical(self, "Error", f"No se pudo cargar la flota vehicular:\n{e}")

    def _update_kpis(self) -> None:
        """Actualiza los contadores de las tarjetas de métricas."""
        total = len(self._vehicles_cache)
        disp = sum(1 for v in self._vehicles_cache if v.estado == VehicleStatus.DISPONIBLE)
        alq = sum(1 for v in self._vehicles_cache if v.estado == VehicleStatus.ALQUILADO)
        mant = sum(1 for v in self._vehicles_cache if v.estado == VehicleStatus.EN_MANTENIMIENTO)

        self.kpi_total.value_label.setText(str(total))
        self.kpi_disp.value_label.setText(str(disp))
        self.kpi_alq.value_label.setText(str(alq))
        self.kpi_mant.value_label.setText(str(mant))

    def _apply_filters(self) -> None:
        """Aplica filtros en memoria según búsqueda, estado y categoría."""
        search = self.search_input.text().strip().lower()
        status_filter = self.status_filter_combo.currentData()
        cat_filter = self.category_filter_combo.currentData()

        filtered = []
        for v in self._vehicles_cache:
            if status_filter != "TODOS" and v.estado.value != status_filter:
                continue

            if cat_filter and cat_filter > 0 and v.id_categoria != cat_filter:
                continue

            if search:
                m_nom = (v.modelo_nombre or "").lower()
                b_nom = (v.marca_nombre or "").lower()
                c_nom = (v.categoria_nombre or "").lower()
                match = (
                    search in v.placa.lower()
                    or search in v.vin.lower()
                    or search in v.color.lower()
                    or search in m_nom
                    or search in b_nom
                    or search in c_nom
                )
                if not match:
                    continue

            filtered.append(v)

        self._render_table(filtered)

    def _render_table(self, vehicles: List[Vehicle]) -> None:
        """Puebla las filas de la tabla con la lista de vehículos."""
        self.table.setRowCount(len(vehicles))

        for row_idx, v in enumerate(vehicles):
            self.table.setRowHeight(row_idx, 46)

            # 0. ID
            item_id = QTableWidgetItem(str(v.id_vehiculo))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, item_id)

            # 1. Placa
            item_placa = QTableWidgetItem(v.placa)
            item_placa.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_placa.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, item_placa)

            # 2. Marca y Modelo
            car_label = f"{v.marca_nombre or ''} {v.modelo_nombre or ''}".strip()
            item_car = QTableWidgetItem(car_label)
            self.table.setItem(row_idx, 2, item_car)

            # 3. Año
            item_anio = QTableWidgetItem(str(v.anio or "-"))
            item_anio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, item_anio)

            # 4. Categoría
            item_cat = QTableWidgetItem(v.categoria_nombre or "-")
            self.table.setItem(row_idx, 4, item_cat)

            # 5. Color
            item_col = QTableWidgetItem(v.color)
            self.table.setItem(row_idx, 5, item_col)

            # 6. Kilometraje Actual
            item_km = QTableWidgetItem(f"{v.kilometraje_actual:,} km")
            item_km.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 6, item_km)

            # 7. Combustible
            fuel_pct = int(float(v.nivel_combustible_actual) * 100)
            item_fuel = QTableWidgetItem(f"{fuel_pct}%")
            item_fuel.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 7, item_fuel)

            # 8. Próximo Mantenimiento
            km_diff = v.km_proximo_mantenimiento - v.kilometraje_actual
            mant_text = f"{v.km_proximo_mantenimiento:,} km ({km_diff:,} km)" if km_diff > 0 else f"{v.km_proximo_mantenimiento:,} km (¡VENCIDO!)"
            item_mant = QTableWidgetItem(mant_text)
            item_mant.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if km_diff <= 0:
                item_mant.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row_idx, 8, item_mant)

            # 9. Badge de Estado
            badge_widget = QWidget()
            badge_layout = QHBoxLayout(badge_widget)
            badge_layout.setContentsMargins(4, 4, 4, 4)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_lbl = get_vehicle_status_badge(v.estado)
            badge_layout.addWidget(badge_lbl)
            self.table.setCellWidget(row_idx, 9, badge_widget)

            # 10. Acciones
            actions_widget = self._create_row_actions(v)
            self.table.setCellWidget(row_idx, 10, actions_widget)

    def _create_row_actions(self, vehicle: Vehicle) -> QWidget:
        """Crea el contenedor con botones de acción para cada vehículo."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Botón Editar
        edit_btn = QPushButton("✏ Editar")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 7px;
                font-size: 8pt;
                font-weight: 600;
                min-height: 22px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        edit_btn.clicked.connect(lambda _, v=vehicle: self._handle_edit_vehicle(v))
        layout.addWidget(edit_btn)

        # Botón Cambiar Estado (Disponible, Alquilado, Taller)
        status_btn = QPushButton("🏷 Estado")
        status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        status_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 7px;
                font-size: 8pt;
                font-weight: 600;
                min-height: 22px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        status_btn.clicked.connect(lambda _, v=vehicle: self._handle_change_status(v))
        layout.addWidget(status_btn)

        # Botón Baja / Eliminar
        del_btn = QPushButton("🗑 Baja")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 4px;
                padding: 4px 7px;
                font-size: 8pt;
                font-weight: 600;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        layout.addWidget(del_btn)

        # Botón Enviar a Taller (Fase 8)
        if vehicle.estado not in (VehicleStatus.ALQUILADO, VehicleStatus.DE_BAJA, VehicleStatus.EN_MANTENIMIENTO):
            workshop_btn = QPushButton("🔧 Taller")
            workshop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            workshop_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(245, 158, 11, 0.2);
                    color: #fbbf24;
                    border: 1px solid rgba(245, 158, 11, 0.4);
                    border-radius: 4px;
                    padding: 4px 7px;
                    font-size: 8pt;
                    font-weight: 600;
                    min-height: 22px;
                }
                QPushButton:hover { background-color: #d97706; color: #ffffff; }
            """)
            workshop_btn.clicked.connect(lambda _, v=vehicle: self._handle_send_to_workshop(v))
            layout.addWidget(workshop_btn)

        return container

    def _handle_send_to_workshop(self, vehicle: Vehicle) -> None:
        """Abre el diálogo de mantenimiento preseleccionando el vehículo."""
        from src.ui.views.maintenance_form_dialog import MaintenanceFormDialog
        dialog = MaintenanceFormDialog(self, preselected_vehicle_id=vehicle.id_vehiculo)
        if dialog.exec():
            self.load_data()

    def _handle_new_vehicle(self) -> None:
        """Abre el diálogo modal de alta de vehículo."""
        dialog = VehicleFormDialog(self, vehicle=None)
        if dialog.exec():
            self.load_data()

    def _handle_edit_vehicle(self, vehicle: Vehicle) -> None:
        """Abre el diálogo modal de edición del vehículo seleccionado."""
        try:
            fresh_vehicle = vehicle_service.get_vehicle(vehicle.id_vehiculo)
            dialog = VehicleFormDialog(self, vehicle=fresh_vehicle)
            if dialog.exec():
                self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el vehículo: {e}")

    def _handle_change_status(self, vehicle: Vehicle) -> None:
        """Abre el diálogo modal especializado para transicionar el estado del vehículo."""
        try:
            fresh_vehicle = vehicle_service.get_vehicle(vehicle.id_vehiculo)
            dialog = VehicleStatusDialog(self, vehicle=fresh_vehicle)
            if dialog.exec():
                self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al abrir diálogo de estado: {e}")

    def _handle_row_double_click(self, row: int, column: int) -> None:
        """Doble clic en fila abre la ficha de edición."""
        item_id = self.table.item(row, 0)
        if item_id:
            v_id = int(item_id.text())
            veh = next((v for v in self._vehicles_cache if v.id_vehiculo == v_id), None)
            if veh:
                self._handle_edit_vehicle(veh)

    def _handle_delete_vehicle(self, vehicle: Vehicle) -> None:
        """Solicita confirmación y ejecuta la baja o eliminación del vehículo."""
        reply = QMessageBox.question(
            self,
            "Confirmar Baja de Vehículo",
            f"¿Desea dar de baja o retirar el vehículo placa '{vehicle.placa}' ({vehicle.modelo_nombre}) de la flota activa?\n\n"
            "Si el vehículo posee historial de alquileres o mantenimientos, pasará automáticamente a estado 'DE_BAJA'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                vehicle_service.delete_vehicle(vehicle.id_vehiculo, force_soft_delete=True)
                QMessageBox.information(
                    self,
                    "Flota Actualizada",
                    f"El vehículo '{vehicle.placa}' fue retirado satisfactoriamente de la flota activa.",
                )
                self.load_data()
            except AppException as e:
                QMessageBox.warning(self, "Acción Bloqueada", e.message)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al procesar baja de vehículo: {e}")
