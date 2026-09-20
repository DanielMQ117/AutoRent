"""Diálogo modal para la Finalización de Mantenimiento y Reactivación de Vehículo (RF-33)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
from src.domain.models import Maintenance
from src.services.maintenance_service import maintenance_service

logger = get_logger(__name__)


class MaintenanceCompleteDialog(QDialog):
    """Formulario modal para auditar costos finales, reprogramar próximo servicio y reactivar vehículo a DISPONIBLE."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        maintenance: Optional[Maintenance] = None,
    ) -> None:
        super().__init__(parent)
        if not maintenance:
            raise ValueError("Se requiere una orden de mantenimiento válida.")
        self.maintenance = maintenance

        self._init_ui()
        self._populate_data()

    @staticmethod
    def _create_section_card(title_text: str, accent_color: str = "#38bdf8") -> tuple[QFrame, QVBoxLayout]:
        """Crea una tarjeta contenedora (QFrame) con el título DENTRO del rectángulo delimitador."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(14)

        title_lbl = QLabel(title_text)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {accent_color};
                background: transparent;
                border: none;
                padding: 0px 0px 2px 0px;
            }}
        """)
        card_layout.addWidget(title_lbl)

        return card, card_layout

    @staticmethod
    def _create_field_label(text: str) -> QLabel:
        """Etiqueta estándar para campos de formulario interactivos."""
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl.setStyleSheet("color: #cbd5e1; background: transparent; border: none;")
        return lbl

    @staticmethod
    def _create_metric_label(text: str) -> QLabel:
        """Etiqueta estándar para títulos de métricas e informaciones."""
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        lbl.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        return lbl

    def _init_ui(self) -> None:
        """Configura la interfaz gráfica del diálogo modal."""
        self.setWindowTitle("AutoRent Pro — Finalizar Orden de Mantenimiento")
        self.resize(700, 740)
        self.setMinimumSize(640, 660)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # 1. Encabezado
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        header_title = QLabel("✓ Salida de Taller y Reactivación de Flota")
        header_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #34d399; background: transparent; border: none;")

        header_desc = QLabel(
            "Ingrese el costo final real auditado y reprograme el odómetro del próximo servicio para liberar la unidad a 'DISPONIBLE'."
        )
        header_desc.setFont(QFont("Segoe UI", 9))
        header_desc.setStyleSheet("color: #94a3b8; background: transparent; border: none;")

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
            padding: 8px 14px;
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

        # SECCIÓN 1: Ficha de la Orden en Taller
        sec1_frame, sec1_layout = self._create_section_card(
            "1. 📋 Resumen de la Orden de Servicio", "#38bdf8"
        )

        grid1 = QGridLayout()
        grid1.setContentsMargins(0, 0, 0, 0)
        grid1.setHorizontalSpacing(16)
        grid1.setVerticalSpacing(10)
        grid1.setColumnStretch(0, 0)
        grid1.setColumnStretch(1, 1)
        grid1.setColumnStretch(2, 0)
        grid1.setColumnStretch(3, 1)

        grid1.addWidget(self._create_metric_label("Orden ID:"), 0, 0)
        self.lbl_id = QLabel(f"#{self.maintenance.id_mantenimiento}")
        self.lbl_id.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_id.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        grid1.addWidget(self.lbl_id, 0, 1)

        grid1.addWidget(self._create_metric_label("Vehículo:"), 0, 2)
        self.lbl_vehiculo = QLabel(
            f"{self.maintenance.vehiculo_placa or ''} — {self.maintenance.vehiculo_modelo or ''}"
        )
        self.lbl_vehiculo.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_vehiculo.setStyleSheet("color: #38bdf8; background: transparent; border: none;")
        grid1.addWidget(self.lbl_vehiculo, 0, 3)

        grid1.addWidget(self._create_metric_label("Taller:"), 1, 0)
        self.lbl_taller = QLabel(self.maintenance.taller_servicio)
        self.lbl_taller.setFont(QFont("Segoe UI", 9))
        self.lbl_taller.setStyleSheet("color: #cbd5e1; background: transparent; border: none;")
        grid1.addWidget(self.lbl_taller, 1, 1)

        grid1.addWidget(self._create_metric_label("Tipo:"), 1, 2)
        self.lbl_tipo = QLabel(self.maintenance.tipo_mantenimiento.value)
        self.lbl_tipo.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_tipo.setStyleSheet("color: #fbbf24; background: transparent; border: none;")
        grid1.addWidget(self.lbl_tipo, 1, 3)

        grid1.addWidget(self._create_metric_label("Fecha Ingreso:"), 2, 0)
        f_ing_str = self.maintenance.fecha_ingreso.strftime("%Y-%m-%d %H:%M") if self.maintenance.fecha_ingreso else "—"
        self.lbl_ingreso = QLabel(f_ing_str)
        self.lbl_ingreso.setFont(QFont("Segoe UI", 9))
        self.lbl_ingreso.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        grid1.addWidget(self.lbl_ingreso, 2, 1)

        grid1.addWidget(self._create_metric_label("Odómetro Ingreso:"), 2, 2)
        self.lbl_km_in = QLabel(f"{self.maintenance.kilometraje_entrada:,} km")
        self.lbl_km_in.setFont(QFont("Segoe UI", 9))
        self.lbl_km_in.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        grid1.addWidget(self.lbl_km_in, 2, 3)

        sec1_layout.addLayout(grid1)
        container_layout.addWidget(sec1_frame)

        # SECCIÓN 2: Cierre Económico y Fechas Reales
        sec2_frame, sec2_layout = self._create_section_card(
            "2. 💰 Liquidación de Costos y Tiempo Real", "#34d399"
        )

        grid2 = QGridLayout()
        grid2.setContentsMargins(0, 0, 0, 0)
        grid2.setHorizontalSpacing(16)
        grid2.setVerticalSpacing(12)
        grid2.setColumnStretch(0, 0)
        grid2.setColumnStretch(1, 1)

        # Fecha y Hora Real de Salida
        grid2.addWidget(self._create_field_label("Fecha y Hora de Salida Real: *"), 0, 0)
        self.datetime_salida_real = QDateTimeEdit()
        self.datetime_salida_real.setCalendarPopup(True)
        self.datetime_salida_real.setDateTime(QDateTime.currentDateTime())
        self.datetime_salida_real.setStyleSheet(self._input_style())
        grid2.addWidget(self.datetime_salida_real, 0, 1)

        # Costo Total Final Real
        grid2.addWidget(self._create_field_label("Costo Total Final Real ($): *"), 1, 0)
        self.spin_costo_final = QDoubleSpinBox()
        self.spin_costo_final.setRange(0.00, 999999.99)
        self.spin_costo_final.setDecimals(2)
        self.spin_costo_final.setPrefix("$ ")
        self.spin_costo_final.setStyleSheet(self._input_style())
        grid2.addWidget(self.spin_costo_final, 1, 1)

        # Reprogramación de Próximo Mantenimiento (RF-33)
        grid2.addWidget(self._create_field_label("Reprogramar Próximo Mantenimiento: *"), 2, 0)
        self.spin_nuevo_km_maint = QSpinBox()
        self.spin_nuevo_km_maint.setRange(0, 9999999)
        self.spin_nuevo_km_maint.setSuffix(" km")
        self.spin_nuevo_km_maint.setStyleSheet(self._input_style())
        grid2.addWidget(self.spin_nuevo_km_maint, 2, 1)

        sec2_layout.addLayout(grid2)
        container_layout.addWidget(sec2_frame)

        # SECCIÓN 3: Trabajos Finales y Conformidad
        sec3_frame, sec3_layout = self._create_section_card(
            "3. 🛠️ Informe de Recepción y Conformidad Técnica", "#fbbf24"
        )

        sec3_layout.addWidget(self._create_field_label("Detalle de los trabajos concluidos y prueba de ruta: *"))

        self.txt_notas_finales = QTextEdit()
        self.txt_notas_finales.setPlaceholderText(
            "Detalle de los trabajos concluidos, repuestos instalados y prueba de ruta satisfactoria..."
        )
        self.txt_notas_finales.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Segoe UI';
                font-size: 9pt;
                min-height: 85px;
            }
            QTextEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        sec3_layout.addWidget(self.txt_notas_finales)
        container_layout.addWidget(sec3_frame)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # 4. Botones de Acción
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFont(QFont("Segoe UI", 9))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 9px 20px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_complete = QPushButton("✓ Finalizar y Reactivar Vehículo")
        self.btn_complete.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_complete.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 9px 24px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
            QPushButton:pressed {
                background-color: #065f46;
            }
        """)
        self.btn_complete.clicked.connect(self._complete_order)

        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_cancel)
        actions_layout.addWidget(self.btn_complete)
        main_layout.addLayout(actions_layout)

    def _input_style(self) -> str:
        return """
            QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
                font-family: 'Segoe UI';
                font-size: 9pt;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {
                border: 1px solid #38bdf8;
            }
        """

    def _populate_data(self) -> None:
        """Carga los valores por defecto en los controles del formulario."""
        # Pre-cargar costo estimado
        self.spin_costo_final.setValue(float(self.maintenance.costo_total or Decimal("0.00")))

        # Calcular sugerencia para próximo mantenimiento: odómetro entrada + 5,000 km
        km_sugerido = self.maintenance.kilometraje_entrada + 5000
        self.spin_nuevo_km_maint.setValue(km_sugerido)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(f"⚠ {message}")
        self.error_label.show()

    def _complete_order(self) -> None:
        """Ejecuta la finalización de la orden y liberación de la unidad."""
        self.error_label.hide()

        salida_real = self.datetime_salida_real.dateTime().toPython()
        costo_final = Decimal(str(self.spin_costo_final.value()))
        nuevo_km_maint = self.spin_nuevo_km_maint.value()
        notas = self.txt_notas_finales.toPlainText().strip()

        if nuevo_km_maint <= self.maintenance.kilometraje_entrada:
            self._show_error(
                f"El nuevo kilometraje para el próximo servicio ({nuevo_km_maint:,} km) "
                f"debe ser superior al kilometraje registrado al ingresar ({self.maintenance.kilometraje_entrada:,} km)."
            )
            self.spin_nuevo_km_maint.setFocus()
            return

        try:
            maintenance_service.complete_maintenance(
                id_mantenimiento=self.maintenance.id_mantenimiento,
                fecha_salida_real=salida_real,
                costo_total=costo_final,
                nuevo_km_proximo_mantenimiento=nuevo_km_maint,
                notas_cierre=notas,
            )

            QMessageBox.information(
                self,
                "Mantenimiento Concluido Exitosamente",
                f"La orden #{self.maintenance.id_mantenimiento} ha sido cerrada como FINALIZADA.\n\n"
                f"• Costo Final Auditado: ${costo_final:,.2f}\n"
                f"• Nuevo Umbral Próximo Servicio: {nuevo_km_maint:,} km\n"
                f"• Estado Vehicular: RESTAURADO A 'DISPONIBLE'",
            )
            self.accept()

        except AppException as e:
            self._show_error(e.message)
        except Exception as e:
            logger.exception("Error al finalizar orden de mantenimiento")
            self._show_error(f"Error inesperado: {str(e)}")
