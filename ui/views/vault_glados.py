"""
View dedicada para Vault Stats + GLaDOS.
Mantém a disposição 40/60 usada anteriormente na dashboard.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import logging

from ui.widgets.cards.glados_card import GladosCard
from ui.widgets.cards.stats_card import VaultStatsCard
from ui.controllers.vault_controller import VaultController

logger = logging.getLogger("GLaDOS.UI.VaultGladosView")


class VaultGladosView(QWidget):
    """Tela dedicada para fluxo contextual de notas com GLaDOS."""

    refresh_requested = pyqtSignal()
    navigate_to = pyqtSignal(str)

    def __init__(self, controllers=None):
        super().__init__()
        self.controllers = controllers or {}
        self.glados_controller = self.controllers.get("glados")
        self.vault_controller = self._resolve_vault_controller()
        self.assistant_name = "GLaDOS"
        self._load_identity_from_settings()

        self.vault_stats_card = None
        self.glados_card = None
        self.header_title_label = None

        self.setup_ui()
        self.setup_connections()

        QTimer.singleShot(100, self.load_initial_data)
        logger.info("VaultGladosView inicializada")

    def _load_identity_from_settings(self):
        try:
            from core.config.settings import Settings
            current_settings = Settings.from_yaml()
            name = str(current_settings.llm.glados.glados_name or "").strip()
            if name:
                self.assistant_name = name
        except Exception:
            pass

    def update_identity(self, user_name: str | None = None, assistant_name: str | None = None):
        del user_name  # Atualmente não utilizado nesta view.
        if assistant_name is not None:
            normalized = str(assistant_name).strip()
            if normalized:
                self.assistant_name = normalized
        if self.header_title_label:
            self.header_title_label.setText(f"🔍 Vault + {self.assistant_name}")

    def _resolve_vault_controller(self):
        if self.controllers.get("vault"):
            return self.controllers.get("vault")

        book_controller = self.controllers.get("book")
        if book_controller and hasattr(book_controller, "vault_manager"):
            vault_manager = getattr(book_controller, "vault_manager", None)
            if vault_manager and hasattr(vault_manager, "vault_path"):
                try:
                    controller = VaultController(str(vault_manager.vault_path))
                    self.controllers["vault"] = controller
                    return controller
                except Exception as e:
                    logger.warning("Falha ao criar VaultController via BookController: %s", e)

        try:
            from core.config.settings import settings as core_settings
            vault_path = str(core_settings.paths.vault)
            if vault_path:
                controller = VaultController(vault_path)
                self.controllers["vault"] = controller
                return controller
        except Exception as e:
            logger.warning("Falha ao resolver VaultController via settings: %s", e)

        return None

    def setup_ui(self):
        self.setObjectName("vault_glados_view")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        header = self._create_header()
        content_layout.addWidget(header)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)

        if self.vault_controller:
            self.vault_stats_card = VaultStatsCard(self.vault_controller)
            self.vault_stats_card.setObjectName("dashboard_card")
            self.vault_stats_card.setMinimumHeight(560)
            self.vault_stats_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row_layout.addWidget(self.vault_stats_card, 30)  # 40% visual
        else:
            placeholder = QLabel("Vault Stats\n(Vault não configurado)")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(
                "background-color: #2A2A2A; border-radius: 8px; color: #888; font-size: 14px; padding: 20px;"
            )
            placeholder.setMinimumHeight(560)
            row_layout.addWidget(placeholder, 30)

        self.glados_card = GladosCard(controller=self.glados_controller)
        self.glados_card.setObjectName("dashboard_card")
        self.glados_card.setMinimumHeight(560)
        self.glados_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(self.glados_card, 70)  # 60% visual

        content_layout.addLayout(row_layout)
        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        root.addWidget(scroll_area)

    def _create_header(self):
        header = QWidget()
        header.setObjectName("minimal_header")
        header.setFixedHeight(60)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel(f"🔍 Vault + {self.assistant_name}")
        title.setFont(QFont("FiraCode Nerd Font Propo", 18, QFont.Weight.Medium))
        self.header_title_label = title
        subtitle = QLabel("Contextualização de notas e chat assistido")
        subtitle.setFont(QFont("FiraCode Nerd Font Propo", 10))
        subtitle.setStyleSheet("color: #8A94A6;")

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        left.addWidget(title)
        left.addWidget(subtitle)

        refresh_button = QLabel(" ")
        layout.addLayout(left)
        layout.addStretch()
        layout.addWidget(refresh_button)
        return header

    def setup_connections(self):
        if self.glados_card:
            self.glados_card.ui_message_sent.connect(self.handle_glados_message)
            self.glados_card.ui_action_selected.connect(self.handle_glados_action)
            self.glados_card.context_action_requested.connect(self.handle_glados_context_action)

        if self.vault_stats_card:
            self.vault_stats_card.sync_requested.connect(self.handle_vault_sync)
            self.vault_stats_card.refresh_requested.connect(self.handle_vault_refresh)
            self.vault_stats_card.context_confirmed.connect(self.handle_vault_context_confirmed)

        if self.vault_controller:
            self.vault_controller.error_occurred.connect(self.handle_vault_error)

    def load_initial_data(self):
        if self.vault_stats_card:
            try:
                self.vault_stats_card.load_initial_data()
            except Exception as e:
                logger.error("Erro ao carregar dados do vault: %s", e)

    def on_view_activated(self):
        self.load_initial_data()

    def handle_glados_message(self, message):
        logger.info("Mensagem GLaDOS: %s...", (message or "")[:50])

    def handle_glados_action(self, action_id):
        logger.info("Ação GLaDOS: %s", action_id)

    def handle_glados_context_action(self, action_id: str, payload: dict):
        notes_count = len(payload.get("notes", []))
        logger.info("Ação de contexto GLaDOS: %s (%s notas)", action_id, notes_count)

    def handle_vault_context_confirmed(self, payload: dict):
        notes = payload.get("notes", [])
        logger.info("Contexto confirmado no vault: %s nota(s)", len(notes))
        if self.glados_card and hasattr(self.glados_card, "apply_vault_context"):
            self.glados_card.apply_vault_context(payload)

    def handle_vault_sync(self, sync_type: str):
        logger.info("Sincronização do vault solicitada: %s", sync_type)
        if sync_type == "from_obsidian":
            reply = QMessageBox.question(
                self,
                "Sincronizar do Obsidian",
                "Deseja importar todas as notas do Obsidian?\nNotas existentes serão atualizadas.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes and self.vault_controller:
                self.vault_controller.sync_from_obsidian()
        elif sync_type == "to_obsidian" and self.vault_controller:
            self.vault_controller.sync_all_to_obsidian()

    def handle_vault_refresh(self):
        if self.vault_stats_card:
            self.vault_stats_card.refresh_data()

    def handle_vault_error(self, error_message: str):
        logger.error("Erro do vault: %s", error_message)
