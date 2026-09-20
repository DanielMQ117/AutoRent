"""Diálogo modal para el restablecimiento administrativo de contraseñas de usuario."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.exceptions import AppException
from src.domain.models import User
from src.services.user_service import user_service


class UserPasswordDialog(QDialog):
    """Diálogo modal para cambiar o restablecer la contraseña de un usuario."""

    def __init__(self, user: User, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.user = user
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"Restablecer Contraseña — @{self.user.username}")
        self.setFixedSize(440, 310)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel {
                color: #cbd5e1;
            }
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Encabezado
        title = QLabel(f"🔑 Restablecer Contraseña")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        info_box = QFrame()
        info_box.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        lbl_user = QLabel(f"<b>Usuario:</b> @{self.user.username} ({self.user.nombre_completo})")
        lbl_user.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        lbl_rol = QLabel(f"<b>Rol:</b> {self.user.rol_nombre or 'N/A'}")
        lbl_rol.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        info_layout.addWidget(lbl_user)
        info_layout.addWidget(lbl_rol)
        layout.addWidget(info_box)

        # Campos
        layout.addWidget(QLabel("Nueva Contraseña (mínimo 6 caracteres):"))
        self.txt_new_password = QLineEdit()
        self.txt_new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_new_password.setPlaceholderText("••••••••")
        layout.addWidget(self.txt_new_password)

        layout.addWidget(QLabel("Confirmar Nueva Contraseña:"))
        self.txt_confirm_password = QLineEdit()
        self.txt_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_confirm_password.setPlaceholderText("••••••••")
        layout.addWidget(self.txt_confirm_password)

        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFont(QFont("Segoe UI", 9))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 16px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Actualizar Contraseña")
        self.btn_save.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 18px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_save.clicked.connect(self._handle_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _handle_save(self) -> None:
        """Valida y procesa el cambio de contraseña."""
        new_pwd = self.txt_new_password.text()
        confirm_pwd = self.txt_confirm_password.text()

        if len(new_pwd) < 6:
            QMessageBox.warning(self, "Contraseña Débil", "La nueva contraseña debe tener al menos 6 caracteres.")
            self.txt_new_password.setFocus()
            return

        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "No Coinciden", "Las contraseñas ingresadas no coinciden. Por favor verifique.")
            self.txt_confirm_password.selectAll()
            self.txt_confirm_password.setFocus()
            return

        try:
            user_service.reset_password(self.user.id_usuario, new_pwd)
            QMessageBox.information(
                self,
                "Contraseña Actualizada",
                f"La contraseña para la cuenta @{self.user.username} ha sido restablecida exitosamente.",
            )
            self.accept()
        except AppException as e:
            QMessageBox.critical(self, "Error de Validación", e.message)
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al actualizar la contraseña: {e}")
