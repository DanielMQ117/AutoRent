"""Diálogo modal para el alta y edición técnica de Vehículos de la flota."""

from decimal import Decimal
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import VehicleStatus
from src.domain.models import Brand, Vehicle, VehicleCategory, VehicleModel
from src.services.vehicle_service import vehicle_service

logger = get_logger(__name__)


class VehicleFormDialog(QDialog):
    """Formulario modal para registrar o modificar datos de un vehículo en la flota."""

    def __init__(self, parent: Optional[QWidget] = None, vehicle: Optional[Vehicle] = None) -> None:
        super().__init__(parent)
        self.vehicle = vehicle
        self.is_edit_mode = vehicle is not None

        self._brands_cache: List[Brand] = []
        self._models_cache: List[VehicleModel] = []
        self._categories_cache: List[VehicleCategory] = []

        self._init_ui()
        self._load_catalogs()
        if self.is_edit_mode:
            self._load_vehicle_data()

    def _init_ui(self) -> None:
        """Configura la interfaz gráfica del diálogo modal."""
        title = "Editar Ficha de Vehículo" if self.is_edit_mode else "Registrar Nuevo Vehículo"
        self.setWindowTitle(f"AutoRent Pro — {title}")
        self.resize(680, 720)
        self.setMinimumSize(620, 640)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # 1. Cabecera
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel(title)
        header_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #38bdf8;")

        header_desc = QLabel(
            "Ingrese las especificaciones técnicas y operativas de la unidad vehicular."
        )
        header_desc.setFont(QFont("Segoe UI", 9))
        header_desc.setStyleSheet("color: #94a3b8;")

        header_layout.addWidget(header_title)
        header_layout.addWidget(header_desc)
        main_layout.addLayout(header_layout)

        # 2. Banner de Error
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Segoe UI", 9))
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 8px 12px;
        """)
        self.error_label.hide()
        main_layout.addWidget(self.error_label)

        # 3. Área de Scroll
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Card 1: Identificación y Modelo
        card_specs = self._create_card("1. Especificación de Marca, Modelo y Categoría")
        grid_specs = QGridLayout()
        grid_specs.setSpacing(12)
        grid_specs.setColumnStretch(0, 0)
        grid_specs.setColumnStretch(1, 1)

        # Marca
        grid_specs.addWidget(self._create_field_label("Marca del Fabricante *"), 0, 0)
        self.marca_combo = QComboBox()
        self.marca_combo.currentIndexChanged.connect(self._on_brand_changed)
        self._style_input(self.marca_combo)
        grid_specs.addWidget(self.marca_combo, 0, 1)

        # Modelo
        grid_specs.addWidget(self._create_field_label("Modelo de Vehículo *"), 1, 0)
        self.modelo_combo = QComboBox()
        self._style_input(self.modelo_combo)
        grid_specs.addWidget(self.modelo_combo, 1, 1)

        # Categoría Tarifaria
        grid_specs.addWidget(self._create_field_label("Categoría Tarifaria *"), 2, 0)
        self.categoria_combo = QComboBox()
        self._style_input(self.categoria_combo)
        grid_specs.addWidget(self.categoria_combo, 2, 1)

        card_specs.layout().addLayout(grid_specs)
        container_layout.addWidget(card_specs)

        # Card 2: Identificación Legal y Carrocería
        card_id = self._create_card("2. Identificación Legal y Carrocería")
        grid_id = QGridLayout()
        grid_id.setSpacing(12)
        grid_id.setColumnStretch(0, 0)
        grid_id.setColumnStretch(1, 1)

        # Placa
        grid_id.addWidget(self._create_field_label("Número de Placa *"), 0, 0)
        self.placa_input = QLineEdit()
        self.placa_input.setPlaceholderText("Ej: M-245890")
        self._style_input(self.placa_input)
        grid_id.addWidget(self.placa_input, 0, 1)

        # VIN
        grid_id.addWidget(self._create_field_label("Número de Chasis (VIN - 17 caracteres) *"), 1, 0)
        self.vin_input = QLineEdit()
        self.vin_input.setMaxLength(17)
        self.vin_input.setPlaceholderText("17 caracteres alfanuméricos")
        self._style_input(self.vin_input)
        grid_id.addWidget(self.vin_input, 1, 1)

        # Color
        grid_id.addWidget(self._create_field_label("Color de Carrocería *"), 2, 0)
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Ej: Blanco, Rojo Metálico, Plata")
        self._style_input(self.color_input)
        grid_id.addWidget(self.color_input, 2, 1)

        card_id.layout().addLayout(grid_id)
        container_layout.addWidget(card_id)

        # Card 3: Parámetros Operativos y Estado
        card_ops = self._create_card("3. Parámetros de Operación y Odómetro")
        grid_ops = QGridLayout()
        grid_ops.setSpacing(12)
        grid_ops.setColumnStretch(0, 0)
        grid_ops.setColumnStretch(1, 1)

        # Kilometraje Actual
        grid_ops.addWidget(self._create_field_label("Kilometraje Actual (km) *"), 0, 0)
        self.km_input = QSpinBox()
        self.km_input.setRange(0, 2000000)
        self.km_input.setSingleStep(500)
        self._style_input(self.km_input)
        grid_ops.addWidget(self.km_input, 0, 1)

        # Combustible Actual
        grid_ops.addWidget(self._create_field_label("Nivel de Combustible *"), 1, 0)
        self.fuel_combo = QComboBox()
        self.fuel_combo.addItem("Tanque Lleno (100% - 1.00)", "1.00")
        self.fuel_combo.addItem("Tres Cuartos (75% - 0.75)", "0.75")
        self.fuel_combo.addItem("Medio Tanque (50% - 0.50)", "0.50")
        self.fuel_combo.addItem("Un Cuarto (25% - 0.25)", "0.25")
        self.fuel_combo.addItem("Reserva (10% - 0.10)", "0.10")
        self._style_input(self.fuel_combo)
        grid_ops.addWidget(self.fuel_combo, 1, 1)

        # Próximo Mantenimiento
        grid_ops.addWidget(self._create_field_label("Km Próximo Mantenimiento *"), 2, 0)
        self.km_mant_input = QSpinBox()
        self.km_mant_input.setRange(100, 3000000)
        self.km_mant_input.setValue(5000)
        self.km_mant_input.setSingleStep(1000)
        self._style_input(self.km_mant_input)
        grid_ops.addWidget(self.km_mant_input, 2, 1)

        # Estado Operativo (Disponible, Alquilado, Taller)
        grid_ops.addWidget(self._create_field_label("Estado Operativo *"), 3, 0)
        self.estado_combo = QComboBox()
        self.estado_combo.addItem("DISPONIBLE (Listo para renta)", VehicleStatus.DISPONIBLE.value)
        self.estado_combo.addItem("ALQUILADO (En posesión)", VehicleStatus.ALQUILADO.value)
        self.estado_combo.addItem("EN MANTENIMIENTO (En taller)", VehicleStatus.EN_MANTENIMIENTO.value)
        if self.is_edit_mode:
            self.estado_combo.addItem("DE BAJA (Fuera de flota)", VehicleStatus.DE_BAJA.value)
        self._style_input(self.estado_combo)
        grid_ops.addWidget(self.estado_combo, 3, 1)

        card_ops.layout().addLayout(grid_ops)
        container_layout.addWidget(card_ops)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        # 4. Botones Inferiores
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setFont(QFont("Segoe UI", 9))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Guardar Cambios" if self.is_edit_mode else "Registrar Vehículo")
        self.save_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.save_btn.clicked.connect(self._handle_save)

        btn_bar.addStretch()
        btn_bar.addWidget(self.cancel_btn)
        btn_bar.addWidget(self.save_btn)
        main_layout.addLayout(btn_bar)

    def _create_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f1f5f9; border: none;")
        layout.addWidget(title_lbl)
        return card

    @staticmethod
    def _create_field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl.setStyleSheet("color: #cbd5e1; border: none;")
        return lbl

    @staticmethod
    def _style_input(widget: QWidget) -> None:
        widget.setStyleSheet("""
            QLineEdit, QComboBox, QSpinBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 10px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
                border: 1px solid #334155;
            }
        """)

    def _load_catalogs(self) -> None:
        """Carga marcas, modelos y categorías de persistencia."""
        self._brands_cache = vehicle_service.get_brands()
        self._categories_cache = vehicle_service.get_categories()

        # Poblar marcas
        self.marca_combo.blockSignals(True)
        self.marca_combo.clear()
        for b in self._brands_cache:
            self.marca_combo.addItem(b.nombre, b.id_marca)
        self.marca_combo.blockSignals(False)

        # Poblar categorías
        self.categoria_combo.clear()
        for c in self._categories_cache:
            self.categoria_combo.addItem(f"{c.nombre} (${c.tarifa_base_diaria}/día)", c.id_categoria)

        # Cargar modelos de la primera marca
        if self._brands_cache:
            self._update_models_combo(self._brands_cache[0].id_marca)

    def _on_brand_changed(self) -> None:
        """Actualiza los modelos disponibles al cambiar de marca."""
        brand_id = self.marca_combo.currentData()
        if brand_id:
            self._update_models_combo(brand_id)

    def _update_models_combo(self, brand_id: int) -> None:
        """Puebla el ComboBox de modelos para la marca seleccionada."""
        self._models_cache = vehicle_service.get_models(brand_id)
        self.modelo_combo.clear()
        for m in self._models_cache:
            self.modelo_combo.addItem(f"{m.nombre} ({m.anio} - {m.tipo_transmision})", m.id_modelo)

    def _load_vehicle_data(self) -> None:
        """Carga los datos del vehículo existente para su edición."""
        if not self.vehicle:
            return

        # Encontrar y seleccionar el modelo y la marca asociada
        all_models = vehicle_service.get_models()
        target_model = next((m for m in all_models if m.id_modelo == self.vehicle.id_modelo), None)

        if target_model:
            # Seleccionar marca
            idx_b = self.marca_combo.findData(target_model.id_marca)
            if idx_b >= 0:
                self.marca_combo.setCurrentIndex(idx_b)
                self._update_models_combo(target_model.id_marca)

            # Seleccionar modelo
            idx_m = self.modelo_combo.findData(self.vehicle.id_modelo)
            if idx_m >= 0:
                self.modelo_combo.setCurrentIndex(idx_m)

        # Seleccionar categoría
        idx_c = self.categoria_combo.findData(self.vehicle.id_categoria)
        if idx_c >= 0:
            self.categoria_combo.setCurrentIndex(idx_c)

        self.placa_input.setText(self.vehicle.placa)
        self.vin_input.setText(self.vehicle.vin)
        self.color_input.setText(self.vehicle.color)
        self.km_input.setValue(self.vehicle.kilometraje_actual)
        self.km_mant_input.setValue(self.vehicle.km_proximo_mantenimiento)

        # Nivel de combustible
        fuel_str = f"{float(self.vehicle.nivel_combustible_actual):.2f}"
        idx_f = self.fuel_combo.findData(fuel_str)
        if idx_f >= 0:
            self.fuel_combo.setCurrentIndex(idx_f)

        # Estado
        idx_s = self.estado_combo.findData(self.vehicle.estado.value)
        if idx_s >= 0:
            self.estado_combo.setCurrentIndex(idx_s)

    def _handle_save(self) -> None:
        """Valida y guarda los datos a través del servicio empresarial."""
        self.error_label.hide()

        id_modelo = self.modelo_combo.currentData()
        id_categoria = self.categoria_combo.currentData()
        placa = self.placa_input.text().strip().upper()
        vin = self.vin_input.text().strip().upper()
        color = self.color_input.text().strip()
        km_actual = self.km_input.value()
        fuel_val = Decimal(self.fuel_combo.currentData())
        km_proximo = self.km_mant_input.value()
        estado = VehicleStatus(self.estado_combo.currentData())

        if not id_modelo:
            self.error_label.setText("⚠ Debe seleccionar un modelo de vehículo válido.")
            self.error_label.show()
            return

        if not id_categoria:
            self.error_label.setText("⚠ Debe seleccionar una categoría vehicular.")
            self.error_label.show()
            return

        try:
            if self.is_edit_mode and self.vehicle:
                self.vehicle.id_modelo = id_modelo
                self.vehicle.id_categoria = id_categoria
                self.vehicle.placa = placa
                self.vehicle.vin = vin
                self.vehicle.color = color
                self.vehicle.kilometraje_actual = km_actual
                self.vehicle.nivel_combustible_actual = fuel_val
                self.vehicle.km_proximo_mantenimiento = km_proximo
                self.vehicle.estado = estado

                vehicle_service.update_vehicle(self.vehicle)
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Ficha técnica del vehículo placa '{self.vehicle.placa}' actualizada correctamente.",
                )
            else:
                new_v = Vehicle(
                    id_modelo=id_modelo,
                    id_categoria=id_categoria,
                    placa=placa,
                    vin=vin,
                    color=color,
                    kilometraje_actual=km_actual,
                    nivel_combustible_actual=fuel_val,
                    km_proximo_mantenimiento=km_proximo,
                    estado=estado,
                    activo=True,
                )
                created = vehicle_service.create_vehicle(new_v)
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Vehículo placa '{created.placa}' ({created.modelo_nombre}) ingresado a la flota exitosamente.",
                )

            self.accept()

        except AppException as e:
            self.error_label.setText(f"⚠ {e.message}")
            self.error_label.show()
        except Exception as e:
            logger.error("Error inesperado en formulario de vehículo: %s", e)
            self.error_label.setText(f"Error del servidor: {e}")
            self.error_label.show()
