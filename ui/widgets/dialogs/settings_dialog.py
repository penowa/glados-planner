"""
Dialog para edição das configurações principais do sistema.
"""
import os
import re
import shutil
from pathlib import Path
import subprocess
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget,
    QFormLayout, QDialogButtonBox, QFileDialog, QMessageBox, QSizePolicy,
    QTextBrowser, QTextEdit, QKeySequenceEdit,
    QGridLayout, QButtonGroup
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence

from core.config.settings import Settings, reload_settings
from core.llm.runtime_discovery import detect_nvidia_gpus, discover_gguf_models
from core.modules.zathura_config_manager import ZathuraConfigManager
from ui.utils.config_manager import ConfigManager
from ui.utils.session_keybindings import SESSION_SHORTCUT_DEFINITIONS, default_session_shortcuts


ZATHURA_KEYMAP_DEFINITIONS = [
    {"id": "capture_citation", "label": "Criar bookmark de citação", "default_key": "zb", "command": 'feedkeys ":bmark "'},
    {"id": "reload", "label": "Recarregar documento", "default_key": "r", "command": "reload"},
    {"id": "toggle_fullscreen", "label": "Alternar tela cheia", "default_key": "f", "command": "toggle_fullscreen"},
    {"id": "scroll_down", "label": "Scroll para baixo", "default_key": "J", "command": "scroll down"},
    {"id": "scroll_up", "label": "Scroll para cima", "default_key": "K", "command": "scroll up"},
    {"id": "zoom_in", "label": "Aumentar zoom", "default_key": "+", "command": "zoom in"},
    {"id": "zoom_out", "label": "Diminuir zoom", "default_key": "-", "command": "zoom out"},
]

ZATHURA_REFERENCE_SECTIONS = [
    (
        "General",
        [
            ("J, PgDn", "Go to the next page"),
            ("K, PgUp", "Go to the previous page"),
            ("h, k, j, l", "Scroll to the left, down, up or right direction"),
            ("Left, Down, Up, Right", "Scroll to the left, down, up or right direction"),
            ("^t, ^d, ^u, ^y", "Scroll a half page left, down, up or right"),
            ("t, ^f, ^b, space, , y", "Scroll a full page left, down, up or right"),
            ("gg, G, nG", "Goto to the first, the last or to the nth page"),
            ("P", "Snaps to the current page"),
            ("H, L", "Goto top or bottom of the current page"),
            ("^o, ^i", "Move backward and forward through the jump list"),
            ("^j, ^k", "Bisect forward and backward between the last two jump points"),
            ("^c, Escape", "Abort"),
            ("a, s", "Adjust window in best-fit or width mode"),
            ("/, ?", "Search for text"),
            ("n, N", "Search for the next or previous result"),
            ("o, O", "Open document"),
            ("f", "Follow links"),
            ("F", "Display link target"),
            ("c", "Copy link target into the clipboard"),
            ("\\:", "Enter command"),
            ("r", "Rotate by 90 degrees"),
            ("^r", "Recolor (grayscale and invert colors)"),
            ("R", "Reload document"),
            ("Tab", "Show index and switch to Index mode"),
            ("d", "Toggle dual page view"),
            ("D", "Cycle opening column in dual page view"),
            ("F5", "Switch to presentation mode"),
            ("F11", "Switch to fullscreen mode"),
            ("^m", "Toggle inputbar"),
            ("^n", "Toggle statusbar"),
            ("+, -, =", "Zoom in, out or to the original size"),
            ("zI, zO, z0", "Zoom in, out or to the original size"),
            ("n=", "Zoom to size n"),
            ("mX", "Set a quickmark to a letter or number X"),
            ("'X", "Goto quickmark saved at letter or number X"),
            ("q", "Quit"),
        ],
    ),
    (
        "Fullscreen mode",
        [
            ("J, K", "Go to the next or previous page"),
            ("space, ,", "Scroll a full page down or up"),
            ("gg, G, nG", "Goto to the first, the last or to the nth page"),
            ("^c, Escape", "Abort"),
            ("F11", "Switch to normal mode"),
            ("+, -, =", "Zoom in, out or to the original size"),
            ("zI, zO, z0", "Zoom in, out or to the original size"),
            ("n=", "Zoom to size n"),
            ("q", "Quit"),
        ],
    ),
    (
        "Presentation mode",
        [
            ("space, ,", "Scroll a full page down or up"),
            ("^c, Escape", "Abort"),
            ("F5", "Switch to normal mode"),
            ("q", "Quit"),
        ],
    ),
    (
        "Index mode",
        [
            ("k, j", "Move to upper or lower entry"),
            ("l", "Expand entry"),
            ("L", "Expand all entries"),
            ("h", "Collapse entry"),
            ("H", "Collapse all entries"),
            ("space, Return", "Select and open entry"),
        ],
    ),
]

ZATHURA_MOUSE_BINDINGS = [
    ("Scroll", "Scroll up or down"),
    ("^Scroll", "Zoom in or out"),
    ("Drag Button2 (middle button drag)", "Pan the document"),
    ("Button1 (left click)", "Follow link"),
    ("Drag Button1", "Select text"),
    ("Drag S-Button1", "Highlight region"),
    (
        "Button3 (right click)",
        "Open popup menu to copy/save image (activates for images recognized by export command)",
    ),
]

