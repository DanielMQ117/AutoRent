"""Diálogo modal especializado para la gestión de estados operativos de vehículos."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import VehicleStatus
from src.domain.models import Vehicle
from src.services.vehicle_service import vehicle_service
from src.ui.components.badges import get_vehicle_status_badge

logger = get_logger(__name__)


class VehicleStatusDialog(QDialog):
    """Diálogo modal para cambiar el estado operativo de un vehículo (Disponible, Alquilado, Taller)."""

    def __init__(self, parent: Optional[QWidget] = None, vehicle: Optional[Vehicle] = None) -> None:
        super().__init__(parent)
        if not vehicle:
            raise ValueError("Se requiere una instancia de Vehicle para inicializar este diálogo.")
        self.vehicle = vehicle
        self._init_ui()

    def _init_ui(self) -> None:
        """Inicializa la interfaz del modal de cambio de estado."""
        self.setWindowTitle(f"Gestión de Estado — {self.vehicle.placa}")
        self.resize(520, 480)
        self.setMinimumSize(480, 440)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(16)

        # 1. Cabecera
        header_title = QLabel(f"Actualizar Estado: {self.vehicle.placa}")
        header_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #38bdf8;")

        header_desc = QLabel(f"Vehículo: {self.vehicle.marca_nombre or ''} {self.vehicle.modelo_nombre or ''}")
        header_desc.setFont(QFont("Segoe UI", 10))
        header_desc.setStyleSheet("color: #94a3b8;")

        main_layout.addWidget(header_title)
        main_layout.addWidget(header_desc)

        # 2. Tarjeta con Ficha Actual
        card_info = QFrame()
        card_info.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        info_layout = QHBoxLayout(card_info)
        info_layout.setSpacing(20)

        left_info = QVBoxLayout()
        left_info.addWidget(self._create_info_item("VIN / Chasis", self.vehicle.vin))
        left_info.addWidget(self._create_info_item("Odómetro Actual", f"{self.vehicle.kilometraje_actual:,} km"))
        info_layout.addLayout(left_info)

        right_info = QVBoxLayout()
        status_label = QLabel("Estado Actual:")
        status_label.setFont(QFont("Segoe UI", 9))
        status_label.setStyleSheet("color: #94a3b8; border: none;")
        badge = get_vehicle_status_badge(self.vehicle.estado)
        right_info.addWidget(status_label)
        right_info.addWidget(badge)
        info_layout.addLayout(right_info)

        main_layout.addWidget(card_info)

        # 3. Selección de Nuevo Estado
        selector_card = QFrame()
        selector_card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        selector_layout = QVBoxLayout(selector_card)
        selector_layout.setSpacing(10)

        choose_title = QLabel("Seleccione el nuevo estado operativo:")
        choose_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        choose_title.setStyleSheet("color: #f1f5f9; border: none;")
        selector_layout.addWidget(choose_title)

        self.button_group = QButtonGroup(self)

        # Opciones de estados
        self.rb_disponible = self._create_radio_option(
            VehicleStatus.DISPONIBLE.value,
            "DISPONIBLE",
            "Unidad lista para ser asignada a reservas o contratos de alquiler.",
            "#34d399",
        )
        self.rb_alquilado = self._create_radio_option(
            VehicleStatus.ALQUILADO.value,
            "ALQUILADO",
            "Unidad entregada a un arrendatario (requiere contrato de salida).",
            "#38bdf8",
        )
        self.rb_taller = self._create_radio_option(
            VehicleStatus.EN_MANTENIMIENTO.value,
            "EN MANTENIMIENTO",
            "Unidad enviada a taller mecánico para servicio preventivo o correctivo.",
            "#fbbf24",
        )
        self.rb_baja = self._create_radio_option(
            VehicleStatus.DE_BAJA.value,
            "DE BAJA",
            "Unidad retirada de la flota activa por obsolescencia o pérdida.",
            "#94a3b8",
        )

        self.button_group.addButton(self.rb_disponible, 1)
        self.button_group.addButton(self.rb_alquilado, 2)
        self.button_group.addButton(self.rb_taller, 3)
        self.button_group.addButton(self.rb_baja, 4)

        selector_layout.addWidget(self.rb_disponible)
        selector_layout.addWidget(self.rb_alquilado)
        selector_layout.addWidget(self.rb_taller)
        selector_layout.addWidget(self.rb_baja)

        # Preseleccionar el estado actual
        current = self.vehicle.estado.value
        if current == VehicleStatus.DISPONIBLE.value:
            self.rb_disponible.setChecked(True)
        elif current == VehicleStatus.ALQUILADO.value:
            self.rb_alquilado.setChecked(True)
        elif current == VehicleStatus.EN_MANTENIMIENTO.value:
            self.rb_taller.setChecked(True)
        elif current == VehicleStatus.DE_BAJA.value:
            self.rb_baja.setChecked(True)

        main_layout.addWidget(selector_card)

        # 4. Mensaje de Error
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

        # 5. Botones de Acción
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFont(QFont("Segoe UI", 9))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QPushButton("Confirmar Cambio")
        self.apply_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.apply_btn.clicked.connect(self._handle_apply_change)

        btn_bar.addStretch()
        btn_bar.addWidget(cancel_btn)
        btn_bar.addWidget(self.apply_btn)
        main_layout.addLayout(btn_bar)

    def _create_info_item(self, label: str, val: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color: #94a3b8; border: none;")

        val_lbl = QLabel(val)
        val_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        val_lbl.setStyleSheet("color: #f8fafc; border: none;")

        layout.addWidget(lbl)
        layout.addWidget(val_lbl)
        return widget

    def _create_radio_option(self, value_key: str, title: str, description: str, color: str) -> QRadioButton:
        rb = QRadioButton()
        rb.status_value = value_key
        rb.setCursor(Qt.CursorShape.PointingHandCursor)
        rb.setStyleSheet(f"""
            QRadioButton {{
                color: #f8fafc;
                font-family: 'Segoe UI';
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {color};
                border: 2px solid #ffffff;
                border-radius: 8px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: #0f172a;
                border: 2px solid #475569;
                border-radius: 8px;
            }}
        """)

        # Label con texto descriptivo
        rb.setText(f"{title} — {description}")
        return rb

    def _handle_apply_change(self) -> None:
        """Aplica el cambio de estado mediante el servicio de negocio."""
        self.error_label.hide()
        selected_button = self.button_group.checkedButton()
        if not selected_button:
            return

        target_status_val = selected_button.status_value
        target_status = VehicleStatus(target_status_val)

        if target_status == self.vehicle.estado:
            self.accept()
            return

        try:
            vehicle_service.change_status(self.vehicle.id_vehiculo, target_status)
            QMessageBox.information(
                self,
                "Estado Actualizado",
                f"El estado del vehículo placa '{self.vehicle.placa}' fue actualizado a '{target_status.value}' satisfactoriamente.",
            )
            self.accept()
        except AppException as e:
            self.error_label.setText(f"⚠ {e.message}")
            self.error_label.show()
        except Exception as e:
            logger.error("Error al cambiar estado del vehículo: %s", e)
            self.error_label.setText(f"Error inesperado: {e}")
            self.error_label.show()
