"""
Dialog para edição das configurações principais do sistema.
"""
import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget,
    QFormLayout, QDialogButtonBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from core.config.settings import Settings, reload_settings
from core.llm.runtime_discovery import detect_nvidia_gpus, discover_gguf_models
from ui.utils.config_manager import ConfigManager


class SettingsDialog(QDialog):
    """Dialog para controle de configurações do sistema."""

    settings_saved = pyqtSignal(dict)
    DEVICE_MODE_LABELS = [
        ("Automático", "auto"),
        ("Apenas CPU", "cpu_only"),
        ("Preferir GPU", "gpu_prefer"),
        ("Apenas GPU (sem fallback)", "gpu_only"),
    ]

    def __init__(self, parent=None, settings_path: str = "config/settings.yaml"):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings_model = Settings.from_yaml(settings_path)
        self.config_manager = ConfigManager.instance()

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
        self._setup_review_view_tab()
        self._setup_features_tab()

        footer_layout = QHBoxLayout()

        self.open_onboarding_now_button = QPushButton("Abrir boas-vindas agora")
        self.open_onboarding_now_button.clicked.connect(self._open_onboarding_now)
        footer_layout.addWidget(self.open_onboarding_now_button)

        self.factory_reset_button = QPushButton("Reset de fábrica")
        self.factory_reset_button.clicked.connect(self._factory_reset)
        footer_layout.addWidget(self.factory_reset_button)
        footer_layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_settings)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)
        layout.addLayout(footer_layout)

    def _setup_app_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.app_name_input = QLineEdit()
        self.app_version_input = QLineEdit()
        self.app_debug_check = QCheckBox("Ativar modo debug")
        self.show_onboarding_check = QCheckBox("Exibir diálogo de boas-vindas ao iniciar")
        self.app_log_level_combo = QComboBox()
        self.app_log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

        form.addRow("Nome da aplicação:", self.app_name_input)
        form.addRow("Versão:", self.app_version_input)
        form.addRow("Nível de log:", self.app_log_level_combo)
        form.addRow("", self.app_debug_check)
        form.addRow("", self.show_onboarding_check)

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
        form.addRow("Diretório de dados:", self.data_dir_input)
        form.addRow("Diretório de modelos:", self.models_dir_input)
        form.addRow("Diretório de exportações:", self.exports_dir_input)
        form.addRow("Diretório de cache:", self.cache_dir_input)

        self.tabs.addTab(tab, "Paths")

    def _setup_llm_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.llm_user_name_input = QLineEdit()
        self.llm_assistant_name_input = QLineEdit()
        self.llm_model_path_input = QLineEdit()
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.currentIndexChanged.connect(self._on_model_combo_changed)
        self.llm_n_ctx_spin = QSpinBox()
        self.llm_n_ctx_spin.setRange(256, 32768)
        self.llm_n_gpu_layers_spin = QSpinBox()
        self.llm_n_gpu_layers_spin.setRange(0, 200)
        self.llm_cpu_threads_spin = QSpinBox()
        max_threads = max(1, int(os.cpu_count() or 1))
        self.llm_cpu_threads_spin.setRange(1, max_threads)
        self.llm_device_mode_combo = QComboBox()
        for label, value in self.DEVICE_MODE_LABELS:
            self.llm_device_mode_combo.addItem(label, value)
        self.llm_device_mode_combo.currentIndexChanged.connect(self._sync_llm_mode_controls)
        self.llm_gpu_combo = QComboBox()
        self.llm_temperature_spin = QDoubleSpinBox()
        self.llm_temperature_spin.setRange(0.0, 2.0)
        self.llm_temperature_spin.setSingleStep(0.05)
        self.llm_top_p_spin = QDoubleSpinBox()
        self.llm_top_p_spin.setRange(0.1, 1.0)
        self.llm_top_p_spin.setSingleStep(0.01)
        self.llm_max_tokens_spin = QSpinBox()
        self.llm_max_tokens_spin.setRange(64, 4096)

        model_catalog_layout = QHBoxLayout()
        model_catalog_layout.addWidget(self.llm_model_combo)
        model_refresh_btn = QPushButton("Atualizar")
        model_refresh_btn.clicked.connect(self._refresh_model_catalog)
        model_catalog_layout.addWidget(model_refresh_btn)

        model_path_layout = QHBoxLayout()
        model_path_layout.addWidget(self.llm_model_path_input)
        model_btn = QPushButton("Selecionar")
        model_btn.clicked.connect(self._select_model_path)
        model_path_layout.addWidget(model_btn)

        gpu_layout = QHBoxLayout()
        gpu_layout.addWidget(self.llm_gpu_combo)
        gpu_refresh_btn = QPushButton("Detectar")
        gpu_refresh_btn.clicked.connect(self._refresh_gpu_catalog)
        gpu_layout.addWidget(gpu_refresh_btn)

        form.addRow("Nome do usuário (dashboard):", self.llm_user_name_input)
        form.addRow("Nome do assistente:", self.llm_assistant_name_input)
        form.addRow("Modelos detectados:", model_catalog_layout)
        form.addRow("Caminho do modelo:", model_path_layout)
        form.addRow("Modo de execução:", self.llm_device_mode_combo)
        form.addRow("GPU detectada:", gpu_layout)
        form.addRow("Context window (n_ctx):", self.llm_n_ctx_spin)
        form.addRow("GPU layers:", self.llm_n_gpu_layers_spin)
        form.addRow("CPU threads (cpu_only):", self.llm_cpu_threads_spin)
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
        self.feature_glados_personality = QCheckBox("Habilitar personalidade do assistente")
        self.feature_vault_brain = QCheckBox("Habilitar vault como cérebro")

        layout.addWidget(self.feature_llm)
        layout.addWidget(self.feature_obsidian)
        layout.addWidget(self.feature_pomodoro)
        layout.addWidget(self.feature_translation)
        layout.addWidget(self.feature_glados_personality)
        layout.addWidget(self.feature_vault_brain)
        layout.addStretch()

        self.tabs.addTab(tab, "Features")

    def _setup_review_view_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.review_prompt_enabled_check = QCheckBox("Ativar perguntas periódicas durante revisão")
        self.review_question_interval_spin = QSpinBox()
        self.review_question_interval_spin.setRange(1, 180)
        self.review_question_interval_spin.setSuffix(" min")
        self.review_arrow_pan_step_spin = QSpinBox()
        self.review_arrow_pan_step_spin.setRange(40, 400)
        self.review_arrow_pan_step_spin.setSingleStep(10)

        form.addRow("", self.review_prompt_enabled_check)
        form.addRow("Intervalo de perguntas:", self.review_question_interval_spin)
        form.addRow("Passo das setas no mapa:", self.review_arrow_pan_step_spin)

        self.tabs.addTab(tab, "Review View")

    def _load_current_values(self):
        app = self.settings_model.app
        paths = self.settings_model.paths
        llm = self.settings_model.llm
        obsidian = self.settings_model.obsidian
        review_view = self.settings_model.review_view
        features = self.settings_model.features

        self.app_name_input.setText(app.name)
        self.app_version_input.setText(app.version)
        self.app_debug_check.setChecked(app.debug)
        self.app_log_level_combo.setCurrentText(app.log_level)
        self.show_onboarding_check.setChecked(
            self._as_bool(self.config_manager.get("ui/show_onboarding_dialog", True), True)
        )

        self.vault_path_input.setText(paths.vault)
        self.data_dir_input.setText(paths.data_dir)
        self.models_dir_input.setText(paths.models_dir)
        self.exports_dir_input.setText(paths.exports_dir)
        self.cache_dir_input.setText(paths.cache_dir)

        self.llm_model_path_input.setText(llm.model_path)
        self._set_device_mode(getattr(llm, "device_mode", self._infer_device_mode(llm)))
        self.llm_n_ctx_spin.setValue(llm.n_ctx)
        self.llm_n_gpu_layers_spin.setValue(llm.n_gpu_layers)
        self.llm_cpu_threads_spin.setValue(max(1, int(getattr(llm.cpu, "threads", 4) or 4)))
        self.llm_temperature_spin.setValue(llm.temperature)
        self.llm_top_p_spin.setValue(llm.top_p)
        self.llm_max_tokens_spin.setValue(llm.max_tokens)
        self.llm_user_name_input.setText(llm.glados.user_name)
        self.llm_assistant_name_input.setText(llm.glados.glados_name)
        self._refresh_model_catalog()
        self._refresh_gpu_catalog(selected_index=int(getattr(llm, "gpu_index", 0) or 0))
        self._sync_llm_mode_controls()

        self.obsidian_templates_dir_input.setText(obsidian.templates_dir)
        self.obsidian_auto_sync_check.setChecked(obsidian.auto_sync)
        self.obsidian_sync_interval_spin.setValue(obsidian.sync_interval)

        self.review_prompt_enabled_check.setChecked(review_view.question_prompt_enabled)
        self.review_question_interval_spin.setValue(int(review_view.question_interval_minutes))
        self.review_arrow_pan_step_spin.setValue(int(review_view.arrow_pan_step))

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

            self.settings_model.llm.model_name = Path(self.llm_model_path_input.text().strip()).name
            self.settings_model.llm.models_dir = self.models_dir_input.text().strip()
            self.settings_model.llm.model_path = self.llm_model_path_input.text().strip()
            mode_value = str(self.llm_device_mode_combo.currentData() or "auto")
            self.settings_model.llm.device_mode = mode_value
            self.settings_model.llm.use_gpu, self.settings_model.llm.use_cpu = self._derive_device_flags(mode_value)
            self.settings_model.llm.gpu_index = int(self.llm_gpu_combo.currentData() or 0)
            self.settings_model.llm.n_ctx = self.llm_n_ctx_spin.value()
            self.settings_model.llm.n_gpu_layers = self.llm_n_gpu_layers_spin.value()
            self.settings_model.llm.cpu.threads = self.llm_cpu_threads_spin.value()
            self.settings_model.llm.temperature = self.llm_temperature_spin.value()
            self.settings_model.llm.top_p = self.llm_top_p_spin.value()
            self.settings_model.llm.max_tokens = self.llm_max_tokens_spin.value()
            self.settings_model.llm.glados.user_name = self.llm_user_name_input.text().strip()
            self.settings_model.llm.glados.glados_name = self.llm_assistant_name_input.text().strip()

            self.settings_model.obsidian.templates_dir = self.obsidian_templates_dir_input.text().strip()
            self.settings_model.obsidian.auto_sync = self.obsidian_auto_sync_check.isChecked()
            self.settings_model.obsidian.sync_interval = self.obsidian_sync_interval_spin.value()

            self.settings_model.review_view.question_prompt_enabled = self.review_prompt_enabled_check.isChecked()
            self.settings_model.review_view.question_interval_minutes = self.review_question_interval_spin.value()
            self.settings_model.review_view.arrow_pan_step = self.review_arrow_pan_step_spin.value()

            self.settings_model.features.enable_llm = self.feature_llm.isChecked()
            self.settings_model.features.enable_obsidian_sync = self.feature_obsidian.isChecked()
            self.settings_model.features.enable_pomodoro = self.feature_pomodoro.isChecked()
            self.settings_model.features.enable_translation = self.feature_translation.isChecked()
            self.settings_model.features.enable_glados_personality = self.feature_glados_personality.isChecked()
            self.settings_model.features.enable_vault_as_brain = self.feature_vault_brain.isChecked()
            self.config_manager.set(
                "ui/show_onboarding_dialog",
                self.show_onboarding_check.isChecked()
            )

            self.settings_model.save_yaml(self.settings_path)
            updated = reload_settings(self.settings_path)
            payload = updated.model_dump()
            payload["ui"] = {
                "show_onboarding_dialog": self.show_onboarding_check.isChecked()
            }
            self.settings_saved.emit(payload)
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao salvar configurações",
                f"Não foi possível salvar as configurações:\n{e}"
            )

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
            self._refresh_model_catalog()

    def _refresh_model_catalog(self):
        models_dir = self.models_dir_input.text().strip() or self.settings_model.paths.models_dir
        current_path = self.llm_model_path_input.text().strip()
        catalog = discover_gguf_models(models_dir)

        self.llm_model_combo.blockSignals(True)
        self.llm_model_combo.clear()
        self.llm_model_combo.addItem("(manual) manter caminho atual", "")
        selected_idx = 0
        for i, item in enumerate(catalog, start=1):
            label = f"{item.get('name')} ({item.get('size_mb', 0)} MB)"
            model_path = str(item.get("path", ""))
            self.llm_model_combo.addItem(label, model_path)
            if current_path and Path(current_path).resolve() == Path(model_path).resolve():
                selected_idx = i
        self.llm_model_combo.setCurrentIndex(selected_idx)
        self.llm_model_combo.blockSignals(False)

    def _on_model_combo_changed(self, _index: int):
        selected_path = str(self.llm_model_combo.currentData() or "").strip()
        if not selected_path:
            return
        self.llm_model_path_input.setText(selected_path)

    def _set_device_mode(self, mode_value: str):
        value = str(mode_value or "auto")
        idx = self.llm_device_mode_combo.findData(value)
        if idx < 0:
            idx = self.llm_device_mode_combo.findData("auto")
        self.llm_device_mode_combo.setCurrentIndex(max(0, idx))
        self._sync_llm_mode_controls()

    def _sync_llm_mode_controls(self):
        mode = str(self.llm_device_mode_combo.currentData() or "auto")
        cpu_only = mode == "cpu_only"
        self.llm_cpu_threads_spin.setEnabled(cpu_only)

    @staticmethod
    def _derive_device_flags(mode_value: str) -> tuple[bool, bool]:
        mode = str(mode_value or "auto")
        if mode == "cpu_only":
            return False, True
        if mode == "gpu_only":
            return True, False
        if mode == "gpu_prefer":
            return True, True
        return True, True

    @staticmethod
    def _infer_device_mode(llm_cfg) -> str:
        use_gpu = bool(getattr(llm_cfg, "use_gpu", True))
        use_cpu = bool(getattr(llm_cfg, "use_cpu", True))
        if use_gpu and not use_cpu:
            return "gpu_only"
        if not use_gpu and use_cpu:
            return "cpu_only"
        return "auto"

    def _refresh_gpu_catalog(self, selected_index: int = 0):
        gpus = detect_nvidia_gpus()
        self.llm_gpu_combo.clear()
        if not gpus:
            self.llm_gpu_combo.addItem("Nenhuma GPU NVIDIA detectada", 0)
            return

        preferred_idx = 0
        for i, gpu in enumerate(gpus):
            idx = int(gpu.get("index", i))
            name = str(gpu.get("name", "GPU"))
            mem_mb = int(gpu.get("memory_total_mb", 0))
            label = f"GPU {idx}: {name} ({mem_mb} MB)"
            self.llm_gpu_combo.addItem(label, idx)
            if idx == selected_index:
                preferred_idx = i
        self.llm_gpu_combo.setCurrentIndex(preferred_idx)

    def _open_onboarding_now(self):
        parent = self.parent()
        if parent and hasattr(parent, "show_onboarding_dialog"):
            parent.show_onboarding_dialog(force=True)
            return

        try:
            from ui.widgets.dialogs.onboarding_dialog import OnboardingDialog

            dialog = OnboardingDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Não foi possível abrir",
                f"Falha ao abrir onboarding:\n{e}"
            )

    def _factory_reset(self):
        answer = QMessageBox.warning(
            self,
            "Reset de fábrica",
            (
                "Isso vai apagar dados da aplicação (cache, histórico/exportações e banco de dados)\n"
                "e resetar nomes para o padrão.\n\n"
                "Deseja continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._reset_application_data()
            self._reset_settings_after_factory_cleanup()
            self._load_current_values()
            QMessageBox.information(
                self,
                "Reset concluído",
                "Configurações de fábrica aplicadas com sucesso."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro no reset",
                f"Não foi possível concluir o reset de fábrica:\n{e}"
            )

    def _reset_application_data(self):
        current_settings = Settings.from_yaml(self.settings_path)

        data_dir = self._to_abs_path(current_settings.paths.data_dir)
        cache_dir = self._to_abs_path(current_settings.paths.cache_dir)
        exports_dir = self._to_abs_path(current_settings.paths.exports_dir)
        history_dir = data_dir / "history"
        db_file = self._resolve_sqlite_db_file(current_settings.database.url)

        # Limpa dados adicionados pela aplicação sem remover modelos baixados.
        self._clear_directory_contents(cache_dir)
        self._clear_directory_contents(exports_dir)
        self._clear_directory_contents(history_dir)

        if db_file:
            self._delete_sqlite_files(db_file)

    def _reset_settings_after_factory_cleanup(self):
        preserved_settings = Settings.from_yaml(self.settings_path)
        default_settings = Settings()

        preserved_settings.llm.glados.user_name = default_settings.llm.glados.user_name
        preserved_settings.llm.glados.glados_name = default_settings.llm.glados.glados_name
        preserved_settings.save_yaml(self.settings_path)

        self.config_manager.reset_to_defaults()
        self.settings_model = reload_settings(self.settings_path)

        payload = self.settings_model.model_dump()
        payload["ui"] = {
            "show_onboarding_dialog": self._as_bool(
                self.config_manager.get("ui/show_onboarding_dialog", True),
                True,
            )
        }
        self.settings_saved.emit(payload)

    @staticmethod
    def _to_abs_path(raw_path: str) -> Path:
        path = Path(str(raw_path or "").strip()).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path

    @staticmethod
    def _clear_directory_contents(directory: Path):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return

        for item in directory.iterdir():
            if item.name == ".keep":
                continue
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    def _resolve_sqlite_db_file(self, database_url: str) -> Path | None:
        url = str(database_url or "").strip()
        if not url.startswith("sqlite:///"):
            return None

        raw_db_path = url.replace("sqlite:///", "", 1)
        if not raw_db_path:
            return None
        return self._to_abs_path(raw_db_path)

    @staticmethod
    def _delete_sqlite_files(db_file: Path):
        db_file.parent.mkdir(parents=True, exist_ok=True)
        sidecars = [db_file, db_file.with_suffix(db_file.suffix + "-wal"), db_file.with_suffix(db_file.suffix + "-shm"), db_file.with_suffix(db_file.suffix + "-journal")]
        for path in sidecars:
            if path.exists():
                path.unlink(missing_ok=True)
