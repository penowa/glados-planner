"""
Gerenciador de temas da aplicação
"""
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
import os
import json

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
        self.themes_dir = os.path.join(os.path.dirname(__file__), '..', 'themes')
        self.load_all_themes()
    
    def load_all_themes(self):
        """Carrega todos os temas disponíveis"""
        theme_files = ['philosophy_dark.qss', 'philosophy_light.qss', 'philosophy_night.qss']
        
        for theme_file in theme_files:
            theme_path = os.path.join(self.themes_dir, theme_file)
            if os.path.exists(theme_path):
                theme_name = theme_file.replace('.qss', '')
                with open(theme_path, 'r', encoding='utf-8') as f:
                    self.themes[theme_name] = f.read()
    
    def load_theme(self, theme_name):
        """Carrega um tema específico"""
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
                    return config.get('theme', 'philosophy_dark')
        except:
            pass
        return 'philosophy_dark'