"""Vista de inicio de sesión con diseño moderno, minimalista y validaciones en tiempo real."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException, AuthenticationError, DatabaseConnectionError, ValidationError
from src.core.logger import get_logger
from src.domain.models import User
from src.services.auth_service import auth_service

logger = get_logger(__name__)


class LoginView(QWidget):
    """Ventana de inicio de sesión moderna y minimalista con soporte Multi-Tenant."""

    # Señal emitida cuando la autenticación es exitosa
    login_success = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._password_visible = False
        self._init_ui()
        self._load_agencies()

    def _init_ui(self) -> None:
        """Inicializa los componentes visuales y estilos del formulario de acceso."""
        self.setWindowTitle("AutoRent Pro — Inicio de Sesión")
        self.resize(480, 680)
        self.setMinimumSize(460, 640)
        self.setStyleSheet("background-color: #0f172a;")  # Fondo oscuro elegante (Slate 900)

        # Layout principal centrado
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Tarjeta contenedora de inicio de sesión
        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(32, 32, 32, 32)

        # 1. Logo / Identificador de la aplicación
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_badge = QLabel("AUTORENT PRO", card)
        brand_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        brand_badge.setStyleSheet("""
            color: #38bdf8;
            background-color: #0c4a6e;
            padding: 5px 14px;
            border-radius: 4px;
            border: none;
        """)
        brand_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("Iniciar Sesión", card)
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc; border: none; margin-top: 4px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Ingrese sus credenciales de acceso", card)
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet("color: #94a3b8; border: none;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(brand_badge)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        card_layout.addLayout(header_layout)

        # 2. Mensaje de Alerta / Error visual
        self.error_label = QLabel("", card)
        self.error_label.setFont(QFont("Segoe UI", 9))
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 8px 12px;
        """)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        # 2.5. Selector de Agencia / Sucursal (Multi-Tenant)
        agency_field_layout = QVBoxLayout()
        agency_field_layout.setSpacing(6)

        agency_title = QLabel("Agencia / Sucursal", card)
        agency_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        agency_title.setStyleSheet("color: #cbd5e1; border: none;")

        self.agency_combo = QComboBox(card)
        self.agency_combo.setFont(QFont("Segoe UI", 10))
        self.agency_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 9px 14px;
                min-height: 20px;
            }
            QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                border: 1px solid #334155;
            }
        """)
        agency_field_layout.addWidget(agency_title)
        agency_field_layout.addWidget(self.agency_combo)
        card_layout.addLayout(agency_field_layout)

        # 3. Campo de Usuario
        user_field_layout = QVBoxLayout()
        user_field_layout.setSpacing(6)

        user_title = QLabel("Usuario", card)
        user_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        user_title.setStyleSheet("color: #cbd5e1; border: none;")

        self.username_input = QLineEdit(card)
        self.username_input.setPlaceholderText("Ej: admin o agente1")
        self.username_input.setFont(QFont("Segoe UI", 10))
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 14px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #0f172a;
            }
        """)
        user_field_layout.addWidget(user_title)
        user_field_layout.addWidget(self.username_input)
        card_layout.addLayout(user_field_layout)

        # 4. Campo de Contraseña
        pass_field_layout = QVBoxLayout()
        pass_field_layout.setSpacing(6)

        pass_title = QLabel("Contraseña", card)
        pass_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        pass_title.setStyleSheet("color: #cbd5e1; border: none;")

        # Contenedor del input y botón de visibilidad
        pass_input_container = QHBoxLayout()
        pass_input_container.setSpacing(0)

        self.password_input = QLineEdit(card)
        self.password_input.setPlaceholderText("••••••••••••")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFont(QFont("Segoe UI", 10))
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 10px 14px;
                min-height: 20px;
                border-right: none;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                border-right: none;
            }
        """)

        self.toggle_pass_btn = QPushButton("👁", card)
        self.toggle_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pass_btn.setToolTip("Mostrar/Ocultar contraseña")
        self.toggle_pass_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #334155;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                padding: 10px 14px;
                min-height: 20px;
                min-width: 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #f8fafc;
            }
        """)
        self.toggle_pass_btn.clicked.connect(self._toggle_password_visibility)

        pass_input_container.addWidget(self.password_input)
        pass_input_container.addWidget(self.toggle_pass_btn)

        pass_field_layout.addWidget(pass_title)
        pass_field_layout.addLayout(pass_input_container)
        card_layout.addLayout(pass_field_layout)

        # 5. Botón de Iniciar Sesión
        self.login_btn = QPushButton("Ingresar al Sistema", card)
        self.login_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px;
                min-height: 22px;
                margin-top: 6px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
        """)
        self.login_btn.clicked.connect(self._handle_login)
        card_layout.addWidget(self.login_btn)

        # 6. Pie de tarjeta
        footer_label = QLabel("UNAN — Proyecto Integrador II", card)
        footer_label.setFont(QFont("Segoe UI", 8))
        footer_label.setStyleSheet("color: #64748b; border: none; margin-top: 8px;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(footer_label)

        main_layout.addWidget(card)

        # Atajo: Tecla Enter ejecuta el login
        enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        enter_shortcut.activated.connect(self._handle_login)

        # Enfocar campo de usuario por defecto
        self.username_input.setFocus()

    def _load_agencies(self) -> None:
        """Carga las agencias activas en el selector de inicio de sesión."""
        self.agency_combo.clear()
        try:
            agencies = auth_service.list_agencies(only_active=True)
            for ag in agencies:
                label = f"🏢 {ag.nombre_comercial} ({ag.codigo_agencia})"
                self.agency_combo.addItem(label, ag.id_agencia)
            if self.agency_combo.count() > 0:
                self.error_label.hide()
        except DatabaseConnectionError as e:
            logger.error("No se pudieron cargar las agencias (servidor API no disponible): %s", e.message)
            self._show_error(e.message)
        except Exception as e:
            logger.error("No se pudieron cargar las agencias en el selector de login: %s", e)
            self._show_error(
                "No se pudo conectar con el servidor API. Asegúrese de iniciar primero: "
                "uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
            )

    def _toggle_password_visibility(self) -> None:
        """Alterna el modo de visualización de la contraseña entre texto y máscara."""
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pass_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_btn.setText("👁")

    def _handle_login(self) -> None:
        """Invoca al servicio de autenticación y gestiona las respuestas visuales."""
        self.error_label.hide()
        if self.agency_combo.count() == 0:
            self._load_agencies()
            if self.agency_combo.count() == 0:
                return

        username = self.username_input.text().strip()
        password = self.password_input.text()
        tenant_id = self.agency_combo.currentData()

        if tenant_id is None:
            self._show_error("Por favor seleccione una agencia / sucursal válida.")
            self.agency_combo.setFocus()
            return

        # Validación visual inmediata
        if not username:
            self._show_error("Por favor ingrese su nombre de usuario.")
            self.username_input.setFocus()
            return

        if not password:
            self._show_error("Por favor ingrese su contraseña.")
            self.password_input.setFocus()
            return

        # Estado de carga visual
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Verificando credenciales...")
        self.setCursor(Qt.CursorShape.WaitCursor)

        try:
            # Delegación exclusiva a la capa de servicios (BLL) incluyendo el tenant_id
            user = auth_service.login(
                username=username,
                password=password,
                tenant_id=int(tenant_id),
            )
            logger.info("Login exitoso en UI para: %s (Agencia ID: %s)", user.username, user.tenant_id)
            self.login_success.emit(user)

        except (ValidationError, AuthenticationError, DatabaseConnectionError, AppException) as e:
            self._show_error(e.message)
            self.password_input.selectAll()
            self.password_input.setFocus()

        except Exception as e:
            logger.error("Error inesperado en vista de login: %s", e)
            self._show_error(f"Error de conexión con el servidor: {e}")

        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Ingresar al Sistema")
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _show_error(self, message: str) -> None:
        """Muestra un mensaje de error estilizado en la tarjeta."""
        self.error_label.setText(message)
        self.error_label.show()

    def clear_inputs(self) -> None:
        """Limpia los campos del formulario para un nuevo ingreso."""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        self.username_input.setFocus()
