"""Dialog de boas-vindas e onboarding completo para primeiro uso."""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config.settings import Settings, reload_settings
from core.llm.runtime_discovery import detect_nvidia_gpus, discover_gguf_models
from core.modules.agenda_manager import AgendaManager
from core.vault.bootstrap import bootstrap_vault
from ui.utils.config_manager import ConfigManager


class OnboardingDialog(QDialog):
    onboarding_preferences_saved = pyqtSignal(dict)

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
        self._routine_preferences = {}

        self.setWindowTitle("Boas-vindas ao GLaDOS Planner")
        self.setModal(True)
        self.setMinimumSize(860, 640)

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Configure seu ambiente inicial")
        header.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        subtitle = QLabel(
            "Primeiro acesso: ajuste identidade, paths, LLM, agenda, pomodoro e revisão. "
            "O vault será criado automaticamente."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._setup_welcome_tab()
        self._setup_identity_tab()
        self._setup_paths_tab()
        self._setup_llm_tab()
        self._setup_agenda_tab()
        self._setup_pomodoro_review_tab()
        self._setup_features_tab()

        self.hide_on_start_check = QCheckBox("Não exibir este diálogo novamente")
        layout.addWidget(self.hide_on_start_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Concluir configuração")
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setText("Fechar")
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _setup_welcome_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        label = QLabel(
            "Checklist desta etapa:\n\n"
            "1. Definir nomes e tema.\n"
            "2. Confirmar paths (vault/data/modelos/export/cache).\n"
            "3. Ajustar preferências da LLM.\n"
            "4. Ajustar rotina da agenda, pomodoro e revisão.\n"
            "5. Confirmar módulos ativos.\n\n"
            "Ao concluir, o vault será inicializado com estrutura e arquivos esperados."
        )
        label.setWordWrap(True)
        tab_layout.addWidget(label)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "Boas-vindas")

    def _setup_identity_tab(self):
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
        self.tabs.addTab(tab, "Identidade")

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

        self.llm_model_path_input = QLineEdit()
        self.llm_model_combo = QComboBox()
        self.llm_model_combo.currentIndexChanged.connect(self._on_model_combo_changed)
        self.llm_device_mode_combo = QComboBox()
        for label, value in self.DEVICE_MODE_LABELS:
            self.llm_device_mode_combo.addItem(label, value)
        self.llm_device_mode_combo.currentIndexChanged.connect(self._sync_llm_mode_controls)
        self.llm_gpu_combo = QComboBox()
        self.llm_n_ctx_spin = QSpinBox()
        self.llm_n_ctx_spin.setRange(256, 32768)
        self.llm_n_gpu_layers_spin = QSpinBox()
        self.llm_n_gpu_layers_spin.setRange(0, 200)
        self.llm_cpu_threads_spin = QSpinBox()
        self.llm_cpu_threads_spin.setRange(1, max(1, int(os.cpu_count() or 1)))
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

    def _setup_agenda_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.sleep_start_input = QLineEdit()
        self.sleep_end_input = QLineEdit()
        self.breakfast_time_input = QLineEdit()
        self.lunch_time_input = QLineEdit()
        self.dinner_time_input = QLineEdit()
        self.weekly_review_time_input = QLineEdit()
        self.weekly_review_duration_spin = QSpinBox()
        self.weekly_review_duration_spin.setRange(30, 240)
        self.weekly_review_duration_spin.setSuffix(" min")

        form.addRow("Sono (início HH:MM):", self.sleep_start_input)
        form.addRow("Sono (fim HH:MM):", self.sleep_end_input)
        form.addRow("Café da manhã:", self.breakfast_time_input)
        form.addRow("Almoço:", self.lunch_time_input)
        form.addRow("Jantar:", self.dinner_time_input)
        form.addRow("Revisão semanal (hora):", self.weekly_review_time_input)
        form.addRow("Duração revisão semanal:", self.weekly_review_duration_spin)
        self.tabs.addTab(tab, "Agenda")

    def _setup_pomodoro_review_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.pomodoro_work_spin = QSpinBox()
        self.pomodoro_work_spin.setRange(1, 180)
        self.pomodoro_work_spin.setSuffix(" min")
        self.pomodoro_short_break_spin = QSpinBox()
        self.pomodoro_short_break_spin.setRange(1, 60)
        self.pomodoro_short_break_spin.setSuffix(" min")
        self.pomodoro_long_break_spin = QSpinBox()
        self.pomodoro_long_break_spin.setRange(5, 120)
        self.pomodoro_long_break_spin.setSuffix(" min")
        self.pomodoro_sessions_spin = QSpinBox()
        self.pomodoro_sessions_spin.setRange(2, 12)
        self.review_prompt_enabled_check = QCheckBox("Ativar perguntas periódicas durante revisão")
        self.review_question_interval_spin = QSpinBox()
        self.review_question_interval_spin.setRange(1, 180)
        self.review_question_interval_spin.setSuffix(" min")
        self.review_arrow_pan_step_spin = QSpinBox()
        self.review_arrow_pan_step_spin.setRange(40, 400)
        self.review_arrow_pan_step_spin.setSingleStep(10)

        form.addRow("Pomodoro (foco):", self.pomodoro_work_spin)
        form.addRow("Pausa curta:", self.pomodoro_short_break_spin)
        form.addRow("Pausa longa:", self.pomodoro_long_break_spin)
        form.addRow("Ciclos até pausa longa:", self.pomodoro_sessions_spin)
        form.addRow("", self.review_prompt_enabled_check)
        form.addRow("Intervalo de perguntas:", self.review_question_interval_spin)
        form.addRow("Passo das setas no mapa:", self.review_arrow_pan_step_spin)
        self.tabs.addTab(tab, "Pomodoro e Review")

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

    def _load_current_values(self):
        paths = self.settings_model.paths
        llm = self.settings_model.llm
        pomodoro = self.settings_model.pomodoro
        review = self.settings_model.review_view
        features = self.settings_model.features

        self.user_name_input.setText(str(llm.glados.user_name or "").strip())
        self.assistant_name_input.setText(str(llm.glados.glados_name or "").strip())
        current_theme = str(self.config_manager.theme or "philosophy_dark")
        idx = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.vault_path_input.setText(paths.vault)
        self.data_dir_input.setText(paths.data_dir)
        self.models_dir_input.setText(paths.models_dir)
        self.exports_dir_input.setText(paths.exports_dir)
        self.cache_dir_input.setText(paths.cache_dir)

        self.llm_model_path_input.setText(llm.model_path)
        self._set_device_mode(getattr(llm, "device_mode", "auto"))
        self.llm_n_ctx_spin.setValue(int(llm.n_ctx))
        self.llm_n_gpu_layers_spin.setValue(int(llm.n_gpu_layers))
        self.llm_cpu_threads_spin.setValue(max(1, int(getattr(llm.cpu, "threads", 4) or 4)))
        self.llm_temperature_spin.setValue(float(llm.temperature))
        self.llm_top_p_spin.setValue(float(llm.top_p))
        self.llm_max_tokens_spin.setValue(int(llm.max_tokens))
        self._refresh_model_catalog()
        self._refresh_gpu_catalog(selected_index=int(getattr(llm, "gpu_index", 0) or 0))
        self._sync_llm_mode_controls()

        self.pomodoro_work_spin.setValue(int(pomodoro.work_duration))
        self.pomodoro_short_break_spin.setValue(int(pomodoro.short_break))
        self.pomodoro_long_break_spin.setValue(int(pomodoro.long_break))
        self.pomodoro_sessions_spin.setValue(int(pomodoro.sessions_before_long_break))

        self.review_prompt_enabled_check.setChecked(bool(review.question_prompt_enabled))
        self.review_question_interval_spin.setValue(int(review.question_interval_minutes))
        self.review_arrow_pan_step_spin.setValue(int(review.arrow_pan_step))

        self.feature_llm.setChecked(bool(features.enable_llm))
        self.feature_obsidian.setChecked(bool(features.enable_obsidian_sync))
        self.feature_pomodoro.setChecked(bool(features.enable_pomodoro))
        self.feature_translation.setChecked(bool(features.enable_translation))
        self.feature_glados_personality.setChecked(bool(features.enable_glados_personality))
        self.feature_vault_brain.setChecked(bool(features.enable_vault_as_brain))

        show_on_start = self._as_bool(self.config_manager.get("ui/show_onboarding_dialog", True), True)
        self.hide_on_start_check.setChecked(not show_on_start)
        self._load_routine_preferences()

    def _load_routine_preferences(self):
        defaults = {
            "sleep_start": "23:00",
            "sleep_end": "07:00",
            "breakfast_time": "08:00",
            "lunch_time": "12:30",
            "dinner_time": "19:30",
            "weekly_review_time": "18:00",
            "weekly_review_duration_minutes": 90,
        }
        vault_path = self.vault_path_input.text().strip() or self.settings_model.paths.vault
        try:
            manager = AgendaManager(vault_path=vault_path)
            loaded = manager.get_routine_preferences()
            if isinstance(loaded, dict):
                defaults.update(loaded)
        except Exception:
            pass
        self._routine_preferences = defaults
        self.sleep_start_input.setText(str(defaults["sleep_start"]))
        self.sleep_end_input.setText(str(defaults["sleep_end"]))
        self.breakfast_time_input.setText(str(defaults["breakfast_time"]))
        self.lunch_time_input.setText(str(defaults["lunch_time"]))
        self.dinner_time_input.setText(str(defaults["dinner_time"]))
        self.weekly_review_time_input.setText(str(defaults["weekly_review_time"]))
        self.weekly_review_duration_spin.setValue(int(defaults["weekly_review_duration_minutes"]))

    def _select_vault_path(self):
        selected = QFileDialog.getExistingDirectory(self, "Selecionar pasta do Vault")
        if selected:
            self.vault_path_input.setText(selected)

    def _select_model_path(self):
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar modelo LLM",
            "",
            "GGUF (*.gguf);;Todos os arquivos (*)",
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
        if selected_path:
            self.llm_model_path_input.setText(selected_path)

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
            self.llm_gpu_combo.addItem(f"GPU {idx}: {name} ({mem_mb} MB)", idx)
            if idx == selected_index:
                preferred_idx = i
        self.llm_gpu_combo.setCurrentIndex(preferred_idx)

    def _set_device_mode(self, mode_value: str):
        value = str(mode_value or "auto")
        idx = self.llm_device_mode_combo.findData(value)
        if idx < 0:
            idx = self.llm_device_mode_combo.findData("auto")
        self.llm_device_mode_combo.setCurrentIndex(max(0, idx))

    def _sync_llm_mode_controls(self):
        cpu_only = str(self.llm_device_mode_combo.currentData() or "auto") == "cpu_only"
        self.llm_cpu_threads_spin.setEnabled(cpu_only)

    @staticmethod
    def _derive_device_flags(mode_value: str) -> tuple[bool, bool]:
        mode = str(mode_value or "auto")
        if mode == "cpu_only":
            return False, True
        if mode == "gpu_only":
            return True, False
        return True, True

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

    def _save_and_accept(self):
        try:
            user_name = self.user_name_input.text().strip()
            assistant_name = self.assistant_name_input.text().strip()
            selected_theme = str(self.theme_combo.currentData())
            show_on_start = not self.hide_on_start_check.isChecked()
            vault_path = self.vault_path_input.text().strip()
            if not vault_path:
                raise ValueError("Defina um caminho de vault válido.")

            self.settings_model.paths.vault = vault_path
            self.settings_model.paths.data_dir = self.data_dir_input.text().strip()
            self.settings_model.paths.models_dir = self.models_dir_input.text().strip()
            self.settings_model.paths.exports_dir = self.exports_dir_input.text().strip()
            self.settings_model.paths.cache_dir = self.cache_dir_input.text().strip()

            self.settings_model.llm.glados.user_name = user_name
            self.settings_model.llm.glados.glados_name = assistant_name
            self.settings_model.llm.model_name = Path(self.llm_model_path_input.text().strip()).name
            self.settings_model.llm.model_path = self.llm_model_path_input.text().strip()
            self.settings_model.llm.models_dir = self.models_dir_input.text().strip()
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

            self.settings_model.pomodoro.work_duration = self.pomodoro_work_spin.value()
            self.settings_model.pomodoro.short_break = self.pomodoro_short_break_spin.value()
            self.settings_model.pomodoro.long_break = self.pomodoro_long_break_spin.value()
            self.settings_model.pomodoro.sessions_before_long_break = self.pomodoro_sessions_spin.value()

            self.settings_model.review_view.question_prompt_enabled = self.review_prompt_enabled_check.isChecked()
            self.settings_model.review_view.question_interval_minutes = self.review_question_interval_spin.value()
            self.settings_model.review_view.arrow_pan_step = self.review_arrow_pan_step_spin.value()

            self.settings_model.features.enable_llm = self.feature_llm.isChecked()
            self.settings_model.features.enable_obsidian_sync = self.feature_obsidian.isChecked()
            self.settings_model.features.enable_pomodoro = self.feature_pomodoro.isChecked()
            self.settings_model.features.enable_translation = self.feature_translation.isChecked()
            self.settings_model.features.enable_glados_personality = self.feature_glados_personality.isChecked()
            self.settings_model.features.enable_vault_as_brain = self.feature_vault_brain.isChecked()

            bootstrap_vault(
                vault_path=vault_path,
                vault_structure=self.settings_model.obsidian.vault_structure,
            )
            self._save_routine_preferences(vault_path)

            self.settings_model.save_yaml(self.settings_path)
            updated_settings = reload_settings(self.settings_path)

            self.config_manager.theme = selected_theme
            self.config_manager.set("ui/show_onboarding_dialog", show_on_start)

            payload = updated_settings.model_dump()
            payload["theme"] = selected_theme
            payload["ui"] = {"show_onboarding_dialog": show_on_start}
            self.onboarding_preferences_saved.emit(payload)
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao salvar onboarding",
                f"Não foi possível salvar as configurações iniciais:\n{e}",
            )

    def _save_routine_preferences(self, vault_path: str):
        updates = {
            "sleep_start": self.sleep_start_input.text().strip(),
            "sleep_end": self.sleep_end_input.text().strip(),
            "breakfast_time": self.breakfast_time_input.text().strip(),
            "lunch_time": self.lunch_time_input.text().strip(),
            "dinner_time": self.dinner_time_input.text().strip(),
            "weekly_review_time": self.weekly_review_time_input.text().strip(),
            "weekly_review_duration_minutes": self.weekly_review_duration_spin.value(),
        }
        manager = AgendaManager(vault_path=vault_path)
        manager.update_routine_preferences(updates)
