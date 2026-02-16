"""
Dialog de boas-vindas e onboarding para novos usuarios.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config.settings import Settings, reload_settings
from ui.utils.config_manager import ConfigManager


class OnboardingDialog(QDialog):
    """Dialog inicial com boas-vindas, tour e configuracoes basicas."""

    onboarding_preferences_saved = pyqtSignal(dict)

    def __init__(self, parent=None, settings_path: str = "config/settings.yaml"):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings_model = Settings.from_yaml(settings_path)
        self.config_manager = ConfigManager.instance()

        self.setWindowTitle("Bem-vindo ao Planner")
        self.setModal(True)
        self.setMinimumSize(720, 520)

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Bem-vindo ao GLaDOS Planner")
        header.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        layout.addWidget(header)

        subtitle = QLabel(
            "Este assistente vai te ajudar a organizar leituras, agenda, foco e revisoes."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self._setup_welcome_tab()
        self._setup_tour_tab()
        self._setup_basic_settings_tab()

        self.hide_on_start_check = QCheckBox("Nao exibir este dialogo novamente")
        layout.addWidget(self.hide_on_start_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Concluir")
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setText("Fechar")

        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _setup_welcome_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        label = QLabel(
            "Este onboarding apresenta as funcoes principais e permite ajustar "
            "configuracoes iniciais para comecar rapidamente."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()

        self.tabs.addTab(tab, "Boas-vindas")

    def _setup_tour_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        tour_text = QLabel(
            "Tour rapido das views:\n\n"
            "1. Dashboard: visao geral do dia, cards e atalhos.\n"
            "2. Biblioteca: gerenciamento de livros e importacao.\n"
            "3. Agenda: compromissos, rotina e organizacao semanal.\n"
            "4. Sessao: leitura focada e pomodoro.\n"
            "5. Vault + GLaDOS: contexto do vault e interacao com assistente.\n"
            "6. Revisao Semanal: acompanhamento de progresso e metricas."
        )
        tour_text.setWordWrap(True)
        layout.addWidget(tour_text)
        layout.addStretch()

        self.tabs.addTab(tab, "Tour")

    def _setup_basic_settings_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.user_name_input = QLineEdit()
        self.assistant_name_input = QLineEdit()

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Academia", "philosophy_dark")
        self.theme_combo.addItem("Light Scholar", "philosophy_light")
        self.theme_combo.addItem("Night Owl", "philosophy_night")

        form.addRow("Seu nome:", self.user_name_input)
        form.addRow("Nome do assistente:", self.assistant_name_input)
        form.addRow("Tema inicial:", self.theme_combo)

        self.tabs.addTab(tab, "Configuracoes")

    @staticmethod
    def _as_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return default

    def _load_current_values(self):
        self.user_name_input.setText(str(self.settings_model.llm.glados.user_name or "").strip())
        self.assistant_name_input.setText(str(self.settings_model.llm.glados.glados_name or "").strip())

        current_theme = str(self.config_manager.theme or "philosophy_dark")
        idx = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)

        show_on_start = self._as_bool(
            self.config_manager.get("ui/show_onboarding_dialog", True),
            True
        )
        self.hide_on_start_check.setChecked(not show_on_start)

    def _save_and_accept(self):
        try:
            user_name = self.user_name_input.text().strip()
            assistant_name = self.assistant_name_input.text().strip()
            selected_theme = str(self.theme_combo.currentData())
            show_on_start = not self.hide_on_start_check.isChecked()

            self.settings_model.llm.glados.user_name = user_name
            self.settings_model.llm.glados.glados_name = assistant_name
            self.settings_model.save_yaml(self.settings_path)
            reload_settings(self.settings_path)

            self.config_manager.theme = selected_theme
            self.config_manager.set("ui/show_onboarding_dialog", show_on_start)

            self.onboarding_preferences_saved.emit(
                {
                    "theme": selected_theme,
                    "llm": {
                        "glados": {
                            "user_name": user_name,
                            "glados_name": assistant_name,
                        }
                    },
                    "ui": {
                        "show_onboarding_dialog": show_on_start,
                    },
                }
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao salvar onboarding",
                f"Nao foi possivel salvar as configuracoes iniciais:\n{e}"
            )
