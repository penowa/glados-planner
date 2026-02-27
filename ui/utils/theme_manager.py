"""
Gerenciador de temas da aplicação
"""
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
import os
import json
import sys
from pathlib import Path
from typing import Tuple

from ui.utils.config_manager import ConfigManager

class ThemeManager(QObject):
    """Gerencia temas da aplicação"""
    
    _instance = None
    theme_changed = pyqtSignal(str)
    DEFAULT_SECONDARY_BUTTON_COLOR = "#FFFFFF"
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.current_theme = None
        self.themes = {}
        self.themes_dir = self._resolve_themes_dir()
        self.config_manager = ConfigManager.instance()
        self.load_all_themes()

    def _resolve_themes_dir(self) -> str:
        """Resolve diretório de temas para dev e build PyInstaller."""
        if getattr(sys, "frozen", False):
            # No PyInstaller onedir, dados ficam sob sys._MEIPASS.
            meipass = Path(getattr(sys, "_MEIPASS", Path.cwd()))
            frozen_dir = meipass / "ui" / "themes"
            return str(frozen_dir)
        local_dir = Path(__file__).resolve().parent.parent / "themes"
        return str(local_dir)
    
    def load_all_themes(self):
        """Carrega apenas o tema oficial da aplicação."""
        theme_files = ["philosophy_dark.qss"]
        
        for theme_file in theme_files:
            theme_path = os.path.join(self.themes_dir, theme_file)
            if os.path.exists(theme_path):
                theme_name = theme_file.replace('.qss', '')
                with open(theme_path, 'r', encoding='utf-8') as f:
                    self.themes[theme_name] = f.read()
    
    def load_theme(self, theme_name):
        """Carrega um tema específico"""
        if theme_name != "philosophy_dark":
            theme_name = "philosophy_dark"
        if theme_name in self.themes:
            app = QApplication.instance()
            if app:
                # Aplicar estilo (com variáveis de aparência resolvidas)
                app.setStyleSheet(self._render_theme_stylesheet(self.themes[theme_name]))
                self.current_theme = theme_name
                self.theme_changed.emit(theme_name)
                
                # Salvar preferência
                self.save_preference(theme_name)
                return True
        # Se algo falhou ao carregar o QSS, mantém um fallback escuro mínimo.
        app = QApplication.instance()
        if app:
            app.setStyleSheet(
                "QWidget { background-color: #1A1F2B; color: #E8EAF0; }"
                "QLineEdit, QTextEdit, QPlainTextEdit, QListView, QTableView {"
                "background-color: #232A38; color: #E8EAF0; border: 1px solid #3A4358; }"
                "QPushButton { background-color: #2A3142; color: #E8EAF0; border: 1px solid #4A5674; padding: 4px; }"
            )
        return False

    def get_secondary_button_color(self) -> str:
        raw = self.config_manager.get("ui/secondary_button_color", self.DEFAULT_SECONDARY_BUTTON_COLOR)
        return self._sanitize_hex_color(str(raw), self.DEFAULT_SECONDARY_BUTTON_COLOR)

    def set_secondary_button_color(self, color: str, reload_theme: bool = True) -> str:
        normalized = self._sanitize_hex_color(color, self.DEFAULT_SECONDARY_BUTTON_COLOR)
        self.config_manager.set("ui/secondary_button_color", normalized)
        if reload_theme:
            self.load_theme(self.current_theme or "philosophy_dark")
        return normalized

    def _render_theme_stylesheet(self, qss_template: str) -> str:
        secondary = self.get_secondary_button_color()
        hover_bg = self._to_rgba(secondary, 0.12)
        pressed_bg = self._to_rgba(secondary, 0.20)
        return (
            qss_template
            .replace("{{SECONDARY_BUTTON_COLOR}}", secondary)
            .replace("{{SECONDARY_BUTTON_HOVER_BG}}", hover_bg)
            .replace("{{SECONDARY_BUTTON_PRESSED_BG}}", pressed_bg)
        )

    @staticmethod
    def _sanitize_hex_color(value: str, fallback: str) -> str:
        candidate = str(value or "").strip().upper()
        if not candidate.startswith("#"):
            candidate = f"#{candidate}"
        if len(candidate) != 7:
            return fallback
        try:
            int(candidate[1:], 16)
        except ValueError:
            return fallback
        return candidate

    @staticmethod
    def _to_rgb_tuple(color: str) -> Tuple[int, int, int]:
        hex_color = color.lstrip("#")
        return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

    @classmethod
    def _to_rgba(cls, color: str, alpha: float) -> str:
        r, g, b = cls._to_rgb_tuple(color)
        bounded = max(0.0, min(float(alpha), 1.0))
        return f"rgba({r}, {g}, {b}, {bounded:.2f})"
    
    def get_theme_names(self):
        """Retorna lista de nomes de temas disponíveis"""
        return list(self.themes.keys())
    
    def save_preference(self, theme_name):
        """Salva preferência de tema"""
        try:
            config_dir = os.path.expanduser('~/.glados')
            os.makedirs(config_dir, exist_ok=True)
            
            config_path = os.path.join(config_dir, 'ui_config.json')
            config = {'theme': theme_name}
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Erro ao salvar preferência: {e}")
    
    def load_preference(self):
        """Carrega preferência de tema salva"""
        try:
            config_path = os.path.expanduser('~/.glados/ui_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if config.get("theme") == "philosophy_dark":
                        return "philosophy_dark"
                    return "philosophy_dark"
        except:
            pass
        return 'philosophy_dark'
