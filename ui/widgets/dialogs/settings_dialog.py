"""
Dialog para edição das configurações principais do sistema.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget,
    QFormLayout, QDialogButtonBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from core.config.settings import Settings, reload_settings


class SettingsDialog(QDialog):
    """Dialog para controle de configurações do sistema."""

    settings_saved = pyqtSignal(dict)

    def __init__(self, parent=None, settings_path: str = "config/settings.yaml"):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings_model = Settings.from_yaml(settings_path)

        self.setWindowTitle("Configurações do Sistema")
        self.setMinimumSize(760, 560)
        self.setModal(True)

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("⚙️ Configurações do Sistema")
        header.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._setup_app_tab()
        self._setup_paths_tab()
        self._setup_llm_tab()
        self._setup_obsidian_tab()
        self._setup_features_tab()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _setup_app_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.app_name_input = QLineEdit()
        self.app_version_input = QLineEdit()
        self.app_debug_check = QCheckBox("Ativar modo debug")
        self.app_log_level_combo = QComboBox()
        self.app_log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

        form.addRow("Nome da aplicação:", self.app_name_input)
        form.addRow("Versão:", self.app_version_input)
        form.addRow("Nível de log:", self.app_log_level_combo)
        form.addRow("", self.app_debug_check)

        self.tabs.addTab(tab, "App")

    def _setup_paths_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.vault_path_input = QLineEdit()
        self.data_dir_input = QLineEdit()
        self.models_dir_input = QLineEdit()
        self.exports_dir_input = QLineEdit()
        self.cache_dir_input = QLineEdit()

        vault_layout = QHBoxLayout()
        vault_layout.addWidget(self.vault_path_input)
        vault_btn = QPushButton("Selecionar")
        vault_btn.clicked.connect(self._select_vault_path)
        vault_layout.addWidget(vault_btn)

        form.addRow("Vault:", vault_layout)
        form.addRow("Data dir:", self.data_dir_input)
        form.addRow("Models dir:", self.models_dir_input)
        form.addRow("Exports dir:", self.exports_dir_input)
        form.addRow("Cache dir:", self.cache_dir_input)

        self.tabs.addTab(tab, "Paths")

    def _setup_llm_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.llm_model_name_input = QLineEdit()
        self.llm_model_path_input = QLineEdit()
        self.llm_n_ctx_spin = QSpinBox()
        self.llm_n_ctx_spin.setRange(256, 32768)
        self.llm_n_gpu_layers_spin = QSpinBox()
        self.llm_n_gpu_layers_spin.setRange(0, 200)
        self.llm_temperature_spin = QDoubleSpinBox()
        self.llm_temperature_spin.setRange(0.0, 2.0)
        self.llm_temperature_spin.setSingleStep(0.05)
        self.llm_top_p_spin = QDoubleSpinBox()
        self.llm_top_p_spin.setRange(0.1, 1.0)
        self.llm_top_p_spin.setSingleStep(0.01)
        self.llm_max_tokens_spin = QSpinBox()
        self.llm_max_tokens_spin.setRange(64, 4096)

        model_path_layout = QHBoxLayout()
        model_path_layout.addWidget(self.llm_model_path_input)
        model_btn = QPushButton("Selecionar")
        model_btn.clicked.connect(self._select_model_path)
        model_path_layout.addWidget(model_btn)

        form.addRow("Nome do modelo:", self.llm_model_name_input)
        form.addRow("Caminho do modelo:", model_path_layout)
        form.addRow("Context window (n_ctx):", self.llm_n_ctx_spin)
        form.addRow("GPU layers:", self.llm_n_gpu_layers_spin)
        form.addRow("Temperature:", self.llm_temperature_spin)
        form.addRow("Top-p:", self.llm_top_p_spin)
        form.addRow("Max tokens:", self.llm_max_tokens_spin)

        self.tabs.addTab(tab, "LLM")

    def _setup_obsidian_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.obsidian_templates_dir_input = QLineEdit()
        self.obsidian_auto_sync_check = QCheckBox("Ativar sincronização automática")
        self.obsidian_sync_interval_spin = QSpinBox()
        self.obsidian_sync_interval_spin.setRange(30, 86400)
        self.obsidian_sync_interval_spin.setSuffix(" s")

        form.addRow("Templates dir:", self.obsidian_templates_dir_input)
        form.addRow("", self.obsidian_auto_sync_check)
        form.addRow("Intervalo de sync:", self.obsidian_sync_interval_spin)

        self.tabs.addTab(tab, "Obsidian")

    def _setup_features_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.feature_llm = QCheckBox("Habilitar LLM")
        self.feature_obsidian = QCheckBox("Habilitar sincronização Obsidian")
        self.feature_pomodoro = QCheckBox("Habilitar Pomodoro")
        self.feature_translation = QCheckBox("Habilitar tradução")
        self.feature_glados_personality = QCheckBox("Habilitar personalidade GLaDOS")
        self.feature_vault_brain = QCheckBox("Habilitar vault como cérebro")

        layout.addWidget(self.feature_llm)
        layout.addWidget(self.feature_obsidian)
        layout.addWidget(self.feature_pomodoro)
        layout.addWidget(self.feature_translation)
        layout.addWidget(self.feature_glados_personality)
        layout.addWidget(self.feature_vault_brain)
        layout.addStretch()

        self.tabs.addTab(tab, "Features")

    def _load_current_values(self):
        app = self.settings_model.app
        paths = self.settings_model.paths
        llm = self.settings_model.llm
        obsidian = self.settings_model.obsidian
        features = self.settings_model.features

        self.app_name_input.setText(app.name)
        self.app_version_input.setText(app.version)
        self.app_debug_check.setChecked(app.debug)
        self.app_log_level_combo.setCurrentText(app.log_level)

        self.vault_path_input.setText(paths.vault)
        self.data_dir_input.setText(paths.data_dir)
        self.models_dir_input.setText(paths.models_dir)
        self.exports_dir_input.setText(paths.exports_dir)
        self.cache_dir_input.setText(paths.cache_dir)

        self.llm_model_name_input.setText(llm.model_name)
        self.llm_model_path_input.setText(llm.model_path)
        self.llm_n_ctx_spin.setValue(llm.n_ctx)
        self.llm_n_gpu_layers_spin.setValue(llm.n_gpu_layers)
        self.llm_temperature_spin.setValue(llm.temperature)
        self.llm_top_p_spin.setValue(llm.top_p)
        self.llm_max_tokens_spin.setValue(llm.max_tokens)

        self.obsidian_templates_dir_input.setText(obsidian.templates_dir)
        self.obsidian_auto_sync_check.setChecked(obsidian.auto_sync)
        self.obsidian_sync_interval_spin.setValue(obsidian.sync_interval)

        self.feature_llm.setChecked(features.enable_llm)
        self.feature_obsidian.setChecked(features.enable_obsidian_sync)
        self.feature_pomodoro.setChecked(features.enable_pomodoro)
        self.feature_translation.setChecked(features.enable_translation)
        self.feature_glados_personality.setChecked(features.enable_glados_personality)
        self.feature_vault_brain.setChecked(features.enable_vault_as_brain)

    def _save_settings(self):
        try:
            self.settings_model.app.name = self.app_name_input.text().strip()
            self.settings_model.app.version = self.app_version_input.text().strip()
            self.settings_model.app.debug = self.app_debug_check.isChecked()
            self.settings_model.app.log_level = self.app_log_level_combo.currentText()

            self.settings_model.paths.vault = self.vault_path_input.text().strip()
            self.settings_model.paths.data_dir = self.data_dir_input.text().strip()
            self.settings_model.paths.models_dir = self.models_dir_input.text().strip()
            self.settings_model.paths.exports_dir = self.exports_dir_input.text().strip()
            self.settings_model.paths.cache_dir = self.cache_dir_input.text().strip()

            self.settings_model.llm.model_name = self.llm_model_name_input.text().strip()
            self.settings_model.llm.model_path = self.llm_model_path_input.text().strip()
            self.settings_model.llm.n_ctx = self.llm_n_ctx_spin.value()
            self.settings_model.llm.n_gpu_layers = self.llm_n_gpu_layers_spin.value()
            self.settings_model.llm.temperature = self.llm_temperature_spin.value()
            self.settings_model.llm.top_p = self.llm_top_p_spin.value()
            self.settings_model.llm.max_tokens = self.llm_max_tokens_spin.value()

            self.settings_model.obsidian.templates_dir = self.obsidian_templates_dir_input.text().strip()
            self.settings_model.obsidian.auto_sync = self.obsidian_auto_sync_check.isChecked()
            self.settings_model.obsidian.sync_interval = self.obsidian_sync_interval_spin.value()

            self.settings_model.features.enable_llm = self.feature_llm.isChecked()
            self.settings_model.features.enable_obsidian_sync = self.feature_obsidian.isChecked()
            self.settings_model.features.enable_pomodoro = self.feature_pomodoro.isChecked()
            self.settings_model.features.enable_translation = self.feature_translation.isChecked()
            self.settings_model.features.enable_glados_personality = self.feature_glados_personality.isChecked()
            self.settings_model.features.enable_vault_as_brain = self.feature_vault_brain.isChecked()

            self.settings_model.save_yaml(self.settings_path)
            updated = reload_settings(self.settings_path)
            self.settings_saved.emit(updated.model_dump())
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao salvar configurações",
                f"Não foi possível salvar as configurações:\n{e}"
            )

    def _select_vault_path(self):
        selected = QFileDialog.getExistingDirectory(self, "Selecionar pasta do Vault")
        if selected:
            self.vault_path_input.setText(selected)

    def _select_model_path(self):
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar modelo LLM",
            "",
            "GGUF (*.gguf);;Todos os arquivos (*)"
        )
        if selected:
            self.llm_model_path_input.setText(selected)
