"""Diálogo modal para el registro de Órdenes de Mantenimiento Preventivo y Correctivo (RF-31, RF-32)."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import MaintenanceType, VehicleStatus
from src.domain.models import Maintenance, Vehicle
from src.services.maintenance_service import maintenance_service
from src.services.vehicle_service import vehicle_service

logger = get_logger(__name__)


class MaintenanceFormDialog(QDialog):
    """Formulario modal para abrir una orden de taller mecánico y bloquear el vehículo."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        preselected_vehicle_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.preselected_vehicle_id = preselected_vehicle_id
        self._vehicles_cache: List[Vehicle] = []

        self._init_ui()
        self._load_vehicles()

    def _init_ui(self) -> None:
        """Configura la interfaz gráfica del diálogo modal."""
        self.setWindowTitle("AutoRent Pro — Nueva Orden de Mantenimiento")
        self.resize(680, 720)
        self.setMinimumSize(620, 660)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # 1. Encabezado
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel("🔧 Registro de Entrada a Taller")
        header_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #38bdf8;")

        header_desc = QLabel(
            "Genere una orden de servicio preventivo o correctivo. El vehículo quedará bloqueado en estado 'EN_MANTENIMIENTO'."
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

        # 3. Contenedor Scroll
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)
        container_layout.setContentsMargins(0, 0, 10, 0)

        # SECCIÓN 1: Selección de Vehículo
        sec1_frame = self._create_card_frame()
        sec1_layout = QVBoxLayout(sec1_frame)
        sec1_layout.setSpacing(12)

        sec1_title = QLabel("1. IDENTIFICACIÓN DEL VEHÍCULO")
        sec1_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sec1_title.setStyleSheet("color: #38bdf8; letter-spacing: 0.5px;")
        sec1_layout.addWidget(sec1_title)

        grid1 = QGridLayout()
        grid1.setSpacing(12)

        lbl_veh = QLabel("Vehículo:")
        lbl_veh.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.combo_vehicle = QComboBox()
        self.combo_vehicle.setStyleSheet(self._input_style())
        self.combo_vehicle.currentIndexChanged.connect(self._on_vehicle_selected)
        grid1.addWidget(lbl_veh, 0, 0)
        grid1.addWidget(self.combo_vehicle, 0, 1)

        sec1_layout.addLayout(grid1)

        # Ficha Informativa del Vehículo Seleccionado
        self.vehicle_info_card = QFrame()
        self.vehicle_info_card.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.6);
            border: 1px dashed rgba(56, 189, 248, 0.3);
            border-radius: 6px;
            padding: 10px;
        """)
        info_layout = QHBoxLayout(self.vehicle_info_card)
        self.lbl_info_odometer = QLabel("Odómetro actual: — km")
        self.lbl_info_odometer.setStyleSheet("color: #cbd5e1; font-weight: bold;")
        self.lbl_info_next_maint = QLabel("Próximo servicio: — km")
        self.lbl_info_next_maint.setStyleSheet("color: #fbbf24; font-weight: bold;")
        self.lbl_info_status = QLabel("Estado: —")
        self.lbl_info_status.setStyleSheet("color: #38bdf8; font-weight: bold;")

        info_layout.addWidget(self.lbl_info_odometer)
        info_layout.addWidget(self.lbl_info_next_maint)
        info_layout.addWidget(self.lbl_info_status)
        sec1_layout.addWidget(self.vehicle_info_card)

        container_layout.addWidget(sec1_frame)

        # SECCIÓN 2: Parámetros del Servicio
        sec2_frame = self._create_card_frame()
        sec2_layout = QVBoxLayout(sec2_frame)
        sec2_layout.setSpacing(12)

        sec2_title = QLabel("2. DETALLES Y PROVEEDOR DEL SERVICIO")
        sec2_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sec2_title.setStyleSheet("color: #38bdf8; letter-spacing: 0.5px;")
        sec2_layout.addWidget(sec2_title)

        grid2 = QGridLayout()
        grid2.setSpacing(12)

        # Tipo de Mantenimiento
        lbl_tipo = QLabel("Tipo de Servicio:")
        lbl_tipo.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.combo_tipo = QComboBox()
        self.combo_tipo.setStyleSheet(self._input_style())
        self.combo_tipo.addItem("🛡 PREVENTIVO (Rutina, Aceite, Filtros)", MaintenanceType.PREVENTIVO.value)
        self.combo_tipo.addItem("⚠️ CORRECTIVO (Avería Mecánica, Reparación)", MaintenanceType.CORRECTIVO.value)
        grid2.addWidget(lbl_tipo, 0, 0)
        grid2.addWidget(self.combo_tipo, 0, 1)

        # Taller de Servicio
        lbl_taller = QLabel("Taller / Proveedor:")
        lbl_taller.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.txt_taller = QLineEdit()
        self.txt_taller.setPlaceholderText("Ej. Taller Mecánico Central / AutoTech Express")
        self.txt_taller.setStyleSheet(self._input_style())
        grid2.addWidget(lbl_taller, 1, 0)
        grid2.addWidget(self.txt_taller, 1, 1)

        # Odómetro de Entrada
        lbl_km = QLabel("Kilometraje de Entrada:")
        lbl_km.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.spin_km_entrada = QSpinBox()
        self.spin_km_entrada.setRange(0, 9999999)
        self.spin_km_entrada.setSuffix(" km")
        self.spin_km_entrada.setStyleSheet(self._input_style())
        grid2.addWidget(lbl_km, 2, 0)
        grid2.addWidget(self.spin_km_entrada, 2, 1)

        # Costo Estimado Inicial
        lbl_costo = QLabel("Costo Estimado ($):")
        lbl_costo.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.spin_costo = QDoubleSpinBox()
        self.spin_costo.setRange(0.00, 999999.99)
        self.spin_costo.setDecimals(2)
        self.spin_costo.setPrefix("$ ")
        self.spin_costo.setStyleSheet(self._input_style())
        grid2.addWidget(lbl_costo, 3, 0)
        grid2.addWidget(self.spin_costo, 3, 1)

        # Fecha Estimada de Salida
        lbl_salida = QLabel("Fecha Estimada de Salida:")
        lbl_salida.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.date_salida_estimada = QDateEdit()
        self.date_salida_estimada.setCalendarPopup(True)
        self.date_salida_estimada.setDate(QDate.currentDate().addDays(3))
        self.date_salida_estimada.setStyleSheet(self._input_style())
        grid2.addWidget(lbl_salida, 4, 0)
        grid2.addWidget(self.date_salida_estimada, 4, 1)

        sec2_layout.addLayout(grid2)
        container_layout.addWidget(sec2_frame)

        # SECCIÓN 3: Diagnóstico y Trabajos Solicitados
        sec3_frame = self._create_card_frame()
        sec3_layout = QVBoxLayout(sec3_frame)
        sec3_layout.setSpacing(12)

        sec3_title = QLabel("3. DIAGNÓSTICO Y DESCRIPCIÓN DEL TRABAJO")
        sec3_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sec3_title.setStyleSheet("color: #38bdf8; letter-spacing: 0.5px;")
        sec3_layout.addWidget(sec3_title)

        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setPlaceholderText(
            "Detalle exhaustivo de las tareas a realizar: cambio de aceite y filtros, inspección de frenos, alineación, "
            "o causas de la avería mecánica reportada..."
        )
        self.txt_descripcion.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
                min-height: 90px;
            }
            QTextEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        sec3_layout.addWidget(self.txt_descripcion)
        container_layout.addWidget(sec3_frame)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # 4. Botones de Acción
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFont(QFont("Segoe UI", 10))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 9px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("🔧 Registrar Orden y Enviar a Taller")
        self.btn_save.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 9px 24px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_save.clicked.connect(self._save_order)

        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_cancel)
        actions_layout.addWidget(self.btn_save)
        main_layout.addLayout(actions_layout)

    def _create_card_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        return frame

    def _input_style(self) -> str:
        return """
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """

    def _load_vehicles(self) -> None:
        """Carga la lista de vehículos elegibles en el combo."""
        try:
            self._vehicles_cache = maintenance_service.get_eligible_vehicles_for_maintenance()
            self.combo_vehicle.clear()

            if not self._vehicles_cache:
                self.combo_vehicle.addItem("No hay vehículos disponibles para taller", None)
                self.btn_save.setEnabled(False)
                return

            target_index = 0
            for idx, veh in enumerate(self._vehicles_cache):
                texto = f"{veh.placa} — {veh.marca_nombre} {veh.modelo_nombre} ({veh.categoria_nombre}) [{veh.estado.value}]"
                self.combo_vehicle.addItem(texto, veh.id_vehiculo)
                if self.preselected_vehicle_id and veh.id_vehiculo == self.preselected_vehicle_id:
                    target_index = idx

            self.combo_vehicle.setCurrentIndex(target_index)
            self._on_vehicle_selected(target_index)

        except AppException as e:
            self._show_error(f"Error al cargar vehículos: {e.message}")

    def _on_vehicle_selected(self, index: int) -> None:
        """Actualiza los datos auxiliares al seleccionar un vehículo."""
        if index < 0 or index >= len(self._vehicles_cache):
            return

        veh = self._vehicles_cache[index]
        self.lbl_info_odometer.setText(f"Odómetro actual: {veh.kilometraje_actual:,} km")
        self.lbl_info_next_maint.setText(f"Próximo servicio: {veh.km_proximo_mantenimiento:,} km")
        self.lbl_info_status.setText(f"Estado actual: {veh.estado.value}")

        self.spin_km_entrada.setValue(veh.kilometraje_actual)

        # Si el odómetro ya superó el umbral de servicio, sugerir PREVENTIVO
        if veh.kilometraje_actual >= veh.km_proximo_mantenimiento:
            self.combo_tipo.setCurrentIndex(0)  # PREVENTIVO
            self.lbl_info_next_maint.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.lbl_info_next_maint.setText(f"Próximo servicio: {veh.km_proximo_mantenimiento:,} km (¡VENCIDO!)")
        else:
            self.lbl_info_next_maint.setStyleSheet("color: #fbbf24; font-weight: bold;")

    def _show_error(self, message: str) -> None:
        self.error_label.setText(f"⚠ {message}")
        self.error_label.show()

    def _save_order(self) -> None:
        """Valida y guarda la orden de mantenimiento."""
        self.error_label.hide()

        v_idx = self.combo_vehicle.currentIndex()
        if v_idx < 0 or v_idx >= len(self._vehicles_cache):
            self._show_error("Debe seleccionar un vehículo válido.")
            return

        veh = self._vehicles_cache[v_idx]
        tipo_str = self.combo_tipo.currentData()
        taller = self.txt_taller.text().strip()
        km_in = self.spin_km_entrada.value()
        costo = Decimal(str(self.spin_costo.value()))
        fecha_salida = self.date_salida_estimada.date().toPython()
        descripcion = self.txt_descripcion.toPlainText().strip()

        if not taller:
            self._show_error("Debe especificar el nombre o razón social del taller mecánico.")
            self.txt_taller.setFocus()
            return

        if not descripcion:
            self._show_error("Debe ingresar la descripción de los trabajos o diagnóstico.")
            self.txt_descripcion.setFocus()
            return

        try:
            m_order = Maintenance(
                id_vehiculo=veh.id_vehiculo,
                tipo_mantenimiento=MaintenanceType(tipo_str),
                fecha_ingreso=datetime.now(),
                fecha_salida_estimada=fecha_salida,
                kilometraje_entrada=km_in,
                taller_servicio=taller,
                descripcion_trabajo=descripcion,
                costo_total=costo,
            )

            maintenance_service.create_maintenance_order(m_order)

            QMessageBox.information(
                self,
                "Orden Registrada con Éxito",
                f"El vehículo con placa '{veh.placa}' ha ingresado a taller satisfactoriamente.\n\n"
                f"• Proveedor: {taller}\n"
                f"• Tipo: {tipo_str}\n"
                f"• Estado vehicular: BLOQUEADO (EN_MANTENIMIENTO)",
            )
            self.accept()

        except AppException as e:
            self._show_error(e.message)
        except Exception as e:
            logger.exception("Error inesperado al registrar orden de mantenimiento")
            self._show_error(f"Error inesperado: {str(e)}")