ZATHURA_COMMANDS = [
    ("bmark", "Save a bookmark"),
    ("bdelete", "Delete a bookmark"),
    ("blist", "List bookmarks"),
    ("bjump", "Jump to given bookmark"),
    (
        "jumplist",
        'Show recent jumps in jumplist (by default last 5). Optional argument specifies number of entries to show. Negative value "-N" shows all except the first "N" entries',
    ),
    ("mark", "Set a quickmark"),
    ("delmarks", "Delete a quickmark. Abbreviation: delm"),
    ("close", "Close document"),
    ("quit", "Quit zathura. Abbreviation: q"),
    ("exec", "Execute an external command. $FILE expands to the current document path, $PAGE to the current page number, and $DBUS to the bus name of the D-Bus interface. Alias: ! (space is still needed after)"),
    ("info", "Show document information"),
    ("open", "Open a document. Abbreviation: o"),
    ("offset", "Set page offset"),
    ("print", "Print document"),
    ("write(!)", "Save document (and force overwriting). Alias: save(!)"),
    ("export", "Export attachments. First argument specifies the attachment identifier (use completion with Tab), second argument gives the target filename (relative to current working directory)"),
    ("dump", "Write values, descriptions, etc. of all current settings to a file"),
    ("source", "Source a configuration file. It is possible to change the config directory by passing an argument"),
    ("hlsearch", "Highlight current search results"),
    ("nohlsearch", "Remove highlights of current search results. Abbreviation: nohl"),
    ("version", "Show version information."),
]


