"""
Gerenciador de temas da aplicação
"""
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
import os
import json
import sys
from pathlib import Path

class ThemeManager(QObject):
    """Gerencia temas da aplicação"""
    
    _instance = None
    theme_changed = pyqtSignal(str)
    
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
                # Aplicar estilo
                app.setStyleSheet(self.themes[theme_name])
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
