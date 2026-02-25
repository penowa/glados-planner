"""Dialog de onboarding rapido, opcional e orientado por interacao."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlsplit, urlunsplit

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config.settings import Settings, reload_settings
from core.llm.model_installer import ModelInstallError, install_models
from core.llm.runtime_discovery import detect_nvidia_gpus, discover_gguf_models
from core.modules.agenda_manager import AgendaManager
from core.vault.bootstrap import bootstrap_vault
from ui.utils.config_manager import ConfigManager


class OnboardingDialog(QDialog):
    onboarding_preferences_saved = pyqtSignal(dict)

    ONBOARDING_VERSION = "tutorial_v3"
    BACKEND_LABELS = [
        ("LLM local (GGUF)", "local"),
        ("LLM cloud (LiteLLM/Ollama)", "cloud"),
    ]
    DEVICE_MODE_LABELS = [
        ("Automatico", "auto"),
        ("Somente CPU", "cpu_only"),
        ("Preferir GPU", "gpu_prefer"),
        ("Somente GPU", "gpu_only"),
    ]
    OLLAMA_DEFAULT_API_BASE = "http://127.0.0.1:11434"
    OLLAMA_CLOUD_DEFAULT_MODEL = "qwen3.5:cloud"
    OLLAMA_PRESET_MODELS = [
        ("Qwen3.5 Cloud (recomendado)", "qwen3.5:cloud"),
        ("Qwen2.5 1.5B", "qwen2.5:1.5b"),
        ("Qwen3 4B", "qwen3:4b"),
        ("Llama 3.2 3B", "llama3.2:3b"),
    ]

    def __init__(self, parent=None, settings_path: str = "config/settings.yaml"):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings_model = Settings.from_yaml(settings_path)
        self.config_manager = ConfigManager.instance()
        self._routine_preferences = {}
        self._llm_form = None
        self._llm_local_rows = []
        self._llm_cloud_rows = []

        self.setWindowTitle("Boas-vindas ao GLaDOS Planner")
        self.setModal(True)
        self.setMinimumSize(860, 640)

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Tutorial inicial (rapido e opcional)")
        header.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        subtitle = QLabel(
            "Voce pode configurar apenas o essencial agora e ajustar o restante depois em Configuracoes."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._setup_welcome_tab()
        self._setup_llm_tab()
        self._setup_paths_tab()
        self._setup_agenda_tab()
        self._setup_pomodoro_review_tab()
        self._setup_features_tab()
        self._setup_summary_tab()

        self.hide_on_start_check = QCheckBox("Nao exibir este guia automaticamente ao iniciar")
        layout.addWidget(self.hide_on_start_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Salvar e iniciar")
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setText("Fechar")

        self.skip_button = buttons.addButton(
            "Pular por agora",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.skip_button.clicked.connect(self._skip_onboarding)

        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._apply_compact_control_style()

    def _setup_welcome_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(
            self._create_info_box(
                "Objetivo: deixar o planner pronto para uso em poucos cliques.\n"
                "O tutorial e opcional: se preferir, use 'Pular por agora' e finalize depois em Configuracoes."
            )
        )

        welcome = QLabel(
            "Como voce deseja ser tratado(a)?"
        )
        welcome.setWordWrap(True)
        welcome.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(welcome)

        form = QFormLayout()
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("Ex.: Pindarolas")
        self.assistant_name_input = QLineEdit()
        self.assistant_name_input.setPlaceholderText("Ex.: GLaDOS")
        form.addRow("Seu nome:", self.user_name_input)
        form.addRow("Nome da assistente:", self.assistant_name_input)
        layout.addLayout(form)

        quick_box = QFrame()
        quick_layout = QVBoxLayout(quick_box)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(8)

        quick_title = QLabel("Atalhos de inicio rapido")
        quick_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        quick_layout.addWidget(quick_title)

        preset_row = QHBoxLayout()
        self.quick_preset_combo = QComboBox()
        self.quick_preset_combo.addItem("Escolha um preset rapido", "none")
        self.quick_preset_combo.addItem("LLM local recomendada", "local")
        self.quick_preset_combo.addItem("Ollama Cloud recomendado", "ollama")
        self.quick_apply_button = QPushButton("Aplicar")
        self._set_compact_button(self.quick_apply_button, min_width=90)
        self.quick_apply_button.clicked.connect(self._apply_selected_quick_preset)
        preset_row.addWidget(self.quick_preset_combo, 1)
        preset_row.addWidget(self.quick_apply_button)
        quick_layout.addLayout(preset_row)

        self.quick_setup_status_label = QLabel("Status rapido: nenhum preset aplicado.")
        self.quick_setup_status_label.setWordWrap(True)
        self.quick_setup_status_label.setStyleSheet("color: #8A94A6; font-size: 12px;")
        quick_layout.addWidget(self.quick_setup_status_label)

        layout.addWidget(quick_box)
        layout.addStretch()
        self.tabs.addTab(tab, "Inicio")

    def _setup_llm_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(
            self._create_info_box(
                "Configuracao de LLM (opcional).\n"
                "No modo cloud, o fluxo guiado faz login no Ollama e prepara qwen3.5:cloud automaticamente."
            )
        )

        form = QFormLayout()
        form.setVerticalSpacing(5)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._llm_form = form
        self._llm_local_rows = []
        self._llm_cloud_rows = []

        self.llm_backend_combo = QComboBox()
        for label, value in self.BACKEND_LABELS:
            self.llm_backend_combo.addItem(label, value)
        self.llm_backend_combo.currentIndexChanged.connect(self._sync_llm_mode_controls)

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

        self.llm_cloud_model_input = QLineEdit()
        self.llm_cloud_model_input.setPlaceholderText("ollama/qwen3.5:cloud ou openai/gpt-4o-mini")
        self.llm_cloud_api_base_input = QLineEdit()
        self.llm_cloud_api_base_input.setPlaceholderText(self.OLLAMA_DEFAULT_API_BASE)
        self.llm_cloud_api_version_input = QLineEdit()
        self.llm_cloud_organization_input = QLineEdit()
        self.llm_cloud_api_key_input = QLineEdit()
        self.llm_cloud_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_cloud_timeout_spin = QSpinBox()
        self.llm_cloud_timeout_spin.setRange(5, 600)
        self.llm_cloud_timeout_spin.setSuffix(" s")
        self.llm_cloud_max_retries_spin = QSpinBox()
        self.llm_cloud_max_retries_spin.setRange(0, 10)

        self.ollama_model_combo = QComboBox()
        for label, value in self.OLLAMA_PRESET_MODELS:
            self.ollama_model_combo.addItem(label, value)

        self.llm_cloud_ollama_preset_button = QPushButton("Aplicar preset")
        self.llm_cloud_ollama_preset_button.clicked.connect(self._apply_ollama_cloud_preset)
        self._set_compact_button(self.llm_cloud_ollama_preset_button, min_width=110)

        self.ollama_setup_button = QPushButton("Login + preparar modelo")
        self.ollama_setup_button.clicked.connect(self._setup_ollama_with_script)
        self._set_compact_button(self.ollama_setup_button, min_width=170)

        self.ollama_probe_button = QPushButton("Testar")
        self.ollama_probe_button.clicked.connect(self._test_ollama_connection)
        self._set_compact_button(self.ollama_probe_button, min_width=90)

        self.ollama_login_help_label = QLabel(
            "Fluxo guiado: clique em 'Login + preparar modelo'. "
            "Se o navegador abrir para autenticacao, conclua o login e aguarde: o modelo "
            "qwen3.5:cloud sera preparado automaticamente."
        )
        self.ollama_login_help_label.setWordWrap(True)
        self.ollama_login_help_label.setStyleSheet("color: #8A94A6; font-size: 12px;")

        self.ollama_status_label = QLabel("Status Ollama: nao verificado.")
        self.ollama_status_label.setWordWrap(True)
        self.ollama_status_label.setStyleSheet("color: #8A94A6; font-size: 12px;")

        self.llm_download_choice_combo = QComboBox()
        self.llm_download_choice_combo.addItem("Nao baixar agora", "none")
        self.llm_download_choice_combo.addItem("Baixar TinyLlama 1.1B - 0.7 GB", "tinyllama")
        self.llm_download_choice_combo.addItem("Baixar Qwen3 4B - 2.5 GB", "qwen4b")
        self.llm_download_choice_combo.addItem("Baixar ambos - 3.2 GB", "all")

        self.llm_download_button = QPushButton("Baixar GGUF")
        self.llm_download_button.clicked.connect(self._download_selected_models)
        self._set_compact_button(self.llm_download_button, min_width=120)

        self.llm_download_status_label = QLabel("Status de download: nenhum.")
        self.llm_download_status_label.setWordWrap(True)
        self.llm_download_status_label.setStyleSheet("color: #8A94A6; font-size: 12px;")

        model_catalog_layout = QHBoxLayout()
        model_catalog_layout.addWidget(self.llm_model_combo)
        model_refresh_btn = QPushButton("Atualizar")
        model_refresh_btn.clicked.connect(self._refresh_model_catalog)
        self._set_compact_button(model_refresh_btn, min_width=95)
        model_catalog_layout.addWidget(model_refresh_btn)

        model_path_layout = QHBoxLayout()
        model_path_layout.addWidget(self.llm_model_path_input)
        model_btn = QPushButton("Selecionar")
        model_btn.clicked.connect(self._select_model_path)
        self._set_compact_button(model_btn, min_width=95)
        model_path_layout.addWidget(model_btn)

        gpu_layout = QHBoxLayout()
        gpu_layout.addWidget(self.llm_gpu_combo)
        gpu_refresh_btn = QPushButton("Detectar")
        gpu_refresh_btn.clicked.connect(self._refresh_gpu_catalog)
        self._set_compact_button(gpu_refresh_btn, min_width=95)
        gpu_layout.addWidget(gpu_refresh_btn)

        cloud_model_layout = QHBoxLayout()
        cloud_model_layout.addWidget(self.llm_cloud_model_input)
        cloud_model_layout.addWidget(self.llm_cloud_ollama_preset_button)

        download_layout = QHBoxLayout()
        download_layout.addWidget(self.llm_download_choice_combo, 1)
        download_layout.addWidget(self.llm_download_button)

        ollama_action_layout = QHBoxLayout()
        ollama_action_layout.addStretch(1)
        ollama_action_layout.addWidget(self.ollama_setup_button)
        ollama_action_layout.addWidget(self.ollama_probe_button)

        self._add_llm_row("Backend da LLM:", self.llm_backend_combo)
        self._add_llm_row("Modelos encontrados (.gguf):", model_catalog_layout, scope="local")
        self._add_llm_row("Arquivo do modelo:", model_path_layout, scope="local")
        self._add_llm_row("Como rodar o modelo:", self.llm_device_mode_combo, scope="local")
        self._add_llm_row("GPU disponivel:", gpu_layout, scope="local")
        self._add_llm_row("Tamanho de contexto:", self.llm_n_ctx_spin, scope="local")
        self._add_llm_row("Camadas na GPU:", self.llm_n_gpu_layers_spin, scope="local")
        self._add_llm_row("Threads de CPU:", self.llm_cpu_threads_spin, scope="local")
        self._add_llm_row("Download de modelos:", download_layout, scope="local")
        self._add_llm_row("", self.llm_download_status_label, scope="local")

        self._add_llm_row("Modelo cloud:", cloud_model_layout, scope="cloud")
        self._add_llm_row("API base cloud:", self.llm_cloud_api_base_input, scope="cloud")
        self._add_llm_row("API version cloud (opcional):", self.llm_cloud_api_version_input, scope="cloud")
        self._add_llm_row("Organization cloud (opcional):", self.llm_cloud_organization_input, scope="cloud")
        self._add_llm_row("API key cloud (opcional):", self.llm_cloud_api_key_input, scope="cloud")
        self._add_llm_row("Timeout cloud:", self.llm_cloud_timeout_spin, scope="cloud")
        self._add_llm_row("Tentativas cloud:", self.llm_cloud_max_retries_spin, scope="cloud")
        self._add_llm_row("Modelo Ollama a preparar:", self.ollama_model_combo, scope="cloud")
        self._add_llm_row("", self.ollama_login_help_label, scope="cloud")
        self._add_llm_row("", ollama_action_layout, scope="cloud")
        self._add_llm_row("", self.ollama_status_label, scope="cloud")

        self._add_llm_row("Criatividade:", self.llm_temperature_spin)
        self._add_llm_row("Foco na resposta:", self.llm_top_p_spin)
        self._add_llm_row("Limite de tokens por resposta:", self.llm_max_tokens_spin)

        tab_layout.addLayout(form)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "LLM")

    @staticmethod
    def _set_compact_button(button: QPushButton, min_width: int = 96):
        button.setMinimumHeight(28)
        button.setMaximumHeight(32)
        button.setMinimumWidth(min_width)
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    @staticmethod
    def _set_compact_combo(combo: QComboBox):
        combo.setMinimumHeight(28)
        combo.setMaximumHeight(32)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _apply_compact_control_style(self):
        for combo in self.findChildren(QComboBox):
            self._set_compact_combo(combo)
        for button in self.findChildren(QPushButton):
            min_width = max(76, min(170, button.sizeHint().width()))
            self._set_compact_button(button, min_width=min_width)

    def _add_llm_row(self, label: str, field, scope: str = "common"):
        if self._llm_form is None:
            return
        row = self._llm_form.rowCount()
        self._llm_form.addRow(label, field)
        if scope == "local":
            self._llm_local_rows.append(row)
        elif scope == "cloud":
            self._llm_cloud_rows.append(row)

    def _setup_paths_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(
            self._create_info_box(
                "Configure apenas o Vault.\n"
                "Pastas internas (dados, modelos, exportacoes e cache) sao criadas automaticamente."
            )
        )

        form = QFormLayout()
        form.setVerticalSpacing(5)

        self.vault_path_input = QLineEdit()
        self.data_dir_input = QLineEdit()
        self.models_dir_input = QLineEdit()
        self.exports_dir_input = QLineEdit()
        self.cache_dir_input = QLineEdit()

        self.data_dir_input.setReadOnly(True)
        self.models_dir_input.setReadOnly(True)
        self.exports_dir_input.setReadOnly(True)
        self.cache_dir_input.setReadOnly(True)

        vault_layout = QHBoxLayout()
        vault_layout.addWidget(self.vault_path_input)
        vault_btn = QPushButton("Selecionar")
        vault_btn.clicked.connect(self._select_vault_path)
        vault_layout.addWidget(vault_btn)

        form.addRow("Vault:", vault_layout)
        form.addRow("Diretorio de dados (automatico):", self.data_dir_input)
        form.addRow("Diretorio de modelos (automatico):", self.models_dir_input)
        form.addRow("Diretorio de exportacoes (automatico):", self.exports_dir_input)
        form.addRow("Diretorio de cache (automatico):", self.cache_dir_input)

        tab_layout.addLayout(form)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "Arquivos")

    def _setup_agenda_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(
            self._create_info_box(
                "Opcional: rotina inicial para facilitar agenda, refeicoes e revisao semanal."
            )
        )

        form = QFormLayout()
        form.setVerticalSpacing(5)

        self.sleep_start_input = QLineEdit()
        self.sleep_end_input = QLineEdit()
        self.breakfast_time_input = QLineEdit()
        self.lunch_time_input = QLineEdit()
        self.dinner_time_input = QLineEdit()
        self.weekly_review_time_input = QLineEdit()
        self.weekly_review_duration_spin = QSpinBox()
        self.weekly_review_duration_spin.setRange(30, 240)
        self.weekly_review_duration_spin.setSuffix(" min")

        form.addRow("Sono (inicio HH:MM):", self.sleep_start_input)
        form.addRow("Sono (fim HH:MM):", self.sleep_end_input)
        form.addRow("Cafe da manha:", self.breakfast_time_input)
        form.addRow("Almoco:", self.lunch_time_input)
        form.addRow("Jantar:", self.dinner_time_input)
        form.addRow("Revisao semanal (hora):", self.weekly_review_time_input)
        form.addRow("Duracao revisao semanal:", self.weekly_review_duration_spin)

        tab_layout.addLayout(form)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "Agenda")

    def _setup_pomodoro_review_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.addWidget(
            self._create_info_box(
                "Opcional: ritmo de foco (Pomodoro) e prompts de revisao."
            )
        )

        form = QFormLayout()
        form.setVerticalSpacing(5)

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

        self.review_prompt_enabled_check = QCheckBox("Ativar perguntas periodicas durante revisao")
        self.review_question_interval_spin = QSpinBox()
        self.review_question_interval_spin.setRange(1, 180)
        self.review_question_interval_spin.setSuffix(" min")

        self.review_arrow_pan_step_spin = QSpinBox()
        self.review_arrow_pan_step_spin.setRange(40, 400)
        self.review_arrow_pan_step_spin.setSingleStep(10)

        form.addRow("Pomodoro (foco):", self.pomodoro_work_spin)
        form.addRow("Pausa curta:", self.pomodoro_short_break_spin)
        form.addRow("Pausa longa:", self.pomodoro_long_break_spin)
        form.addRow("Ciclos ate pausa longa:", self.pomodoro_sessions_spin)
        form.addRow("", self.review_prompt_enabled_check)
        form.addRow("Intervalo de perguntas:", self.review_question_interval_spin)
        form.addRow("Passo das setas no mapa:", self.review_arrow_pan_step_spin)

        tab_layout.addLayout(form)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "Pomodoro e Review")

    def _setup_features_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(
            self._create_info_box(
                "Opcional: ative somente os módulos que quer usar agora.\n"
                "Você pode mudar tudo depois em Configurações."
            )
        )

        self.feature_llm = QCheckBox("Habilitar LLM")
        self.feature_obsidian = QCheckBox("Habilitar sincronizacao Obsidian")
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

    def _setup_summary_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        summary_box = self._create_info_box(
            "Resumo:\n\n"
            "1. Identidade (usuario e assistente).\n"
            "2. LLM local ou cloud, com automacoes opcionais (GGUF/Ollama).\n"
            "3. Vault e diretorios internos automaticos.\n"
            "4. Rotina base (agenda/pomodoro/review), se voce quiser ajustar agora.\n"
            "5. Modulos ativos.\n\n"
            "Ao clicar em 'Salvar e iniciar', o planner abre pronto para uso.\n"
            "Downloads e setups pesados ficam opcionais e sob seu controle."
        )
        tab_layout.addWidget(summary_box)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "Resumo")

    def _create_info_box(self, text: str) -> QFrame:
        box = QFrame()
        box.setObjectName("onboarding_info_box")
        box.setStyleSheet(
            "QFrame#onboarding_info_box {"
            "background: rgba(98, 114, 164, 0.12);"
            "border: 1px solid rgba(136, 154, 219, 0.35);"
            "border-radius: 8px;"
            "padding: 6px;"
            "}"
        )
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(2)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #AFC3FF; font-size: 12px;")
        box_layout.addWidget(label)
        return box

    def _load_current_values(self):
        paths = self.settings_model.paths
        llm = self.settings_model.llm
        pomodoro = self.settings_model.pomodoro
        review = self.settings_model.review_view
        features = self.settings_model.features

        self.user_name_input.setText(str(llm.glados.user_name or "").strip())
        self.assistant_name_input.setText(str(llm.glados.glados_name or "").strip())
        self.config_manager.theme = "philosophy_dark"

        self.vault_path_input.setText(paths.vault)
        self.data_dir_input.setText(paths.data_dir)
        self.models_dir_input.setText(paths.models_dir)
        self.exports_dir_input.setText(paths.exports_dir)
        self.cache_dir_input.setText(paths.cache_dir)

        backend_value = str(getattr(llm, "backend", "local") or "local")
        self._set_backend_mode(backend_value)

        self.llm_model_path_input.setText(str(llm.model_path or ""))
        self._set_device_mode(getattr(llm, "device_mode", "auto"))
        self.llm_n_ctx_spin.setValue(int(llm.n_ctx))
        self.llm_n_gpu_layers_spin.setValue(int(llm.n_gpu_layers))
        self.llm_cpu_threads_spin.setValue(max(1, int(getattr(llm.cpu, "threads", 4) or 4)))
        self.llm_temperature_spin.setValue(float(llm.temperature))
        self.llm_top_p_spin.setValue(float(llm.top_p))
        self.llm_max_tokens_spin.setValue(int(llm.max_tokens))

        cloud_cfg = getattr(llm, "cloud", None)
        cloud_model = str(getattr(cloud_cfg, "model", f"ollama/{self.OLLAMA_CLOUD_DEFAULT_MODEL}") or "")
        self.llm_cloud_model_input.setText(cloud_model)
        cloud_api_base = str(getattr(cloud_cfg, "api_base", "") or "")
        self.llm_cloud_api_base_input.setText(cloud_api_base or self.OLLAMA_DEFAULT_API_BASE)
        self.llm_cloud_api_version_input.setText(str(getattr(cloud_cfg, "api_version", "") or ""))
        self.llm_cloud_organization_input.setText(str(getattr(cloud_cfg, "organization", "") or ""))
        self.llm_cloud_api_key_input.setText(str(getattr(cloud_cfg, "api_key", "") or ""))
        self.llm_cloud_timeout_spin.setValue(int(getattr(cloud_cfg, "timeout_seconds", 120) or 120))
        self.llm_cloud_max_retries_spin.setValue(int(getattr(cloud_cfg, "max_retries", 1) or 1))
        self._set_ollama_model_selection_from_cloud_model(cloud_model)

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

    def _set_backend_mode(self, backend_value: str):
        value = str(backend_value or "local")
        idx = self.llm_backend_combo.findData(value)
        if idx < 0:
            idx = self.llm_backend_combo.findData("local")
        self.llm_backend_combo.setCurrentIndex(max(0, idx))

    def _set_device_mode(self, mode_value: str):
        value = str(mode_value or "auto")
        idx = self.llm_device_mode_combo.findData(value)
        if idx < 0:
            idx = self.llm_device_mode_combo.findData("auto")
        self.llm_device_mode_combo.setCurrentIndex(max(0, idx))

    def _set_ollama_model_selection_from_cloud_model(self, cloud_model: str):
        model_name = self._extract_ollama_model_name(cloud_model)
        if not model_name:
            return
        idx = self.ollama_model_combo.findData(model_name)
        if idx >= 0:
            self.ollama_model_combo.setCurrentIndex(idx)
            return

        custom_label = f"Atual ({model_name})"
        self.ollama_model_combo.addItem(custom_label, model_name)
        self.ollama_model_combo.setCurrentIndex(self.ollama_model_combo.count() - 1)

    def _apply_local_quick_preset(self):
        self._set_backend_mode("local")
        self._set_device_mode("auto")
        if not self.llm_model_path_input.text().strip():
            self._refresh_model_catalog()
        self.quick_setup_status_label.setText(
            "Status rapido: preset local aplicado (backend local + modo automatico)."
        )

    def _apply_ollama_quick_preset(self):
        self._apply_ollama_cloud_preset()
        self.quick_setup_status_label.setText(
            "Status rapido: preset Ollama Cloud aplicado. Use o botao de login para preparar qwen3.5:cloud."
        )
        if self.tabs.count() > 1:
            self.tabs.setCurrentIndex(1)

    def _apply_selected_quick_preset(self):
        selected = str(self.quick_preset_combo.currentData() or "none")
        if selected == "local":
            self._apply_local_quick_preset()
            return
        if selected == "ollama":
            self._apply_ollama_quick_preset()
            return
        self.quick_setup_status_label.setText(
            "Status rapido: selecione um preset para aplicar."
        )

    def _apply_ollama_cloud_preset(self):
        self._set_backend_mode("cloud")
        self._set_ollama_model_selection_from_cloud_model(f"ollama/{self.OLLAMA_CLOUD_DEFAULT_MODEL}")
        model_name = str(self.ollama_model_combo.currentData() or self.OLLAMA_CLOUD_DEFAULT_MODEL).strip()
        self.llm_cloud_model_input.setText(f"ollama/{model_name}")
        self.llm_cloud_api_base_input.setText(self.OLLAMA_DEFAULT_API_BASE)
        if self.llm_cloud_timeout_spin.value() < 60:
            self.llm_cloud_timeout_spin.setValue(120)
        if self.llm_cloud_max_retries_spin.value() < 1:
            self.llm_cloud_max_retries_spin.setValue(1)
        self._sync_llm_mode_controls()

    def _setup_ollama_with_script(self):
        api_base = self._normalize_ollama_api_base(self.llm_cloud_api_base_input.text().strip())
        model_name = self.OLLAMA_CLOUD_DEFAULT_MODEL
        self._set_ollama_model_selection_from_cloud_model(f"ollama/{model_name}")
        self._set_backend_mode("cloud")
        self.llm_cloud_model_input.setText(f"ollama/{model_name}")

        self.ollama_setup_button.setEnabled(False)
        self.ollama_status_label.setText("Status Ollama: iniciando login e preparando qwen3.5:cloud...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            # No app empacotado, evite executar script com Python externo.
            # Use o fallback interno para garantir login/pull no mesmo runtime da UI.
            if getattr(sys, "frozen", False):
                report = self._setup_ollama_fallback(
                    model_name=model_name,
                    api_base=api_base,
                    require_signin=True,
                )
            else:
                try:
                    report = self._run_script_json(
                        "scripts/setup_ollama.py",
                        [
                            "--model",
                            model_name,
                            "--api-base",
                            api_base,
                            "--signin",
                            "--install-python-deps",
                            "--python-deps-file",
                            "requirements-llm.txt",
                            "--json",
                        ],
                        timeout_seconds=4200,
                    )
                except FileNotFoundError:
                    report = self._setup_ollama_fallback(
                        model_name=model_name,
                        api_base=api_base,
                        require_signin=True,
                    )
            if not report:
                report = self._setup_ollama_fallback(
                    model_name=model_name,
                    api_base=api_base,
                    require_signin=True,
                )
            if not bool(report.get("ok", False)):
                detail = str(report.get("error") or "Falha na automacao do Ollama.")
                signin_url = str(report.get("signin_url") or "").strip()
                if signin_url:
                    detail += f"\n\nConclua o login da conta Ollama em:\n{signin_url}"
                deps_error = str(report.get("python_deps_error") or "").strip()
                if deps_error:
                    detail += f"\n\nDependencias Python cloud:\n{deps_error}"
                raise RuntimeError(detail)

            reachable = bool(report.get("service_reachable", False))
            pulled = bool(report.get("model_pulled", False))
            already = bool(report.get("model_already_available", False))
            signin_attempted = bool(report.get("signin_attempted", False))
            signin_ok = bool(report.get("signin_ok", False))
            signin_user = str(report.get("signin_user") or "").strip()

            self._set_backend_mode("cloud")
            self.llm_cloud_model_input.setText(f"ollama/{model_name}")
            self.llm_cloud_api_base_input.setText(str(report.get("api_base") or api_base))
            self._sync_llm_mode_controls()

            if pulled:
                model_text = "modelo baixado"
            elif already:
                model_text = "modelo ja disponivel"
            else:
                model_text = "modelo sem alteracoes"

            if reachable:
                service_text = "servico conectado"
            else:
                service_text = "servico nao conectado"

            if signin_attempted and signin_ok and signin_user:
                login_text = f"login confirmado ({signin_user})"
            elif signin_attempted and signin_ok:
                login_text = "login confirmado"
            elif signin_attempted:
                login_text = "login nao confirmado"
            else:
                login_text = "login nao verificado"

            self.ollama_status_label.setText(
                f"Status Ollama: {login_text}; {service_text}; {model_text}."
            )
            QMessageBox.information(
                self,
                "Ollama pronto",
                (
                    f"Login: {login_text}\n"
                    f"API base: {report.get('api_base')}\n"
                    f"Modelo: ollama/{model_name}\n"
                    f"Servico: {service_text}\n"
                    f"Resultado: {model_text}"
                ),
            )
        except Exception as exc:
            self.ollama_status_label.setText("Status Ollama: falha na automacao.")
            QMessageBox.critical(
                self,
                "Falha ao preparar Ollama",
                f"Nao foi possivel concluir a automacao:\n{exc}",
            )
        finally:
            self.ollama_setup_button.setEnabled(True)
            QApplication.restoreOverrideCursor()

    def _test_ollama_connection(self):
        api_base = self._normalize_ollama_api_base(self.llm_cloud_api_base_input.text().strip())
        self.ollama_status_label.setText("Status Ollama: testando conexao...")
        QApplication.processEvents()

        result = self._probe_ollama(api_base=api_base, timeout_seconds=2)
        if result.get("reachable"):
            models_count = int(result.get("models_count", 0) or 0)
            self.ollama_status_label.setText(
                f"Status Ollama: conectado em {result.get('api_base')} ({models_count} modelo(s))."
            )
            QMessageBox.information(
                self,
                "Ollama conectado",
                f"Conexao ok em {result.get('api_base')}\nModelos detectados: {models_count}",
            )
            return

        self.ollama_status_label.setText(
            f"Status Ollama: indisponivel em {result.get('api_base')}."
        )
        QMessageBox.warning(
            self,
            "Ollama indisponivel",
            (
                f"Nao foi possivel conectar ao Ollama em {result.get('api_base')}.\n"
                "Use o botao 'Login + preparar modelo' ou inicie manualmente com: ollama serve"
            ),
        )

    def _refresh_model_catalog(self):
        models_dir = self.models_dir_input.text().strip() or self.settings_model.paths.models_dir
        current_path = self.llm_model_path_input.text().strip()
        catalog = discover_gguf_models(models_dir)

        self.llm_model_combo.blockSignals(True)
        self.llm_model_combo.clear()
        self.llm_model_combo.addItem("Manual - manter caminho atual", "")

        selected_idx = 0
        for i, item in enumerate(catalog, start=1):
            label = f"{item.get('name')} - {item.get('size_mb', 0)} MB"
            model_path = str(item.get("path", ""))
            self.llm_model_combo.addItem(label, model_path)
            try:
                if current_path and Path(current_path).resolve() == Path(model_path).resolve():
                    selected_idx = i
            except Exception:
                pass

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
            self.llm_gpu_combo.addItem(f"GPU {idx}: {name} - {mem_mb} MB", idx)
            if idx == selected_index:
                preferred_idx = i
        self.llm_gpu_combo.setCurrentIndex(preferred_idx)

    def _sync_llm_mode_controls(self):
        backend = str(self.llm_backend_combo.currentData() or "local")
        mode = str(self.llm_device_mode_combo.currentData() or "auto")
        cpu_only = mode == "cpu_only"
        local_enabled = backend == "local"

        if self._llm_form is not None:
            for row in self._llm_local_rows:
                self._llm_form.setRowVisible(row, local_enabled)
            for row in self._llm_cloud_rows:
                self._llm_form.setRowVisible(row, not local_enabled)

        self.llm_model_combo.setEnabled(local_enabled)
        self.llm_model_path_input.setEnabled(local_enabled)
        self.llm_device_mode_combo.setEnabled(local_enabled)
        self.llm_gpu_combo.setEnabled(local_enabled)
        self.llm_n_ctx_spin.setEnabled(local_enabled)
        self.llm_n_gpu_layers_spin.setEnabled(local_enabled)
        self.llm_cpu_threads_spin.setEnabled(local_enabled and cpu_only)
        self.llm_download_choice_combo.setEnabled(local_enabled)
        self.llm_download_button.setEnabled(local_enabled)

        self.llm_cloud_model_input.setEnabled(not local_enabled)
        self.llm_cloud_api_base_input.setEnabled(not local_enabled)
        self.llm_cloud_api_version_input.setEnabled(not local_enabled)
        self.llm_cloud_organization_input.setEnabled(not local_enabled)
        self.llm_cloud_api_key_input.setEnabled(not local_enabled)
        self.llm_cloud_timeout_spin.setEnabled(not local_enabled)
        self.llm_cloud_max_retries_spin.setEnabled(not local_enabled)
        self.ollama_model_combo.setEnabled(not local_enabled)
        self.llm_cloud_ollama_preset_button.setEnabled(not local_enabled)
        self.ollama_setup_button.setEnabled(not local_enabled)
        self.ollama_probe_button.setEnabled(not local_enabled)

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

    @staticmethod
    def _format_size_bytes(size_bytes: int) -> str:
        value = float(max(0, int(size_bytes or 0)))
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        while value >= 1024.0 and idx < len(units) - 1:
            value /= 1024.0
            idx += 1
        return f"{value:.2f} {units[idx]}"

    def _download_selected_models(self):
        selection = str(self.llm_download_choice_combo.currentData() or "none")
        if selection == "none":
            QMessageBox.information(
                self,
                "Download de modelos",
                "Selecione TinyLlama, Qwen3 4B ou ambos para iniciar o download.",
            )
            return

        models_dir = self.models_dir_input.text().strip() or self.settings_model.paths.models_dir
        self.llm_download_button.setEnabled(False)
        self.llm_download_status_label.setText("Status de download: iniciando...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            if getattr(sys, "frozen", False):
                report = self._download_models_fallback(selection=selection, models_dir=models_dir)
            else:
                try:
                    report = self._run_script_json(
                        "scripts/install_llm_models.py",
                        [
                            "--model",
                            selection,
                            "--models-dir",
                            models_dir,
                            "--json",
                        ],
                        timeout_seconds=7200,
                    )
                except FileNotFoundError:
                    report = self._download_models_fallback(selection=selection, models_dir=models_dir)

            results = list(report.get("results", []))
            downloaded = [item for item in results if item.get("status") == "downloaded"]
            skipped = [item for item in results if item.get("status") == "skipped"]

            self._refresh_model_catalog()
            if not self.llm_model_path_input.text().strip():
                for item in downloaded + skipped:
                    path = str(item.get("path", "")).strip()
                    if path:
                        self.llm_model_path_input.setText(path)
                        break

            self.llm_download_status_label.setText(
                f"Status de download: concluido. Baixados={len(downloaded)} | ja existentes={len(skipped)}"
            )
            QMessageBox.information(
                self,
                "Download concluido",
                (
                    f"Modelos processados em:\n{report.get('models_dir')}\n\n"
                    f"Baixados: {len(downloaded)}\n"
                    f"Ja existentes: {len(skipped)}"
                ),
            )
        except Exception as exc:
            self.llm_download_status_label.setText("Status de download: falha.")
            QMessageBox.critical(
                self,
                "Falha no download",
                f"Nao foi possivel baixar os modelos:\n{exc}",
            )
        finally:
            self.llm_download_button.setEnabled(True)
            QApplication.restoreOverrideCursor()

    def _download_models_fallback(self, selection: str, models_dir: str) -> dict:
        def _on_progress(file_name: str, downloaded: int, total: int):
            if total > 0:
                pct = (downloaded / total) * 100.0
                text = (
                    f"Status de download: {file_name} "
                    f"{pct:5.1f}% - {self._format_size_bytes(downloaded)} / {self._format_size_bytes(total)}"
                )
            else:
                text = f"Status de download: {file_name} {self._format_size_bytes(downloaded)}"
            self.llm_download_status_label.setText(text)
            QApplication.processEvents()

        try:
            return install_models(
                selection=selection,
                models_dir=models_dir,
                force=False,
                dry_run=False,
                progress_callback=_on_progress,
            )
        except ModelInstallError as exc:
            raise RuntimeError(str(exc)) from exc

    def _run_script_json(
        self,
        script_relative_path: str,
        args: list[str],
        timeout_seconds: int = 600,
    ) -> dict:
        script_path = self._project_root() / script_relative_path
        if not script_path.exists():
            raise FileNotFoundError(f"Script nao encontrado: {script_path}")

        command: list[str]
        if getattr(sys, "frozen", False):
            if os.access(str(script_path), os.X_OK):
                command = [str(script_path), *args]
            else:
                exe_dir = Path(sys.executable).resolve().parent
                candidate_bins = [
                    exe_dir / "python3",
                    exe_dir / "python",
                ]
                py_bin = ""
                for candidate in candidate_bins:
                    if candidate.exists() and os.access(str(candidate), os.X_OK):
                        py_bin = str(candidate)
                        break
                if not py_bin:
                    py_bin = shutil.which("python3") or shutil.which("python") or ""
                if not py_bin:
                    raise RuntimeError(
                        "Nao foi possivel executar o script no pacote: interpretador Python nao encontrado."
                    )
                command = [py_bin, str(script_path), *args]
        else:
            command = [sys.executable, str(script_path), *args]

        proc = subprocess.run(
            command,
            cwd=str(self._project_root()),
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout_seconds)),
            check=False,
        )

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            if not detail:
                detail = f"Codigo de saida: {proc.returncode}"
            raise RuntimeError(detail)

        output = str(proc.stdout or "").strip()
        if not output:
            return {}

        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                return parsed
            return {"result": parsed}
        except json.JSONDecodeError:
            parsed = self._extract_last_json_object(output)
            if isinstance(parsed, dict):
                return parsed
            raise RuntimeError("Script retornou saida invalida para JSON.")

    @staticmethod
    def _extract_last_json_object(text: str) -> dict | None:
        value = str(text or "").strip()
        if not value:
            return None
        for idx in range(len(value) - 1, -1, -1):
            if value[idx] != "{":
                continue
            candidate = value[idx:].strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
        return None

    def _project_root(self) -> Path:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates = []
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                candidates.append(Path(meipass))
            candidates.append(exe_dir)
            candidates.append(exe_dir / "_internal")
            for candidate in candidates:
                if (candidate / "scripts" / "setup_ollama.py").exists():
                    return candidate
            return candidates[0] if candidates else exe_dir
        return Path(__file__).resolve().parents[3]

    @classmethod
    def _normalize_ollama_api_base(cls, api_base: str) -> str:
        value = str(api_base or "").strip().rstrip("/")
        if not value:
            return cls.OLLAMA_DEFAULT_API_BASE
        try:
            parsed = urlsplit(value)
        except Exception:
            return value
        if not parsed.scheme:
            return value
        host = (parsed.hostname or "").strip().lower()
        if host != "localhost":
            return value
        netloc = "127.0.0.1"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")

    @staticmethod
    def _extract_ollama_model_name(model_text: str) -> str:
        value = str(model_text or "").strip()
        if not value:
            return ""
        if value.lower().startswith("ollama/"):
            _, short = value.split("/", 1)
            return short.strip()
        return value

    def _probe_ollama(self, api_base: str, timeout_seconds: int = 2) -> dict:
        target = self._normalize_ollama_api_base(api_base)
        url = f"{target}/api/tags"
        req = urllib_request.Request(url, method="GET")
        opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=max(1, int(timeout_seconds))) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                payload = json.loads(body or "{}")
            models = payload.get("models", []) if isinstance(payload, dict) else []
            names = []
            for item in models:
                if isinstance(item, dict):
                    name = str(item.get("name") or "").strip()
                    if name:
                        names.append(name)
            return {
                "reachable": True,
                "api_base": target,
                "models_count": len(names),
                "models": names[:20],
            }
        except urllib_error.URLError as exc:
            return {
                "reachable": False,
                "api_base": target,
                "error": str(getattr(exc, "reason", exc)),
            }
        except Exception as exc:
            return {
                "reachable": False,
                "api_base": target,
                "error": str(exc),
            }

    @staticmethod
    def _find_ollama_binary() -> str | None:
        candidates = []
        env_bin = str(os.environ.get("OLLAMA_BIN", "") or "").strip()
        if env_bin:
            candidates.append(Path(env_bin).expanduser())
        which_bin = shutil.which("ollama")
        if which_bin:
            candidates.append(Path(which_bin))
        candidates.append(Path.home() / ".local" / "bin" / "ollama")
        candidates.append(Path("/usr/bin/ollama"))

        for candidate in candidates:
            try:
                resolved = candidate.expanduser().resolve()
            except Exception:
                resolved = candidate
            if resolved.exists() and os.access(resolved, os.X_OK):
                return str(resolved)
        return None

    @staticmethod
    def _extract_ollama_connect_url(text: str) -> str:
        match = re.search(r"https?://ollama\.com/connect[^\s'\"]+", str(text or ""))
        return str(match.group(0)).strip() if match else ""

    @staticmethod
    def _extract_ollama_signed_user(text: str) -> str:
        match = re.search(r"signed in as user ['\"]([^'\"]+)['\"]", str(text or ""), flags=re.IGNORECASE)
        return str(match.group(1)).strip() if match else ""

    def _run_ollama_signin_fallback(self, ollama_bin: str, timeout_seconds: int = 900) -> dict:
        try:
            proc = subprocess.run(
                [ollama_bin, "signin"],
                capture_output=True,
                text=True,
                timeout=max(15, int(timeout_seconds)),
                check=False,
            )
            stdout = str(proc.stdout or "").strip()
            stderr = str(proc.stderr or "").strip()
            combined = "\n".join(part for part in (stdout, stderr) if part).strip()
            signin_url = self._extract_ollama_connect_url(combined)
            signin_user = self._extract_ollama_signed_user(combined)
            if proc.returncode != 0:
                detail = stderr or stdout or f"ollama signin retornou codigo {proc.returncode}"
                return {
                    "ok": False,
                    "error": detail,
                    "signin_url": signin_url,
                    "signin_user": signin_user,
                }
            return {
                "ok": True,
                "error": "",
                "signin_url": signin_url,
                "signin_user": signin_user,
            }
        except subprocess.TimeoutExpired as exc:
            partial = "\n".join(
                part for part in (str(exc.stdout or "").strip(), str(exc.stderr or "").strip()) if part
            ).strip()
            return {
                "ok": False,
                "error": "Timeout no login do Ollama. Conclua a autenticacao no navegador e tente novamente.",
                "signin_url": self._extract_ollama_connect_url(partial),
                "signin_user": "",
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Falha ao executar 'ollama signin': {exc}",
                "signin_url": "",
                "signin_user": "",
            }

    def _setup_ollama_fallback(self, model_name: str, api_base: str, require_signin: bool = False) -> dict:
        ollama_bin = self._find_ollama_binary()
        if not ollama_bin:
            return {
                "ok": False,
                "api_base": api_base,
                "error": "Binario 'ollama' nao encontrado no PATH.",
            }

        probe = self._probe_ollama(api_base=api_base, timeout_seconds=2)
        service_started = False
        if not probe.get("reachable"):
            env = os.environ.copy()
            env["OLLAMA_HOST"] = api_base
            kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "env": env}
            if os.name != "nt":
                kwargs["start_new_session"] = True
            try:
                subprocess.Popen([ollama_bin, "serve"], **kwargs)
                service_started = True
            except Exception as exc:
                return {
                    "ok": False,
                    "api_base": api_base,
                    "error": f"Falha ao iniciar ollama serve: {exc}",
                }

            deadline = time.time() + 20.0
            while time.time() < deadline:
                probe = self._probe_ollama(api_base=api_base, timeout_seconds=1)
                if probe.get("reachable"):
                    break
                time.sleep(0.35)

        if not probe.get("reachable"):
            return {
                "ok": False,
                "api_base": api_base,
                "service_started": service_started,
                "error": f"Nao foi possivel conectar ao Ollama em {api_base}.",
            }

        signin_attempted = bool(require_signin)
        signin_ok = False
        signin_user = ""
        signin_url = ""
        if require_signin:
            signin_result = self._run_ollama_signin_fallback(ollama_bin=ollama_bin)
            signin_ok = bool(signin_result.get("ok", False))
            signin_user = str(signin_result.get("signin_user", "") or "")
            signin_url = str(signin_result.get("signin_url", "") or "")
            if not signin_ok:
                return {
                    "ok": False,
                    "api_base": api_base,
                    "service_started": service_started,
                    "signin_attempted": True,
                    "signin_ok": False,
                    "signin_user": signin_user,
                    "signin_url": signin_url,
                    "error": str(signin_result.get("error") or "Falha no login do Ollama."),
                }

        models = set(str(name).strip() for name in probe.get("models", []) if str(name).strip())
        already = model_name in models
        pulled = False
        if not already:
            env = os.environ.copy()
            env["OLLAMA_HOST"] = api_base
            proc = subprocess.run(
                [ollama_bin, "pull", model_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=3600,
                check=False,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip() or f"Codigo de saida: {proc.returncode}"
                return {
                    "ok": False,
                    "api_base": api_base,
                    "service_started": service_started,
                    "error": f"Falha ao baixar modelo no Ollama: {detail}",
                }

            probe_after_pull = self._probe_ollama(api_base=api_base, timeout_seconds=2)
            models_after = set(
                str(name).strip() for name in probe_after_pull.get("models", []) if str(name).strip()
            )
            pulled = model_name in models_after
            probe = probe_after_pull

        return {
            "ok": True,
            "api_base": api_base,
            "service_reachable": bool(probe.get("reachable", False)),
            "service_was_running": not service_started,
            "service_started": service_started,
            "signin_attempted": signin_attempted,
            "signin_ok": signin_ok,
            "signin_user": signin_user,
            "signin_url": signin_url,
            "model_already_available": already,
            "model_pulled": pulled,
            "models_count": int(probe.get("models_count", 0) or 0),
            "error": "",
        }

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

    def _skip_onboarding(self):
        self.config_manager.set("ui/show_onboarding_dialog", False)
        self.config_manager.set("ui/onboarding_preference_set", True)
        self.config_manager.set("ui/onboarding_dialog_version", self.ONBOARDING_VERSION)

        payload = self.settings_model.model_dump()
        payload["theme"] = "philosophy_dark"
        payload["ui"] = {
            "show_onboarding_dialog": False,
            "onboarding_preference_set": True,
            "onboarding_dialog_version": self.ONBOARDING_VERSION,
        }
        self.onboarding_preferences_saved.emit(payload)
        self.reject()

    def _save_and_accept(self):
        try:
            user_name = self.user_name_input.text().strip()
            assistant_name = self.assistant_name_input.text().strip()
            selected_theme = "philosophy_dark"
            show_on_start = not self.hide_on_start_check.isChecked()

            vault_path = self.vault_path_input.text().strip()
            if not vault_path:
                raise ValueError("Defina um caminho de vault valido.")

            self.settings_model.paths.vault = vault_path
            self.settings_model.paths.data_dir = self.data_dir_input.text().strip()
            self.settings_model.paths.models_dir = self.models_dir_input.text().strip()
            self.settings_model.paths.exports_dir = self.exports_dir_input.text().strip()
            self.settings_model.paths.cache_dir = self.cache_dir_input.text().strip()

            self.settings_model.llm.backend = str(self.llm_backend_combo.currentData() or "local")
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

            cloud_model = self.llm_cloud_model_input.text().strip()
            if self.settings_model.llm.backend == "cloud" and not cloud_model:
                fallback_ollama_model = str(
                    self.ollama_model_combo.currentData() or self.OLLAMA_CLOUD_DEFAULT_MODEL
                ).strip()
                cloud_model = f"ollama/{fallback_ollama_model}"

            cloud_api_base = self.llm_cloud_api_base_input.text().strip()
            if cloud_model.lower().startswith("ollama/"):
                cloud_api_base = self._normalize_ollama_api_base(cloud_api_base)

            self.settings_model.llm.cloud.model = cloud_model
            self.settings_model.llm.cloud.api_base = cloud_api_base
            self.settings_model.llm.cloud.api_version = self.llm_cloud_api_version_input.text().strip()
            self.settings_model.llm.cloud.organization = self.llm_cloud_organization_input.text().strip()
            self.settings_model.llm.cloud.api_key = self.llm_cloud_api_key_input.text().strip()
            self.settings_model.llm.cloud.timeout_seconds = self.llm_cloud_timeout_spin.value()
            self.settings_model.llm.cloud.max_retries = self.llm_cloud_max_retries_spin.value()

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
            self.config_manager.set("ui/onboarding_preference_set", True)
            self.config_manager.set("ui/onboarding_dialog_version", self.ONBOARDING_VERSION)

            payload = updated_settings.model_dump()
            payload["theme"] = selected_theme
            payload["ui"] = {
                "show_onboarding_dialog": show_on_start,
                "onboarding_preference_set": True,
                "onboarding_dialog_version": self.ONBOARDING_VERSION,
            }
            self.onboarding_preferences_saved.emit(payload)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao salvar onboarding",
                f"Nao foi possivel salvar as configuracoes iniciais:\n{exc}",
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