class ZathuraKeybindingsDialog(QDialog):
    """Painel de configuracao de keybindings do Zathura e da SessionView."""

    def __init__(
        self,
        model_getter: Callable[[], Any],
        apply_callback: Callable[[Any], tuple[bool, str]],
        session_shortcuts_getter: Callable[[], dict[str, str]],
        session_shortcuts_setter: Callable[[dict[str, str]], None],
        parent=None,
    ):
        super().__init__(parent)
        self._model_getter = model_getter
        self._apply_callback = apply_callback
        self._session_shortcuts_getter = session_shortcuts_getter
        self._session_shortcuts_setter = session_shortcuts_setter
        self._zathura_key_inputs: dict[str, QLineEdit] = {}
        self._session_key_inputs: dict[str, QKeySequenceEdit] = {}
        self._unmapped_keymap_lines: list[str] = []

        self.setWindowTitle("Keybindings do Zathura")
        self.resize(760, 720)
        self.setModal(True)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Configure os atalhos principais do Zathura e da sessao de leitura. "
            "Atalhos extras ja existentes no zathurarc serao preservados."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        content_tabs = QTabWidget()
        layout.addWidget(content_tabs, 1)

        editor_tab = QWidget()
        editor_layout = QVBoxLayout(editor_tab)

        zathura_form = QFormLayout()
        for item in ZATHURA_KEYMAP_DEFINITIONS:
            key_input = QLineEdit()
            key_input.setPlaceholderText(item["default_key"])
            self._zathura_key_inputs[item["id"]] = key_input
            zathura_form.addRow(f"{item['label']}:", key_input)
        editor_layout.addLayout(zathura_form)

        self.preserved_keymaps_label = QLabel("")
        self.preserved_keymaps_label.setWordWrap(True)
        self.preserved_keymaps_label.setStyleSheet("color: #8F8F8F; font-size: 12px;")
        editor_layout.addWidget(self.preserved_keymaps_label)

        session_title = QLabel("Atalhos da SessionView")
        session_title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        editor_layout.addWidget(session_title)

        session_form = QFormLayout()
        for item in SESSION_SHORTCUT_DEFINITIONS:
            key_input = QKeySequenceEdit()
            key_input.setClearButtonEnabled(True)
            self._session_key_inputs[item["id"]] = key_input
            session_form.addRow(f"{item['label']}:", key_input)
        editor_layout.addLayout(session_form)
        editor_layout.addStretch()

        reference_tab = QWidget()
        reference_layout = QVBoxLayout(reference_tab)
        self.reference_browser = QTextBrowser()
        self.reference_browser.setOpenExternalLinks(False)
        self.reference_browser.setHtml(self._build_reference_html())
        reference_layout.addWidget(self.reference_browser)

        content_tabs.addTab(editor_tab, "Editar")
        content_tabs.addTab(reference_tab, "Referencia")

        action_row = QHBoxLayout()
        self.restore_defaults_button = QPushButton("Restaurar padroes")
        self.save_apply_button = QPushButton("Salvar e aplicar")
        action_row.addWidget(self.restore_defaults_button)
        action_row.addStretch(1)
        action_row.addWidget(self.save_apply_button)
        layout.addLayout(action_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

        self.restore_defaults_button.clicked.connect(self._restore_defaults)
        self.save_apply_button.clicked.connect(self._save_and_apply)

        self._load_values()

    def _build_reference_html(self) -> str:
        sections = [
            "<html><head><style>"
            "body { font-family: sans-serif; color: #E6E6E6; background: #171717; }"
            "h2 { color: #F1F1F1; margin-top: 18px; }"
            "h3 { color: #D6D6D6; margin-top: 16px; }"
            "table { border-collapse: collapse; width: 100%; margin-top: 8px; margin-bottom: 14px; }"
            "th, td { border: 1px solid #3F3F3F; padding: 8px; text-align: left; vertical-align: top; }"
            "th { background: #222222; }"
            "td:first-child { white-space: nowrap; width: 28%; color: #A9D1FF; }"
            "code { color: #A9D1FF; }"
            "</style></head><body>",
            "<h2>Mouse and Key Bindings</h2>",
        ]

        for title, rows in ZATHURA_REFERENCE_SECTIONS:
            sections.append(f"<h3>{title}</h3>")
            sections.append("<table><tr><th>Input</th><th>Description</th></tr>")
            for key, description in rows:
                sections.append(f"<tr><td><code>{key}</code></td><td>{description}</td></tr>")
            sections.append("</table>")

        sections.append("<h3>Mouse bindings</h3>")
        sections.append("<table><tr><th>Input</th><th>Description</th></tr>")
        for key, description in ZATHURA_MOUSE_BINDINGS:
            sections.append(f"<tr><td><code>{key}</code></td><td>{description}</td></tr>")
        sections.append("</table>")

        sections.append("<h3>Commands</h3>")
        sections.append("<table><tr><th>Command</th><th>Description</th></tr>")
        for command, description in ZATHURA_COMMANDS:
            sections.append(f"<tr><td><code>{command}</code></td><td>{description}</td></tr>")
        sections.append("</table></body></html>")
        return "".join(sections)

    def _load_values(self):
        model = self._model_getter()
        mapped_keys, self._unmapped_keymap_lines = self._parse_known_keymaps(getattr(model, "keymaps", []) or [])
        for item in ZATHURA_KEYMAP_DEFINITIONS:
            self._zathura_key_inputs[item["id"]].setText(mapped_keys.get(item["id"], item["default_key"]))

        self.preserved_keymaps_label.setText(
            f"Linhas extras preservadas automaticamente: {len(self._unmapped_keymap_lines)}"
        )

        session_shortcuts = self._session_shortcuts_getter()
        defaults = default_session_shortcuts()
        for item in SESSION_SHORTCUT_DEFINITIONS:
            sequence = str(session_shortcuts.get(item["id"], defaults[item["id"]]) or "").strip()
            self._session_key_inputs[item["id"]].setKeySequence(QKeySequence(sequence))

    def _parse_known_keymaps(self, keymaps: list[str]) -> tuple[dict[str, str], list[str]]:
        command_to_id = {item["command"]: item["id"] for item in ZATHURA_KEYMAP_DEFINITIONS}
        known: dict[str, str] = {}
        unknown: list[str] = []
        for raw_line in keymaps:
            line = str(raw_line or "").strip()
            match = re.match(r"^map\s+(\S+)\s+(.+)$", line)
            if not match:
                if line:
                    unknown.append(line)
                continue
            key_text = match.group(1).strip()
            command_text = match.group(2).strip()
            action_id = command_to_id.get(command_text)
            if action_id and action_id not in known:
                known[action_id] = key_text
            else:
                unknown.append(line)
        return known, unknown

    def _restore_defaults(self):
        for item in ZATHURA_KEYMAP_DEFINITIONS:
            self._zathura_key_inputs[item["id"]].setText(item["default_key"])
        defaults = default_session_shortcuts()
        for item in SESSION_SHORTCUT_DEFINITIONS:
            self._session_key_inputs[item["id"]].setKeySequence(QKeySequence(defaults[item["id"]]))

    def _save_and_apply(self):
        model = self._model_getter()
        new_keymaps: list[str] = []
        for item in ZATHURA_KEYMAP_DEFINITIONS:
            key_text = self._zathura_key_inputs[item["id"]].text().strip()
            if key_text:
                new_keymaps.append(f"map {key_text} {item['command']}")
        new_keymaps.extend(self._unmapped_keymap_lines)
        model.keymaps = new_keymaps

        session_shortcuts: dict[str, str] = {}
        for item in SESSION_SHORTCUT_DEFINITIONS:
            sequence = self._session_key_inputs[item["id"]].keySequence().toString(
                QKeySequence.SequenceFormat.PortableText
            ).strip()
            session_shortcuts[item["id"]] = sequence

        self._session_shortcuts_setter(session_shortcuts)
        success, message = self._apply_callback(model)
        if success:
            QMessageBox.information(self, "Zathura", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Zathura", message)


class SettingsDialog(QDialog):
    """Dialog para controle de configurações do sistema."""

    settings_saved = pyqtSignal(dict)
    BACKEND_LABELS = [
        ("LLM local (GGUF)", "local"),
        ("LLM em nuvem (LiteLLM)", "cloud"),
    ]
    DEVICE_MODE_LABELS = [
        ("Automático (recomendado)", "auto"),
        ("Somente CPU (mais compatível)", "cpu_only"),
        ("Preferir GPU (com fallback para CPU)", "gpu_prefer"),
        ("Somente GPU (sem fallback)", "gpu_only"),
    ]
    PERSONALITY_PROFILE_LABELS = [
        ("Automático", "auto"),
        ("GLaDOS", "glados"),
        ("Marvin", "marvin"),
    ]
    SECONDARY_BUTTON_PALETTE = [
        "#FFFFFF",
        "#ECECEC",
        "#D8D8D8",
        "#CFCFCF",
        "#BFBFBF",
        "#AFAFAF",
        "#9A9A9A",
        "#8A8A8A",
        "#6F6F6F",
        "#4F4F4F",
    ]
    ZATHURA_PRESETS = [
        ("classic", "Classico"),
        ("pywal", "Pywal"),
        ("focus", "Foco"),
        ("midnight_lilac", "Lilac Night"),
    ]

    def __init__(self, parent=None, settings_path: str = "config/settings.yaml"):
        super().__init__(parent)
        self.settings_path = settings_path
        self.settings_model = Settings.from_yaml(settings_path)
        self.config_manager = ConfigManager.instance()
        self._zathura_working_model = self.settings_model.zathura.model_copy(deep=True)
        self._llm_form = None
        self._llm_local_rows = []
        self._llm_cloud_rows = []
        self._secondary_color_buttons: dict[str, QPushButton] = {}
        self._selected_secondary_button_color = "#FFFFFF"
        self._zathura_preset_buttons: dict[str, QPushButton] = {}

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
        self._setup_zathura_tab()
        self._setup_appearance_tab()
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
        self._apply_compact_control_style()

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
        auto_paths_note = QLabel(
            "Pastas de dados são gerenciadas automaticamente em data/ ao lado do executável."
        )
        auto_paths_note.setWordWrap(True)
        auto_paths_note.setStyleSheet("color: #8F8F8F; font-size: 12px;")

        form.addRow("Diretório de dados (automático):", self.data_dir_input)
        form.addRow("Diretório de modelos (automático):", self.models_dir_input)
        form.addRow("Diretório de exportações (automático):", self.exports_dir_input)
        form.addRow("Diretório de cache (automático):", self.cache_dir_input)
        form.addRow("", auto_paths_note)

        self.tabs.addTab(tab, "Paths")

    def _setup_llm_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self._llm_form = form
        self._llm_local_rows = []
        self._llm_cloud_rows = []

        self.llm_backend_combo = QComboBox()
        for label, value in self.BACKEND_LABELS:
            self.llm_backend_combo.addItem(label, value)
        self.llm_backend_combo.currentIndexChanged.connect(self._sync_llm_mode_controls)
        self.personality_profile_combo = QComboBox()
        for label, value in self.PERSONALITY_PROFILE_LABELS:
            self.personality_profile_combo.addItem(label, value)
        self.personality_profile_combo.currentIndexChanged.connect(self._sync_personality_profile_summary)
        self.personality_profile_summary_label = QLabel("")
        self.personality_profile_summary_label.setWordWrap(True)
        self.personality_profile_summary_label.setStyleSheet("color: #8F8F8F; font-size: 12px;")
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
        self.llm_cloud_model_input = QLineEdit()
        self.llm_cloud_model_input.setPlaceholderText("ollama/qwen2.5:1.5b ou openai/gpt-4o-mini")
        self.llm_cloud_api_base_input = QLineEdit()
        self.llm_cloud_api_base_input.setPlaceholderText("http://127.0.0.1:11434")
        self.llm_cloud_api_version_input = QLineEdit()
        self.llm_cloud_organization_input = QLineEdit()
        self.llm_cloud_api_key_input = QLineEdit()
        self.llm_cloud_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_cloud_timeout_spin = QSpinBox()
        self.llm_cloud_timeout_spin.setRange(5, 600)
        self.llm_cloud_timeout_spin.setSuffix(" s")
        self.llm_cloud_max_retries_spin = QSpinBox()
        self.llm_cloud_max_retries_spin.setRange(0, 10)
        llm_help = QLabel(
            "Dica rápida: use 'Automático' e ajuste apenas se souber o que está fazendo."
        )
        llm_help.setWordWrap(True)
        llm_help.setStyleSheet("color: #8F8F8F; font-size: 12px;")

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

        cloud_model_layout = QHBoxLayout()
        cloud_model_layout.addWidget(self.llm_cloud_model_input)
        self.llm_cloud_ollama_preset_button = QPushButton("Preset Ollama local")
        self.llm_cloud_ollama_preset_button.clicked.connect(self._apply_ollama_cloud_preset)
        cloud_model_layout.addWidget(self.llm_cloud_ollama_preset_button)

        self._add_llm_row("Nome do usuário (dashboard):", self.llm_user_name_input)
        self._add_llm_row("Nome do assistente:", self.llm_assistant_name_input)
        self._add_llm_row("Perfil da personalidade:", self.personality_profile_combo)
        self._add_llm_row("", self.personality_profile_summary_label)
        self._add_llm_row("Backend da LLM:", self.llm_backend_combo)
        self._add_llm_row("", llm_help)
        self._add_llm_row("Modelos encontrados (.gguf):", model_catalog_layout, scope="local")
        self._add_llm_row("Arquivo do modelo:", model_path_layout, scope="local")
        self._add_llm_row("Como rodar o modelo:", self.llm_device_mode_combo, scope="local")
        self._add_llm_row("GPU disponível:", gpu_layout, scope="local")
        self._add_llm_row("Tamanho de contexto (n_ctx):", self.llm_n_ctx_spin, scope="local")
        self._add_llm_row("Camadas na GPU (n_gpu_layers):", self.llm_n_gpu_layers_spin, scope="local")
        self._add_llm_row("Threads de CPU (somente CPU):", self.llm_cpu_threads_spin, scope="local")
        self._add_llm_row("Criatividade (temperature):", self.llm_temperature_spin)
        self._add_llm_row("Foco na resposta (top-p):", self.llm_top_p_spin)
        self._add_llm_row("Limite de tokens por resposta:", self.llm_max_tokens_spin)
        self._add_llm_row("Modelo cloud (LiteLLM):", cloud_model_layout, scope="cloud")
        self._add_llm_row("Timeout cloud:", self.llm_cloud_timeout_spin, scope="cloud")
        self._add_llm_row("Tentativas cloud:", self.llm_cloud_max_retries_spin, scope="cloud")

        self._sync_personality_profile_summary()
        self.tabs.addTab(tab, "LLM")

    def _add_llm_row(self, label: str, field, scope: str = "common"):
        if self._llm_form is None:
            return
        row = self._llm_form.rowCount()
        self._llm_form.addRow(label, field)
        if scope == "local":
            self._llm_local_rows.append(row)
        elif scope == "cloud":
            self._llm_cloud_rows.append(row)

    @staticmethod
    def _set_compact_button(button: QPushButton, min_width: int = 90):
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

    def _setup_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        helper = QLabel(
            "Cor secundária dos botões.\n"
            "Padrão: branco. Essa cor é aplicada globalmente no tema."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #8F8F8F; font-size: 12px;")
        layout.addWidget(helper)

        palette_box = QWidget()
        palette_grid = QGridLayout(palette_box)
        palette_grid.setContentsMargins(0, 0, 0, 0)
        palette_grid.setHorizontalSpacing(12)
        palette_grid.setVerticalSpacing(12)
        self.secondary_color_group = QButtonGroup(self)
        self.secondary_color_group.setExclusive(True)

        columns = 5
        for idx, color in enumerate(self.SECONDARY_BUTTON_PALETTE):
            swatch = QPushButton("")
            swatch.setCheckable(True)
            swatch.setFixedSize(30, 30)
            swatch.setToolTip(color)
            swatch.clicked.connect(lambda _checked, chosen=color: self._select_secondary_button_color(chosen))
            self.secondary_color_group.addButton(swatch)
            self._secondary_color_buttons[color] = swatch
            row = idx // columns
            col = idx % columns
            palette_grid.addWidget(swatch, row, col)

        layout.addWidget(palette_box)
        layout.addStretch()
        self.tabs.addTab(tab, "Aparência")
        self._refresh_secondary_palette_styles()

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

    def _setup_zathura_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        self.zathura_preset_group = QButtonGroup(self)
        self.zathura_preset_group.setExclusive(True)

        preset_buttons = QHBoxLayout()
        for preset_id, label in self.ZATHURA_PRESETS:
            button = QPushButton(label)
            button.setCheckable(True)
            self.zathura_preset_group.addButton(button)
            self._zathura_preset_buttons[preset_id] = button
            preset_buttons.addWidget(button)
        layout.addLayout(preset_buttons)

        action_buttons = QHBoxLayout()
        self.zathura_apply_preset_button = QPushButton("Aplicar preset")
        self.zathura_test_button = QPushButton("Testar")
        self.zathura_panel_button = QPushButton("Configurar keybindings")
        action_buttons.addWidget(self.zathura_apply_preset_button)
        action_buttons.addWidget(self.zathura_test_button)
        action_buttons.addWidget(self.zathura_panel_button)
        layout.addLayout(action_buttons)
        layout.addStretch()

        self.zathura_apply_preset_button.clicked.connect(self._apply_selected_zathura_preset)
        self.zathura_test_button.clicked.connect(self._test_zathura_with_pdf)
        self.zathura_panel_button.clicked.connect(self._open_zathura_panel)
        self.tabs.addTab(tab, "Zathura")

    def _load_current_values(self):
        app = self.settings_model.app
        paths = self.settings_model.paths
        llm = self.settings_model.llm
        obsidian = self.settings_model.obsidian
        review_view = self.settings_model.review_view
        zathura = self.settings_model.zathura
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
        backend_value = str(getattr(llm, "backend", "local") or "local")
        backend_idx = self.llm_backend_combo.findData(backend_value)
        self.llm_backend_combo.setCurrentIndex(max(0, backend_idx))
        self._set_device_mode(getattr(llm, "device_mode", self._infer_device_mode(llm)))
        self.llm_n_ctx_spin.setValue(llm.n_ctx)
        self.llm_n_gpu_layers_spin.setValue(llm.n_gpu_layers)
        self.llm_cpu_threads_spin.setValue(max(1, int(getattr(llm.cpu, "threads", 4) or 4)))
        self.llm_temperature_spin.setValue(llm.temperature)
        self.llm_top_p_spin.setValue(llm.top_p)
        self.llm_max_tokens_spin.setValue(llm.max_tokens)
        cloud_cfg = getattr(llm, "cloud", None)
        self.llm_cloud_model_input.setText(str(getattr(cloud_cfg, "model", "ollama/qwen2.5:1.5b") or ""))
        self.llm_cloud_api_base_input.setText(str(getattr(cloud_cfg, "api_base", "") or ""))
        self.llm_cloud_api_version_input.setText(str(getattr(cloud_cfg, "api_version", "") or ""))
        self.llm_cloud_organization_input.setText(str(getattr(cloud_cfg, "organization", "") or ""))
        self.llm_cloud_api_key_input.setText(str(getattr(cloud_cfg, "api_key", "") or ""))
        self.llm_cloud_timeout_spin.setValue(int(getattr(cloud_cfg, "timeout_seconds", 120) or 120))
        self.llm_cloud_max_retries_spin.setValue(int(getattr(cloud_cfg, "max_retries", 1) or 1))
        self.llm_user_name_input.setText(llm.glados.user_name)
        self.llm_assistant_name_input.setText(llm.glados.glados_name)
        personality_profile = str(getattr(llm.glados, "personality_profile", "auto") or "auto").strip().lower()
        profile_idx = self.personality_profile_combo.findData(personality_profile)
        self.personality_profile_combo.setCurrentIndex(max(0, profile_idx))
        self._sync_personality_profile_summary()
        self._refresh_model_catalog()
        self._refresh_gpu_catalog(selected_index=int(getattr(llm, "gpu_index", 0) or 0))
        self._sync_llm_mode_controls()

        self.obsidian_templates_dir_input.setText(obsidian.templates_dir)
        self.obsidian_auto_sync_check.setChecked(obsidian.auto_sync)
        self.obsidian_sync_interval_spin.setValue(obsidian.sync_interval)

        self.review_prompt_enabled_check.setChecked(review_view.question_prompt_enabled)
        self.review_question_interval_spin.setValue(int(review_view.question_interval_minutes))
        self.review_arrow_pan_step_spin.setValue(int(review_view.arrow_pan_step))

        self._zathura_working_model = zathura.model_copy(deep=True)
        self._set_zathura_preset_selection(self._infer_zathura_preset(zathura))

        self.feature_llm.setChecked(features.enable_llm)
        self.feature_obsidian.setChecked(features.enable_obsidian_sync)
        self.feature_pomodoro.setChecked(features.enable_pomodoro)
        self.feature_translation.setChecked(features.enable_translation)
        self.feature_glados_personality.setChecked(features.enable_glados_personality)
        self.feature_vault_brain.setChecked(features.enable_vault_as_brain)
        self._selected_secondary_button_color = str(
            self.config_manager.get("ui/secondary_button_color", "#FFFFFF")
        ).strip().upper() or "#FFFFFF"
        if self._selected_secondary_button_color not in self._secondary_color_buttons:
            self._selected_secondary_button_color = "#FFFFFF"
        self._refresh_secondary_palette_styles()

    def _dump_option_pairs(self, values: dict) -> str:
        lines = []
        for key, value in values.items():
            lines.append(f"{key}={value}")
        return "\n".join(lines)

    def _parse_key_value_lines(self, raw_text: str) -> dict:
        data: dict[str, Any] = {}
        for raw_line in str(raw_text or "").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            normalized_key = key.strip()
            normalized_value = value.strip()
            if not normalized_key:
                continue
            lowered = normalized_value.lower()
            if lowered in {"true", "false"}:
                data[normalized_key] = lowered == "true"
                continue
            try:
                data[normalized_key] = int(normalized_value)
                continue
            except ValueError:
                pass
            try:
                data[normalized_key] = float(normalized_value)
                continue
            except ValueError:
                pass
            data[normalized_key] = normalized_value
        return data

    def _parse_nonempty_lines(self, raw_text: str) -> list[str]:
        return [line.strip() for line in str(raw_text or "").splitlines() if line.strip()]

    def _selected_zathura_preset(self) -> str:
        for preset_id, button in self._zathura_preset_buttons.items():
            if button.isChecked():
                return preset_id
        return "classic"

    def _set_zathura_preset_selection(self, preset_id: str):
        selected = preset_id if preset_id in self._zathura_preset_buttons else "classic"
        button = self._zathura_preset_buttons.get(selected)
        if button is not None:
            button.setChecked(True)

    def _infer_zathura_preset(self, model: Any) -> str:
        preset = str(getattr(model, "preset", "") or "").strip().lower()
        if preset in self._zathura_preset_buttons:
            return preset
        extra_options = dict(getattr(model, "extra_options", {}) or {})
        if extra_options.get("default-bg") == "#1E2740":
            return "midnight_lilac"
        theme_mode = str(getattr(model, "theme_mode", "plain") or "plain")
        if theme_mode == "pywal_generator":
            return "pywal"
        if theme_mode == "pywal_internal" or bool(getattr(model, "recolor", False)):
            return "focus"
        return "classic"

    def _preset_model(self, preset_id: str):
        model = self._zathura_working_model.model_copy(deep=True)
        model.extra_options = dict(getattr(model, "extra_options", {}) or {})
        for key in (
            "page-padding",
            "default-bg",
            "default-fg",
            "statusbar-bg",
            "statusbar-fg",
            "inputbar-bg",
            "inputbar-fg",
            "completion-bg",
            "completion-fg",
            "completion-group-bg",
            "completion-group-fg",
            "completion-highlight-bg",
            "completion-highlight-fg",
            "notification-bg",
            "notification-fg",
            "notification-error-bg",
            "notification-error-fg",
            "notification-warning-bg",
            "notification-warning-fg",
            "recolor-lightcolor",
            "recolor-darkcolor",
            "render-loading-bg",
            "render-loading-fg",
            "index-bg",
            "index-fg",
            "index-active-bg",
            "index-active-fg",
        ):
            model.extra_options.pop(key, None)
        model.enabled = True
        model.sync_to_zathurarc = True
        model.preset = preset_id
        model.statusbar_basename = True
        model.window_title_home_tilde = True
        model.session_use_fork = True
        model.include_files = list(getattr(model, "include_files", []) or [])

        if preset_id == "pywal":
            model.theme_mode = "pywal_generator"
            model.selection_clipboard = "primary"
            model.recolor = False
            model.session_open_mode = "fullscreen"
            return model

        if preset_id == "focus":
            model.theme_mode = "pywal_internal"
            model.selection_clipboard = "primary"
            model.recolor = True
            model.session_open_mode = "fullscreen"
            model.extra_options["page-padding"] = 8
            return model

        if preset_id == "midnight_lilac":
            model.theme_mode = "plain"
            model.selection_clipboard = "primary"
            model.recolor = True
            model.session_open_mode = "fullscreen"
            model.extra_options.update(
                {
                    "page-padding": 10,
                    "default-bg": "#1E2740",
                    "default-fg": "#9FC0E5",
                    "statusbar-bg": "#151D31",
                    "statusbar-fg": "#A77AD7",
                    "inputbar-bg": "#151D31",
                    "inputbar-fg": "#9FC0E5",
                    "completion-bg": "#1E2740",
                    "completion-fg": "#9FC0E5",
                    "completion-group-bg": "#1E2740",
                    "completion-group-fg": "#4C8EC5",
                    "completion-highlight-bg": "#A77AD7",
                    "completion-highlight-fg": "#151D31",
                    "notification-bg": "#1E2740",
                    "notification-fg": "#9FC0E5",
                    "notification-error-bg": "#A77AD7",
                    "notification-error-fg": "#151D31",
                    "notification-warning-bg": "#4C8EC5",
                    "notification-warning-fg": "#151D31",
                    "recolor-lightcolor": "#1E2740",
                    "recolor-darkcolor": "#9FC0E5",
                    "render-loading-bg": "#1E2740",
                    "render-loading-fg": "#4C8EC5",
                    "index-bg": "#1E2740",
                    "index-fg": "#9FC0E5",
                    "index-active-bg": "#4C8EC5",
                    "index-active-fg": "#151D31",
                }
            )
            return model

        model.theme_mode = "plain"
        model.selection_clipboard = "clipboard"
        model.recolor = False
        model.session_open_mode = "normal"
        return model

    def _apply_selected_zathura_preset(self):
        preset_id = self._selected_zathura_preset()
        self._zathura_working_model = self._preset_model(preset_id)
        success, message = self._save_zathura_settings_only(self._build_zathura_model_from_form())
        if success:
            QMessageBox.information(self, "Zathura", message)
        else:
            QMessageBox.warning(self, "Zathura", message)

    def _test_zathura_with_pdf(self):
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF para teste do Zathura",
            str(Path.home()),
            "Arquivos PDF (*.pdf)",
        )
        if not selected:
            return
        try:
            manager = ZathuraConfigManager(self._build_zathura_model_from_form())
            command = manager.build_open_command(selected, page=1)
            subprocess.Popen(command, start_new_session=True)
        except Exception as exc:
            QMessageBox.warning(self, "Teste Zathura", f"Não foi possível abrir o PDF de teste.\n\n{exc}")

    def _load_session_shortcuts(self) -> dict[str, str]:
        shortcuts = default_session_shortcuts()
        for item in SESSION_SHORTCUT_DEFINITIONS:
            key = f"ui/session_shortcuts/{item['id']}"
            shortcuts[item["id"]] = str(self.config_manager.get(key, shortcuts[item["id"]]) or "").strip()
        return shortcuts

    def _save_session_shortcuts(self, shortcuts: dict[str, str]):
        for item in SESSION_SHORTCUT_DEFINITIONS:
            key = f"ui/session_shortcuts/{item['id']}"
            self.config_manager.set(key, str(shortcuts.get(item["id"], "") or "").strip())
        parent = self.parent()
        views = getattr(parent, "views", None)
        session_view = views.get("session") if isinstance(views, dict) else None
        if session_view is not None and hasattr(session_view, "reload_configurable_shortcuts"):
            session_view.reload_configurable_shortcuts()

    def _build_zathura_model_from_form(self):
        model = self._zathura_working_model.model_copy(deep=True)
        model.preset = self._selected_zathura_preset()
        return model

    def _apply_zathura_form_to_settings_model(self):
        self.settings_model.zathura = self._build_zathura_model_from_form()

    def _save_zathura_settings_only(self, zathura_model: Any | None = None) -> tuple[bool, str]:
        try:
            if zathura_model is not None:
                self.settings_model.zathura = zathura_model
                self._zathura_working_model = zathura_model.model_copy(deep=True)
            else:
                self._apply_zathura_form_to_settings_model()
            self.settings_model.save_yaml(self.settings_path)
            updated = reload_settings(self.settings_path)
            self.settings_model = updated
            self._zathura_working_model = updated.zathura.model_copy(deep=True)
            if updated.zathura.enabled and updated.zathura.sync_to_zathurarc:
                result = ZathuraConfigManager(updated.zathura).apply()
                details = "\n".join(result.get("errors", []) + result.get("warnings", []))
                if result.get("success", False):
                    return True, details.strip() or "Configuração do Zathura aplicada com sucesso."
                return False, details.strip() or "A sincronização do zathurarc falhou."
            return True, "Configuração do Zathura salva no settings.yaml."
        except Exception as exc:
            return False, f"Não foi possível aplicar as configurações do Zathura.\n\n{exc}"

    def _refresh_zathura_status(self):
        return ZathuraConfigManager(self._build_zathura_model_from_form()).status()

    def _open_zathura_panel(self):
        dialog = ZathuraKeybindingsDialog(
            model_getter=self._build_zathura_model_from_form,
            apply_callback=self._save_zathura_settings_only,
            session_shortcuts_getter=self._load_session_shortcuts,
            session_shortcuts_setter=self._save_session_shortcuts,
            parent=self,
        )
        dialog.exec()

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
            self.settings_model.llm.backend = str(self.llm_backend_combo.currentData() or "local")
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
            self.settings_model.llm.cloud.model = self.llm_cloud_model_input.text().strip()
            self.settings_model.llm.cloud.api_base = self.llm_cloud_api_base_input.text().strip()
            self.settings_model.llm.cloud.api_version = self.llm_cloud_api_version_input.text().strip()
            self.settings_model.llm.cloud.organization = self.llm_cloud_organization_input.text().strip()
            self.settings_model.llm.cloud.api_key = self.llm_cloud_api_key_input.text().strip()
            self.settings_model.llm.cloud.timeout_seconds = self.llm_cloud_timeout_spin.value()
            self.settings_model.llm.cloud.max_retries = self.llm_cloud_max_retries_spin.value()
            self.settings_model.llm.glados.user_name = self.llm_user_name_input.text().strip()
            self.settings_model.llm.glados.glados_name = self.llm_assistant_name_input.text().strip()
            self.settings_model.llm.glados.personality_profile = str(
                self.personality_profile_combo.currentData() or "auto"
            ).strip().lower()

            self.settings_model.obsidian.templates_dir = self.obsidian_templates_dir_input.text().strip()
            self.settings_model.obsidian.auto_sync = self.obsidian_auto_sync_check.isChecked()
            self.settings_model.obsidian.sync_interval = self.obsidian_sync_interval_spin.value()

            self.settings_model.review_view.question_prompt_enabled = self.review_prompt_enabled_check.isChecked()
            self.settings_model.review_view.question_interval_minutes = self.review_question_interval_spin.value()
            self.settings_model.review_view.arrow_pan_step = self.review_arrow_pan_step_spin.value()

            self._apply_zathura_form_to_settings_model()

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
            self.config_manager.set("ui/onboarding_preference_set", True)
            self.config_manager.set("ui/onboarding_dialog_version", "tutorial_v3")
            self.config_manager.set("ui/secondary_button_color", self._selected_secondary_button_color)

            self.settings_model.save_yaml(self.settings_path)
            updated = reload_settings(self.settings_path)
            self.settings_model = updated
            self._zathura_working_model = updated.zathura.model_copy(deep=True)
            if updated.zathura.enabled and updated.zathura.sync_to_zathurarc:
                zathura_result = ZathuraConfigManager(updated.zathura).apply()
                if not zathura_result.get("success", False):
                    errors = "\n".join(zathura_result.get("errors", []))
                    warnings = "\n".join(zathura_result.get("warnings", []))
                    detail = "\n".join(part for part in [errors, warnings] if part).strip()
                    if detail:
                        QMessageBox.warning(
                            self,
                            "Zathura",
                            "As configurações foram salvas, mas a sincronização do zathurarc teve problemas:\n\n"
                            f"{detail}",
                        )
            payload = updated.model_dump()
            payload["ui"] = {
                "show_onboarding_dialog": self.show_onboarding_check.isChecked(),
                "onboarding_preference_set": True,
                "onboarding_dialog_version": "tutorial_v3",
                "secondary_button_color": self._selected_secondary_button_color,
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

    @staticmethod
    def _personality_profile_summary(profile_value: str) -> str:
        normalized = str(profile_value or "auto").strip().lower()
        mapping = {
            "auto": "Escolhe automaticamente com base na identidade atual do assistente.",
            "glados": "Tom irônico, técnico e exigente, com sarcasmo seco e foco em clareza.",
            "marvin": "Tom melancólico, pessimista e entediado, com humor existencial e precisão.",
        }
        return mapping.get(normalized, mapping["auto"])

    def _sync_personality_profile_summary(self):
        selected = str(self.personality_profile_combo.currentData() or "auto")
        self.personality_profile_summary_label.setText(self._personality_profile_summary(selected))

    def _set_device_mode(self, mode_value: str):
        value = str(mode_value or "auto")
        idx = self.llm_device_mode_combo.findData(value)
        if idx < 0:
            idx = self.llm_device_mode_combo.findData("auto")
        self.llm_device_mode_combo.setCurrentIndex(max(0, idx))
        self._sync_llm_mode_controls()

    def _apply_ollama_cloud_preset(self):
        cloud_idx = self.llm_backend_combo.findData("cloud")
        if cloud_idx >= 0:
            self.llm_backend_combo.setCurrentIndex(cloud_idx)
        self.llm_cloud_model_input.setText("ollama/qwen2.5:1.5b")
        self.llm_cloud_api_base_input.setText("http://127.0.0.1:11434")
        self.llm_cloud_api_version_input.clear()
        self.llm_cloud_organization_input.clear()
        self.llm_cloud_api_key_input.clear()
        if self.llm_cloud_timeout_spin.value() < 60:
            self.llm_cloud_timeout_spin.setValue(120)
        if self.llm_cloud_max_retries_spin.value() < 1:
            self.llm_cloud_max_retries_spin.setValue(1)
        self._sync_llm_mode_controls()

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
        self.llm_n_ctx_spin.setEnabled(local_enabled)
        self.llm_n_gpu_layers_spin.setEnabled(local_enabled)
        self.llm_device_mode_combo.setEnabled(local_enabled)
        self.llm_gpu_combo.setEnabled(local_enabled)
        self.llm_cpu_threads_spin.setEnabled(local_enabled and cpu_only)
        self.llm_cloud_model_input.setEnabled(not local_enabled)
        self.llm_cloud_ollama_preset_button.setEnabled(not local_enabled)
        self.llm_cloud_api_base_input.setEnabled(not local_enabled)
        self.llm_cloud_api_version_input.setEnabled(not local_enabled)
        self.llm_cloud_organization_input.setEnabled(not local_enabled)
        self.llm_cloud_api_key_input.setEnabled(not local_enabled)
        self.llm_cloud_timeout_spin.setEnabled(not local_enabled)
        self.llm_cloud_max_retries_spin.setEnabled(not local_enabled)

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
            ),
            "secondary_button_color": "#FFFFFF",
        }
        self.settings_saved.emit(payload)

    def _select_secondary_button_color(self, color: str):
        chosen = str(color or "").strip().upper()
        if chosen not in self._secondary_color_buttons:
            return
        self._selected_secondary_button_color = chosen
        self._refresh_secondary_palette_styles()

    def _refresh_secondary_palette_styles(self):
        for color, swatch in self._secondary_color_buttons.items():
            is_selected = color == self._selected_secondary_button_color
            border = "#ECECEC" if is_selected else "#444444"
            swatch.setChecked(is_selected)
            swatch.setStyleSheet(
                f"""
                QPushButton {{
                    background: {color};
                    border-radius: 15px;
                    border: 2px solid {border};
                }}
                QPushButton:hover {{
                    border: 2px solid #D8D8D8;
                }}
                """
            )

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
