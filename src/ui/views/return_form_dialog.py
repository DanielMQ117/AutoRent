"""Diálogo modal para la Recepción Física, Inspección de Daños y Liquidación Final (Fase 6)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.core.logger import get_logger
from src.domain.enums import (
    ContractStatus,
    DamageSeverity,
    DamageType,
    PaymentMethod,
    PaymentType,
    SettlementStatus,
)
from src.domain.models import Contract, Damage, ReturnInspection, Settlement
from src.services.contract_service import contract_service
from src.services.return_service import return_service

logger = get_logger(__name__)


class ReturnFormDialog(QDialog):
    """Formulario interactivo para registrar la devolución física, inspección y liquidación final."""

    def __init__(
        self,
        contract: Contract,
        return_inspection: Optional[ReturnInspection] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.contract = contract
        self.return_inspection = return_inspection
        self.is_view_mode = contract.estado == ContractStatus.LIQUIDADO or return_inspection is not None
        self.damages_list: List[Damage] = []

        if self.return_inspection and self.return_inspection.danios:
            self.damages_list = list(self.return_inspection.danios)

        self._init_ui()
        if not self.is_view_mode:
            self._recalculate_liquidation()

    def _init_ui(self) -> None:
        """Configura la estructura gráfica del diálogo."""
        mode_text = "Auditoría de Devolución" if self.is_view_mode else "Recepción e Inspección de Retorno"
        self.setWindowTitle(f"AutoRent Pro — {mode_text} ({self.contract.codigo_contrato})")
        self.resize(940, 860)
        self.setMinimumSize(860, 760)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Cabecera Informativa del Contrato
        header_card = self._create_header_card()
        main_layout.addWidget(header_card)

        # 2. Área desplazable para las secciones del formulario
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)

        # Sección: Retorno Físico & Odómetro
        scroll_layout.addWidget(self._create_physical_inspection_box())

        # Sección: Registro de Averías / Daños Físicos
        scroll_layout.addWidget(self._create_damages_box())

        # Sección: Resumen Financiero y Liquidación en Vivo
        scroll_layout.addWidget(self._create_settlement_preview_card())

        # Sección: Cierre Contable y Método de Pago
        scroll_layout.addWidget(self._create_payment_closing_box())

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

        # 3. Botones de Acción Inferiores
        main_layout.addLayout(self._create_bottom_actions())

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
        """Etiqueta estándar para títulos de métricas financieras e informativas."""
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        lbl.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        return lbl

    def _create_header_card(self) -> QFrame:
        """Crea la tarjeta resumen con los datos de entrega del contrato."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-left: 4px solid #38bdf8;
                border-radius: 8px;
            }
        """)
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 14, 18, 14)
        grid.setSpacing(10)

        title = QLabel(f"CONTRATO: {self.contract.codigo_contrato}")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8; background: transparent; border: none;")
        grid.addWidget(title, 0, 0, 1, 2)

        cliente_info = f"👤 Cliente: {self.contract.cliente_nombre or 'N/A'} (Doc: {self.contract.cliente_identificacion or 'N/A'})"
        lbl_cliente = QLabel(cliente_info)
        lbl_cliente.setFont(QFont("Segoe UI", 9))
        lbl_cliente.setStyleSheet("color: #e2e8f0; background: transparent; border: none;")
        grid.addWidget(lbl_cliente, 1, 0)

        veh_info = f"🚗 Vehículo: {self.contract.vehiculo_placa or 'N/A'} — {self.contract.vehiculo_modelo or 'N/A'}"
        lbl_veh = QLabel(veh_info)
        lbl_veh.setFont(QFont("Segoe UI", 9))
        lbl_veh.setStyleSheet("color: #e2e8f0; background: transparent; border: none;")
        grid.addWidget(lbl_veh, 1, 1)

        fecha_salida_str = self.contract.fecha_hora_salida_real.strftime("%d/%m/%Y %H:%M") if self.contract.fecha_hora_salida_real else "N/A"
        fecha_fin_str = self.contract.fecha_hora_fin_pactada.strftime("%d/%m/%Y %H:%M") if self.contract.fecha_hora_fin_pactada else "N/A"
        tiempo_info = f"📅 Salida: {fecha_salida_str}  ➔  Fin Pactado: {fecha_fin_str}"
        lbl_tiempo = QLabel(tiempo_info)
        lbl_tiempo.setFont(QFont("Segoe UI", 9))
        lbl_tiempo.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        grid.addWidget(lbl_tiempo, 2, 0)

        comb_salida_pct = int(self.contract.combustible_salida * 100)
        condiciones_salida = (
            f"Odómetro Salida: {self.contract.kilometraje_salida:,} km | "
            f"Combustible Salida: {comb_salida_pct}% | "
            f"Garantía Retenida: ${self.contract.monto_garantia:,.2f}"
        )
        lbl_cond = QLabel(condiciones_salida)
        lbl_cond.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        lbl_cond.setStyleSheet("color: #34d399; background: transparent; border: none;")
        grid.addWidget(lbl_cond, 2, 1)

        return card

    def _create_physical_inspection_box(self) -> QFrame:
        """Crea el bloque de controles para la recepción física."""
        card, card_layout = self._create_section_card(
            "1. 🔍 Inspección Física de Retorno (Check-out)", "#38bdf8"
        )

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        # Fecha de Retorno Real
        grid.addWidget(self._create_field_label("Fecha y Hora Real de Devolución: *"), 0, 0)
        self.retorno_dt_edit = QDateTimeEdit()
        self.retorno_dt_edit.setCalendarPopup(True)
        self.retorno_dt_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        if self.return_inspection and self.return_inspection.fecha_hora_retorno_real:
            self.retorno_dt_edit.setDateTime(self.return_inspection.fecha_hora_retorno_real)
        else:
            self.retorno_dt_edit.setDateTime(datetime.now())
        self._style_input(self.retorno_dt_edit)
        self.retorno_dt_edit.dateTimeChanged.connect(self._recalculate_liquidation)
        grid.addWidget(self.retorno_dt_edit, 0, 1)

        # Odómetro de Retorno
        grid.addWidget(self._create_field_label("Odómetro de Retorno: *"), 0, 2)
        self.odometro_input = QSpinBox()
        self.odometro_input.setRange(self.contract.kilometraje_salida, 9999999)
        if self.return_inspection:
            self.odometro_input.setValue(self.return_inspection.kilometraje_retorno)
        else:
            self.odometro_input.setValue(self.contract.kilometraje_salida)
        self.odometro_input.setSuffix(" km")
        self._style_input(self.odometro_input)
        self.odometro_input.valueChanged.connect(self._recalculate_liquidation)
        grid.addWidget(self.odometro_input, 0, 3)

        # Nivel de Combustible de Retorno
        grid.addWidget(self._create_field_label("Nivel de Combustible Devuelto: *"), 1, 0)
        self.combustible_combo = QComboBox()
        self.combustible_combo.addItem("1.00 (Tanque Lleno - 100%)", Decimal("1.00"))
        self.combustible_combo.addItem("0.75 (3/4 Tanque - 75%)", Decimal("0.75"))
        self.combustible_combo.addItem("0.50 (1/2 Tanque - 50%)", Decimal("0.50"))
        self.combustible_combo.addItem("0.25 (1/4 Tanque - 25%)", Decimal("0.25"))
        self.combustible_combo.addItem("0.00 (Vacío - 0%)", Decimal("0.00"))

        if self.return_inspection:
            val = self.return_inspection.combustible_retorno
            idx = self.combustible_combo.findData(val)
            if idx >= 0:
                self.combustible_combo.setCurrentIndex(idx)
        self._style_input(self.combustible_combo)
        self.combustible_combo.currentIndexChanged.connect(self._recalculate_liquidation)
        grid.addWidget(self.combustible_combo, 1, 1)

        # Checklist de Limpieza y Accesorios
        chk_layout = QHBoxLayout()
        chk_layout.setSpacing(18)
        chk_style = """
            QCheckBox {
                color: #cbd5e1;
                font-size: 9pt;
                spacing: 8px;
                background: transparent;
                border: none;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #0f172a;
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """
        self.chk_limpieza = QCheckBox("Limpieza Aprobada")
        self.chk_limpieza.setChecked(self.return_inspection.limpieza_aprobada if self.return_inspection else True)
        self.chk_limpieza.setStyleSheet(chk_style)
        chk_layout.addWidget(self.chk_limpieza)

        self.chk_accesorios = QCheckBox("Accesorios Completos")
        self.chk_accesorios.setChecked(self.return_inspection.accesorios_completos if self.return_inspection else True)
        self.chk_accesorios.setStyleSheet(chk_style)
        chk_layout.addWidget(self.chk_accesorios)
        grid.addLayout(chk_layout, 1, 2, 1, 2)

        # Observaciones
        grid.addWidget(self._create_field_label("Observaciones de Inspección:"), 2, 0)
        self.observaciones_input = QLineEdit()
        self.observaciones_input.setPlaceholderText("Comentarios o anotaciones sobre el estado del vehículo al retorno...")
        if self.return_inspection and self.return_inspection.observaciones:
            self.observaciones_input.setText(self.return_inspection.observaciones)
        self._style_input(self.observaciones_input)
        grid.addWidget(self.observaciones_input, 2, 1, 1, 3)

        card_layout.addLayout(grid)

        if self.is_view_mode:
            self.retorno_dt_edit.setReadOnly(True)
            self.odometro_input.setReadOnly(True)
            self.combustible_combo.setEnabled(False)
            self.chk_limpieza.setEnabled(False)
            self.chk_accesorios.setEnabled(False)
            self.observaciones_input.setReadOnly(True)

        return card

    def _create_damages_box(self) -> QFrame:
        """Crea el bloque para reportar y valorar averías detectadas."""
        card, card_layout = self._create_section_card(
            "2. ⚠️ Registro de Daños Físicos e Incidencias", "#f87171"
        )

        # Controles para agregar daños nuevos
        if not self.is_view_mode:
            dmg_entry_card = QFrame()
            dmg_entry_card.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #334155;
                    border-radius: 6px;
                }
            """)
            dmg_grid = QGridLayout(dmg_entry_card)
            dmg_grid.setContentsMargins(16, 14, 16, 14)
            dmg_grid.setSpacing(10)
            dmg_grid.setColumnStretch(0, 2)
            dmg_grid.setColumnStretch(1, 1)
            dmg_grid.setColumnStretch(2, 1)
            dmg_grid.setColumnStretch(3, 1)

            # Fila 0: Etiquetas
            dmg_grid.addWidget(self._create_field_label("Zona Afectada: *"), 0, 0)
            dmg_grid.addWidget(self._create_field_label("Tipo de Avería: *"), 0, 1)
            dmg_grid.addWidget(self._create_field_label("Gravedad: *"), 0, 2)
            dmg_grid.addWidget(self._create_field_label("Costo Estimado ($): *"), 0, 3)

            # Fila 1: Entradas
            self.dmg_zona_input = QLineEdit()
            self.dmg_zona_input.setPlaceholderText("ej: Parachoques frontal, Puerta der.")
            self._style_input(self.dmg_zona_input)
            dmg_grid.addWidget(self.dmg_zona_input, 1, 0)

            self.dmg_tipo_combo = QComboBox()
            for t in DamageType:
                self.dmg_tipo_combo.addItem(t.value, t)
            self._style_input(self.dmg_tipo_combo)
            dmg_grid.addWidget(self.dmg_tipo_combo, 1, 1)

            self.dmg_grav_combo = QComboBox()
            for g in DamageSeverity:
                self.dmg_grav_combo.addItem(g.value, g)
            self._style_input(self.dmg_grav_combo)
            dmg_grid.addWidget(self.dmg_grav_combo, 1, 2)

            self.dmg_cost_input = QDoubleSpinBox()
            self.dmg_cost_input.setRange(0.00, 10000.00)
            self.dmg_cost_input.setPrefix("$ ")
            self.dmg_cost_input.setValue(0.00)
            self._style_input(self.dmg_cost_input)
            dmg_grid.addWidget(self.dmg_cost_input, 1, 3)

            # Fila 2: Etiquetas Descripción y Botón
            dmg_grid.addWidget(self._create_field_label("Descripción de la Avería / Daño:"), 2, 0, 1, 3)

            # Fila 3: Descripción y Botón de acción
            self.dmg_desc_input = QLineEdit()
            self.dmg_desc_input.setPlaceholderText("Detalles adicionales del daño (ej: Rayón profundo de 15cm con pérdida de pintura)...")
            self._style_input(self.dmg_desc_input)
            dmg_grid.addWidget(self.dmg_desc_input, 3, 0, 1, 3)

            self.dmg_zona_input.returnPressed.connect(self._add_damage)
            self.dmg_desc_input.returnPressed.connect(self._add_damage)

            btn_add_dmg = QPushButton("➕ Agregar Avería")
            btn_add_dmg.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn_add_dmg.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_add_dmg.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 7px 16px;
                }
                QPushButton:hover {
                    background-color: #b91c1c;
                }
            """)
            btn_add_dmg.clicked.connect(self._add_damage)
            dmg_grid.addWidget(btn_add_dmg, 3, 3)

            card_layout.addWidget(dmg_entry_card)

        # Encabezado de la tabla
        lbl_tbl_title = QLabel("📋 Detalle de Averías y Daños Registrados")
        lbl_tbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl_tbl_title.setStyleSheet("color: #cbd5e1; background: transparent; border: none; margin-top: 4px;")
        card_layout.addWidget(lbl_tbl_title)

        # Tabla de daños registrados
        self.damages_table = QTableWidget(0, 5 if self.is_view_mode else 6)
        headers = ["Zona Afectada", "Tipo de Avería", "Gravedad", "Descripción", "Costo Estimado"]
        if not self.is_view_mode:
            headers.append("Acción")
        self.damages_table.setHorizontalHeaderLabels(headers)
        self.damages_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.damages_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.damages_table.horizontalHeader().setStretchLastSection(False)
        self.damages_table.verticalHeader().setVisible(False)
        self.damages_table.verticalHeader().setDefaultSectionSize(36)
        self.damages_table.setColumnWidth(0, 160)  # Zona
        self.damages_table.setColumnWidth(1, 120)  # Tipo
        self.damages_table.setColumnWidth(2, 105)  # Gravedad
        self.damages_table.setColumnWidth(4, 130)  # Costo Reparación
        if not self.is_view_mode:
            self.damages_table.setColumnWidth(5, 85)  # Acción
        self.damages_table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                gridline-color: #1e293b;
                color: #f8fafc;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 7px 8px;
                border: none;
                border-bottom: 1px solid #334155;
                font-weight: bold;
                font-size: 9pt;
            }
        """)
        self.damages_table.setMinimumHeight(130)
        card_layout.addWidget(self.damages_table)
        self._refresh_damages_table()

        return card

    def _create_settlement_preview_card(self) -> QFrame:
        """Crea la tarjeta con el cálculo en vivo de la liquidación financiera."""
        card, card_layout = self._create_section_card(
            "3. 💰 Balance Financiero de Liquidación", "#fbbf24"
        )

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        # Fila 1: Días facturados y subtotal renta
        grid.addWidget(self._create_metric_label("Días Facturados:"), 0, 0)
        self.lbl_dias_fact = QLabel("0 días")
        self.lbl_dias_fact.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_dias_fact.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        grid.addWidget(self.lbl_dias_fact, 0, 1)

        grid.addWidget(self._create_metric_label("Subtotal Renta + Seguro:"), 0, 2)
        self.lbl_subtotal_renta = QLabel("$0.00")
        self.lbl_subtotal_renta.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_subtotal_renta.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        grid.addWidget(self.lbl_subtotal_renta, 0, 3)

        # Fila 2: Penalizaciones (Retraso y Combustible)
        grid.addWidget(self._create_metric_label("Penalización por Retraso:"), 1, 0)
        self.lbl_penal_retraso = QLabel("$0.00 (0 hrs)")
        self.lbl_penal_retraso.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_penal_retraso.setStyleSheet("color: #f87171; background: transparent; border: none;")
        grid.addWidget(self.lbl_penal_retraso, 1, 1)

        grid.addWidget(self._create_metric_label("Penalización Combustible:"), 1, 2)
        self.lbl_penal_comb = QLabel("$0.00 (0% faltante)")
        self.lbl_penal_comb.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_penal_comb.setStyleSheet("color: #f87171; background: transparent; border: none;")
        grid.addWidget(self.lbl_penal_comb, 1, 3)

        # Fila 3: Daños y Total Bruto
        grid.addWidget(self._create_metric_label("Cargos por Daños / Averías:"), 2, 0)
        self.lbl_cargos_danios = QLabel("$0.00")
        self.lbl_cargos_danios.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_cargos_danios.setStyleSheet("color: #f87171; background: transparent; border: none;")
        grid.addWidget(self.lbl_cargos_danios, 2, 1)

        grid.addWidget(self._create_field_label("TOTAL BRUTO A LIQUIDAR:"), 2, 2)
        self.lbl_total_bruto = QLabel("$0.00")
        self.lbl_total_bruto.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_total_bruto.setStyleSheet("color: #f8fafc; background: transparent; border: none;")
        grid.addWidget(self.lbl_total_bruto, 2, 3)

        card_layout.addLayout(grid)

        # Separador horizontal
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #334155; border: none; min-height: 1px; max-height: 1px;")
        card_layout.addWidget(sep)

        # Barra inferior: Depósito en Garantía y Saldo Neto
        net_card = QFrame()
        net_card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
            }
        """)
        net_layout = QHBoxLayout(net_card)
        net_layout.setContentsMargins(16, 12, 16, 12)
        net_layout.setSpacing(12)

        lbl_gar = QLabel(f"Depósito en Garantía Retenido: ${self.contract.monto_garantia:,.2f}")
        lbl_gar.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        lbl_gar.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        net_layout.addWidget(lbl_gar)

        net_layout.addStretch()

        self.lbl_saldo_neto = QLabel("SALDO: $0.00")
        self.lbl_saldo_neto.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_saldo_neto.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 6px;
            padding: 6px 16px;
        """)
        net_layout.addWidget(self.lbl_saldo_neto)

        card_layout.addWidget(net_card)
        return card

    def _create_payment_closing_box(self) -> QFrame:
        """Crea el bloque con los datos para liquidar o reembolsar el saldo."""
        card, card_layout = self._create_section_card(
            "4. 💳 Liquidación y Cierre Contable", "#34d399"
        )

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        grid.addWidget(self._create_field_label("Método de Pago / Reembolso: *"), 0, 0)
        self.metodo_pago_combo = QComboBox()
        self.metodo_pago_combo.addItem("Efectivo", PaymentMethod.EFECTIVO)
        self.metodo_pago_combo.addItem("Tarjeta de Crédito", PaymentMethod.TARJETA_CREDITO)
        self.metodo_pago_combo.addItem("Tarjeta de Débito", PaymentMethod.TARJETA_DEBITO)
        self.metodo_pago_combo.addItem("Transferencia Bancaria", PaymentMethod.TRANSFERENCIA)
        self._style_input(self.metodo_pago_combo)
        grid.addWidget(self.metodo_pago_combo, 0, 1)

        grid.addWidget(self._create_field_label("Referencia de Transacción:"), 0, 2)
        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText("N° comprobante o váucher bancario...")
        self._style_input(self.referencia_input)
        grid.addWidget(self.referencia_input, 0, 3)

        lbl_note = QLabel("ℹ️ Nota: Si el balance resulta en reembolso, el depósito restante se devolverá por esta vía. Si existen cargos pendientes, se registrará el cobro.")
        lbl_note.setFont(QFont("Segoe UI", 8))
        lbl_note.setStyleSheet("color: #64748b; background: transparent; border: none; font-style: italic; margin-top: 4px;")
        grid.addWidget(lbl_note, 1, 0, 1, 4)

        card_layout.addLayout(grid)

        if self.is_view_mode:
            self.metodo_pago_combo.setEnabled(False)
            self.referencia_input.setReadOnly(True)

        return card

    def _create_bottom_actions(self) -> QHBoxLayout:
        """Botones de control en la base de la ventana modal."""
        actions = QHBoxLayout()
        actions.setSpacing(12)

        self.btn_cancel = QPushButton("Cerrar" if self.is_view_mode else "Cancelar")
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
        actions.addWidget(self.btn_cancel)

        actions.addStretch()

        if not self.is_view_mode:
            self.btn_liquidar = QPushButton("💾 Procesar Devolución y Liquidar")
            self.btn_liquidar.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.btn_liquidar.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_liquidar.setStyleSheet("""
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
            """)
            self.btn_liquidar.clicked.connect(self._process_return)
            actions.addWidget(self.btn_liquidar)

        return actions

    def _add_damage(self) -> None:
        """Agrega una avería a la lista en memoria."""
        zona = self.dmg_zona_input.text().strip()
        desc = self.dmg_desc_input.text().strip()
        costo = Decimal(str(self.dmg_cost_input.value()))

        if not zona:
            QMessageBox.warning(self, "Campo Requerido", "Especifique la zona de la carrocería afectada (ej: Parachoques, Puerta derecha).")
            self.dmg_zona_input.setFocus()
            return

        if costo <= Decimal("0.00"):
            QMessageBox.warning(self, "Costo Inválido", "El costo estimado de reparación debe ser estrictamente mayor a $0.00.")
            self.dmg_cost_input.setFocus()
            return

        tipo = self.dmg_tipo_combo.currentData()
        gravedad = self.dmg_grav_combo.currentData()

        # Si la descripción está vacía, generar una descriptiva por defecto
        if not desc:
            tipo_txt = tipo.value if hasattr(tipo, "value") else str(tipo)
            desc = f"{tipo_txt.capitalize()} detectado en {zona}"

        danio = Damage(
            zona_carroceria=zona,
            tipo_danio=tipo,
            gravedad=gravedad,
            descripcion=desc,
            costo_reparacion=costo,
        )
        self.damages_list.append(danio)

        # Limpiar inputs de daños y posicionar el foco
        self.dmg_zona_input.clear()
        self.dmg_desc_input.clear()
        self.dmg_cost_input.setValue(0.00)
        self.dmg_zona_input.setFocus()

        self._refresh_damages_table()
        self._recalculate_liquidation()

    def _remove_damage(self, index: int) -> None:
        """Elimina una avería de la lista."""
        if 0 <= index < len(self.damages_list):
            del self.damages_list[index]
            self._refresh_damages_table()
            self._recalculate_liquidation()

    def _refresh_damages_table(self) -> None:
        """Redibuja la tabla de daños."""
        self.damages_table.setRowCount(0)
        for idx, d in enumerate(self.damages_list):
            row = self.damages_table.rowCount()
            self.damages_table.insertRow(row)

            item_zona = QTableWidgetItem(d.zona_carroceria)
            item_zona.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            self.damages_table.setItem(row, 0, item_zona)

            tipo_val = d.tipo_danio.value if hasattr(d.tipo_danio, "value") else str(d.tipo_danio)
            item_tipo = QTableWidgetItem(tipo_val)
            item_tipo.setFont(QFont("Segoe UI", 9))
            self.damages_table.setItem(row, 1, item_tipo)

            grav_val = d.gravedad.value if hasattr(d.gravedad, "value") else str(d.gravedad)
            item_grav = QTableWidgetItem(grav_val)
            item_grav.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            if grav_val == "GRAVE":
                item_grav.setForeground(QColor("#f87171"))
            elif grav_val == "MODERADO":
                item_grav.setForeground(QColor("#fbbf24"))
            else:
                item_grav.setForeground(QColor("#34d399"))
            self.damages_table.setItem(row, 2, item_grav)

            item_desc = QTableWidgetItem(d.descripcion)
            item_desc.setFont(QFont("Segoe UI", 9))
            self.damages_table.setItem(row, 3, item_desc)

            item_cost = QTableWidgetItem(f"${d.costo_reparacion:,.2f}")
            item_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_cost.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_cost.setForeground(QColor("#38bdf8"))
            self.damages_table.setItem(row, 4, item_cost)

            if not self.is_view_mode:
                btn_del = QPushButton("✖ Quitar")
                btn_del.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet("""
                    QPushButton {
                        background-color: #7f1d1d;
                        color: #ffffff;
                        border: none;
                        border-radius: 4px;
                        padding: 3px 8px;
                    }
                    QPushButton:hover {
                        background-color: #991b1b;
                    }
                """)
                btn_del.clicked.connect(lambda _, i=idx: self._remove_damage(i))
                self.damages_table.setCellWidget(row, 5, btn_del)

        if self.damages_table.rowCount() > 0:
            self.damages_table.scrollToBottom()

    def _recalculate_liquidation(self) -> None:
        """Recalcula las cifras de la liquidación en tiempo real ante cualquier cambio."""
        ret_inspection = ReturnInspection(
            id_contrato=self.contract.id_contrato,
            fecha_hora_retorno_real=self.retorno_dt_edit.dateTime().toPython(),
            kilometraje_retorno=self.odometro_input.value(),
            combustible_retorno=self.combustible_combo.currentData() or Decimal("1.00"),
            danios=self.damages_list,
        )

        calc = return_service.calculate_penalties(self.contract, ret_inspection)

        # Actualizar etiquetas
        self.lbl_dias_fact.setText(f"{calc['dias_facturados']} día(s)")
        self.lbl_subtotal_renta.setText(f"${calc['subtotal_renta']:,.2f}")

        horas = calc["horas_retraso"]
        self.lbl_penal_retraso.setText(f"${calc['cargos_retraso']:,.2f} ({horas} hr{'s' if horas != 1 else ''})")

        comb_faltante_pct = int(calc["combustible_faltante"] * 100)
        self.lbl_penal_comb.setText(f"${calc['cargos_combustible']:,.2f} ({comb_faltante_pct}% faltante)")

        self.lbl_cargos_danios.setText(f"${calc['cargos_danios']:,.2f}")
        self.lbl_total_bruto.setText(f"${calc['total_bruto']:,.2f}")

        saldo = calc["saldo_cliente"]
        if saldo < Decimal("0.00"):
            reembolso = abs(saldo)
            self.lbl_saldo_neto.setText(f"✓ REEMBOLSO AL CLIENTE: ${reembolso:,.2f}")
            self.lbl_saldo_neto.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 10pt;
            """)
        elif saldo > Decimal("0.00"):
            self.lbl_saldo_neto.setText(f"⚠ COBRO PENDIENTE AL CLIENTE: ${saldo:,.2f}")
            self.lbl_saldo_neto.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 10pt;
            """)
        else:
            self.lbl_saldo_neto.setText("✓ LIQUIDACIÓN EN EQUILIBRIO: $0.00")
            self.lbl_saldo_neto.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 10pt;
            """)

    def _process_return(self) -> None:
        """Valida y procesa la transacción de liquidación en el backend."""
        # Confirmación del operador
        reply = QMessageBox.question(
            self,
            "Confirmar Liquidación",
            f"¿Está seguro de procesar la devolución y liquidar definitivamente el contrato {self.contract.codigo_contrato}?\n"
            f"El vehículo será reclasificado en flota y se asentará el pago/reembolso correspondiente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ret_inspection = ReturnInspection(
            id_contrato=self.contract.id_contrato,
            fecha_hora_retorno_real=self.retorno_dt_edit.dateTime().toPython(),
            kilometraje_retorno=self.odometro_input.value(),
            combustible_retorno=self.combustible_combo.currentData() or Decimal("1.00"),
            limpieza_aprobada=self.chk_limpieza.isChecked(),
            accesorios_completos=self.chk_accesorios.isChecked(),
            observaciones=self.observaciones_input.text().strip() or None,
            danios=self.damages_list,
        )

        metodo_pago = self.metodo_pago_combo.currentData()
        referencia = self.referencia_input.text().strip() or None

        try:
            result = return_service.process_return_and_settlement(
                id_contrato=self.contract.id_contrato,
                return_data=ret_inspection,
                metodo_pago=metodo_pago,
                referencia_pago=referencia,
            )

            settlement: Settlement = result["settlement"]
            saldo = settlement.saldo_cliente
            msg = f"Contrato {self.contract.codigo_contrato} liquidado exitosamente.\n\n"
            msg += f"• Total Bruto Facturado: ${settlement.total_bruto:,.2f}\n"
            msg += f"• Depósito Aplicado: ${settlement.monto_garantia_aplicado:,.2f}\n"
            if saldo < Decimal("0.00"):
                msg += f"• Reembolso de Garantía Emitido: ${abs(saldo):,.2f}\n"
            elif saldo > Decimal("0.00"):
                msg += f"• Cobro Liquidado al Cliente: ${saldo:,.2f}\n"
            else:
                msg += "• Balance Exacto: $0.00 (Sin diferencias)\n"

            QMessageBox.information(self, "Liquidación Finalizada", msg)
            self.accept()
        except AppException as e:
            QMessageBox.warning(self, "Regla de Negocio Incumplida", str(e))
        except Exception as e:
            logger.exception("Error inesperado al procesar devolución y liquidación.")
            QMessageBox.critical(self, "Error de Sistema", f"Ocurrió un error inesperado:\n{e}")

    @staticmethod
    def _style_input(widget: QWidget) -> None:
        """Aplica estilos consistentes a los controles del formulario."""
        widget.setFont(QFont("Segoe UI", 9))
        widget.setStyleSheet("""
            QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus, QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
            }
        """)
